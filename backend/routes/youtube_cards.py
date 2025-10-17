"""
YouTube flashcards router - handles YouTube URL to flashcards conversion.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from services.youtube_transcript import get_transcript, list_transcripts
from services.cardify import (
    merge_small_segments, 
    semantic_windows, 
    select_key_points,
    prepare_excerpts_for_llm,
    deduplicate_cards,
    truncate_answer
)
from services.llm_integration import generate_flashcards_from_excerpts
from services.decks import get_or_create_deck_for_source, attach_cards_to_deck
from utils import clamp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/youtube", tags=["youtube"])

class YouTubeTrack(BaseModel):
    lang: str = Field(..., description="Language code")
    kind: str = Field(..., description="Type: manual or auto")

class YouTubeTracksResponse(BaseModel):
    video_id: str
    tracks: List[YouTubeTrack]
    gated: bool = Field(default=False, description="Video is age/consent restricted")

class YouTubeFlashcardsRequest(BaseModel):
    url: str = Field(..., description="YouTube URL")
    n_cards: int = Field(default=10, ge=1, le=20, description="Number of cards to generate")
    # Add-ONLY: Optional requested count for enhanced control
    requested_count: Optional[int] = Field(default=None, ge=1, le=50, description="Requested number of cards (overrides n_cards if provided)")
    lang_hint: List[str] = Field(default=["en", "en-US", "en-GB"], description="Language preferences")
    allow_auto_generated: bool = Field(default=True, description="Allow auto-generated captions")
    use_cookies: bool = Field(default=False, description="Use cookies for authentication")
    enable_fallback: bool = Field(default=False, description="Enable yt-dlp fallback")

    @field_validator("requested_count", mode="before")
    @classmethod
    def coerce_count(cls, v):
        """Coerce requested_count to integer or None"""
        if v is None or v == '' or v == "":
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

class YouTubeCard(BaseModel):
    front: str
    back: str
    cloze: Optional[str] = None
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    evidence: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    tags: List[str] = ["youtube"]

class YouTubeFlashcardsResponse(BaseModel):
    video_id: str
    title: Optional[str] = None
    url: str
    lang: str
    cards: List[YouTubeCard]
    warnings: List[str]
    # Added for deck parity (additive, backwards-compatible)
    deck_id: Optional[str] = None

@router.get("/flashcards/ping")
async def youtube_flashcards_ping():
    return {"ok": True}

@router.get("/tracks", response_model=YouTubeTracksResponse)
async def get_youtube_tracks(url: str):
    """
    Get available transcript tracks for a YouTube video.
    """
    try:
        from services.youtube_transcript import extract_video_id
        video_id = extract_video_id(url)
        
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        logger.info(f"Listing tracks for video {video_id}")
        
        # Check if cookies are available
        import os
        cookies_path = os.getenv("YT_COOKIES_PATH")
        cookies = cookies_path if cookies_path and os.path.exists(cookies_path) else None
        
        try:
            tracks_data = list_transcripts(video_id, cookies=cookies)
        except Exception as e:
            error_msg = str(e).lower()
            if "age" in error_msg or "consent" in error_msg or "membership" in error_msg:
                return YouTubeTracksResponse(
                    video_id=video_id,
                    tracks=[],
                    gated=True
                )
            else:
                raise HTTPException(status_code=500, detail=f"Failed to list tracks: {str(e)}")
        
        tracks = []
        for track in tracks_data:
            tracks.append(YouTubeTrack(
                lang=track['lang'],
                kind='manual' if not track.get('is_generated', True) else 'auto'
            ))
        
        return YouTubeTracksResponse(
            video_id=video_id,
            tracks=tracks,
            gated=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing tracks: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/flashcards", response_model=YouTubeFlashcardsResponse)
async def generate_youtube_flashcards(request: YouTubeFlashcardsRequest):
    """
    Generate flashcards from YouTube video transcript.
    """
    try:
        # Extract video ID for logging
        from services.youtube_transcript import extract_video_id
        video_id = extract_video_id(request.url)
        
        logger.info(f"Processing YouTube flashcards request for video {video_id}")
        
        # Normalize language hints: map all "en-*" to "en"
        normalized_langs = []
        for lang in request.lang_hint:
            if lang.startswith('en-'):
                normalized_langs.append('en')
            else:
                normalized_langs.append(lang)
        # Remove duplicates while preserving order
        normalized_langs = list(dict.fromkeys(normalized_langs))
        
        # Get transcript
        try:
            segments, chosen_lang, warnings = get_transcript(
                video_url=request.url,
                langs=normalized_langs,
                allow_auto=request.allow_auto_generated,
                use_cookies=request.use_cookies,
                enable_fallback=request.enable_fallback
            )
        except Exception as e:
            error_msg = str(e)
            if "Age/consent" in error_msg or "membership" in error_msg or "restricted" in error_msg:
                raise HTTPException(
                    status_code=422, 
                    detail={
                        "detail": "Video is age/consent/membership restricted.",
                        "next_steps": [
                            "Enable cookies and retry",
                            "Check available tracks via /youtube/tracks",
                            "Try a different video"
                        ]
                    }
                )
            elif "No transcript available" in error_msg:
                raise HTTPException(
                    status_code=422, 
                    detail={
                        "detail": "No transcript available for this video/language.",
                        "next_steps": [
                            "Enable fallback",
                            "Provide cookies (consent/age/membership)",
                            "Check available tracks via /youtube/tracks and adjust langHint"
                        ]
                    }
                )
            else:
                raise HTTPException(status_code=500, detail=f"Transcript extraction failed: {error_msg}")
        
        if not segments:
            raise HTTPException(status_code=422, detail="No transcript segments found")
        
        # Convert transcript objects to dictionaries
        segment_dicts = []
        for segment in segments:
            if hasattr(segment, 'text'):
                segment_dicts.append({
                    'text': segment.text,
                    'start': segment.start,
                    'end': segment.start + segment.duration
                })
            else:
                segment_dicts.append(segment)  # Already a dict
        
        # Process segments into semantic windows
        merged_segments = merge_small_segments(segment_dicts)
        windows = semantic_windows(merged_segments)
        
        if not windows:
            raise HTTPException(status_code=422, detail="No suitable content windows found")
        
        # Determine target count (requested_count overrides n_cards if provided)
        # Add defensive integer coercion (belt & suspenders)
        target_count = None
        if request.requested_count is not None:
            try:
                target_count = clamp(
                    int(request.requested_count), 
                    default=request.n_cards, 
                    min_val=1, 
                    max_val=50
                )
            except (TypeError, ValueError):
                target_count = request.n_cards
        else:
            target_count = request.n_cards
        
        # Select key points for flashcard generation
        key_windows = select_key_points(windows, target_count)
        
        if not key_windows:
            raise HTTPException(status_code=422, detail="No key points selected for flashcard generation")
        
        # Prepare excerpts for LLM
        excerpts_json = prepare_excerpts_for_llm(key_windows)
        
        # Generate flashcards using LLM
        try:
            raw_cards = generate_flashcards_from_excerpts(excerpts_json, target_count, target_count)
        except Exception as e:
            logger.error(f"LLM flashcard generation failed for {video_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Flashcard generation failed: {str(e)}")
        
        # Post-process cards
        processed_cards = []
        for card in raw_cards:
            # Ensure timestamps are filled from window data if missing
            if card.get('start_s') is None or card.get('end_s') is None:
                # Find matching window and use its timestamps
                for window in key_windows:
                    if window['text'] in excerpts_json:  # Simple matching
                        card['start_s'] = window['start']
                        card['end_s'] = window['end']
                        break
            
            # Truncate answer if too long
            card['back'] = truncate_answer(card['back'])
            
            # Ensure tags include youtube
            if 'youtube' not in card.get('tags', []):
                card['tags'] = card.get('tags', []) + ['youtube']
            
            processed_cards.append(YouTubeCard(**card))
        
        # Deduplicate cards
        deduplicated_cards = deduplicate_cards([card.dict() for card in processed_cards])
        final_cards = [YouTubeCard(**card) for card in deduplicated_cards]
        
        # Limit to target count (enforce exact count)
        final_cards = final_cards[:int(target_count)]
        
        # Automatically save cards to deck for parity with PDF flow
        deck_id = None
        try:
            # Build a friendly label similar to existing /youtube/save endpoint
            label_parts = ["youtube"]
            if video_id:
                label_parts.append(video_id)
            if request.url:
                # keep it short
                label_parts.append(request.url[:60])
            source_label = " | ".join(label_parts)
            
            # Create or get deck for this source
            deck_id = get_or_create_deck_for_source("pdf_flashcards.db", source_label)
            
            # Convert cards to the format expected by attach_cards_to_deck
            cards_data = []
            for card in final_cards:
                cards_data.append({
                    'front': card.front,
                    'back': card.back
                })
            
            # Attach cards to the deck
            attach_cards_to_deck("pdf_flashcards.db", deck_id, cards_data)
            
            logger.info(f"Auto-saved {len(final_cards)} YouTube cards to deck {deck_id}")
            
        except Exception as persist_err:
            # Log but do not break the generation response; frontend can still use manual save
            logger.error(f"Failed to auto-save YouTube cards to deck: {persist_err}")
            deck_id = None
        
        # Log success
        logger.info(
            f"Successfully generated {len(final_cards)} flashcards for video {video_id}",
            extra={
                "event": "youtube_flashcards",
                "video_id": video_id,
                "lang": chosen_lang,
                "using_cookies": request.use_cookies,
                "enable_fallback": request.enable_fallback,
                "cards": len(final_cards),
                "warnings": warnings
            }
        )
        
        return YouTubeFlashcardsResponse(
            video_id=video_id,
            title=None,  # Could be extracted from YouTube API if needed
            url=request.url,
            lang=chosen_lang,
            cards=final_cards,
            warnings=warnings,
            deck_id=deck_id  # Include deck_id for auto-navigation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in YouTube flashcards generation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health")
async def youtube_health_check():
    """Health check for YouTube functionality."""
    try:
        # Check if required dependencies are available
        from services.youtube_transcript import YouTubeTranscriptApi
        from services.cardify import merge_small_segments
        from services.llm_integration import call_llm_json
        
        return {
            "status": "healthy",
            "dependencies": {
                "youtube_transcript_api": YouTubeTranscriptApi is not None,
                "webvtt": True,  # Will be imported in transcript service
                "openai": True   # Will be imported in LLM service
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
