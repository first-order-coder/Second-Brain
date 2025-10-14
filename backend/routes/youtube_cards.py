"""
YouTube flashcards router - handles YouTube URL to flashcards conversion.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
    lang_hint: List[str] = Field(default=["en", "en-US", "en-GB"], description="Language preferences")
    allow_auto_generated: bool = Field(default=True, description="Allow auto-generated captions")
    use_cookies: bool = Field(default=False, description="Use cookies for authentication")
    enable_fallback: bool = Field(default=False, description="Enable yt-dlp fallback")

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
        
        # Select key points for flashcard generation
        key_windows = select_key_points(windows, request.n_cards)
        
        if not key_windows:
            raise HTTPException(status_code=422, detail="No key points selected for flashcard generation")
        
        # Prepare excerpts for LLM
        excerpts_json = prepare_excerpts_for_llm(key_windows)
        
        # Generate flashcards using LLM
        try:
            raw_cards = generate_flashcards_from_excerpts(excerpts_json, request.n_cards)
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
        
        # Limit to requested number
        final_cards = final_cards[:request.n_cards]
        
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
            warnings=warnings
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
