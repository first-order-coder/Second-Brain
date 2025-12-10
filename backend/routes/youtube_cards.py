"""
YouTube flashcards router - handles YouTube URL to flashcards conversion.

This router uses yt-dlp for robust subtitle extraction and creates decks
in Supabase for the "My Decks" feature.

    Pipeline:
    1. Extract video ID + title (yt-dlp metadata)
    2. Fetch raw VTT subtitles via yt-dlp
    3. Clean transcript via OpenAI (remove timestamps, formatting)
    4. Create deck in Supabase (required before transcript due to FK constraint)
    5. Store cleaned transcript in Supabase
    6. Generate flashcards from cleaned transcript (same as PDFs)
    7. Store flashcards in Supabase
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field, field_validator, ConfigDict
import httpx

from services.youtube_transcript import list_transcripts  # Still used for /tracks endpoint
from services.youtube_utils import clean_youtube_url
from services.ytdlp_subs import YTDlpError, fetch_youtube_metadata, fetch_raw_vtt_with_ytdlp
from services.transcript_cleaner import clean_transcript_with_openai, TranscriptCleaningError
from flashcard_generator import generate_flashcards  # Same function used for PDFs
from repo.dual_repo import create_deck_in_supabase, upsert_flashcard, delete_flashcards
from repo.supabase_transcripts import save_cleaned_transcript_to_supabase

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
    # Pydantic v2 model config - explicitly allow extra fields to be ignored
    model_config = ConfigDict(extra="ignore")  # Ignore extra fields instead of raising validation error
    
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

class ManualTranscriptRequest(BaseModel):
    """Request model for manual transcript flashcard generation"""
    url: Optional[str] = Field(default=None, description="YouTube URL (optional metadata)")
    title: Optional[str] = Field(default=None, description="Optional deck title hint")
    transcript: str = Field(..., description="Raw transcript text (required)")

class ManualTranscriptRequest(BaseModel):
    """Request model for manual transcript flashcard generation"""
    url: Optional[str] = Field(default=None, description="YouTube URL (optional metadata)")
    title: Optional[str] = Field(default=None, description="Optional deck title hint")
    transcript: str = Field(..., description="Raw transcript text (required)")

class YouTubeFlashcardsResponse(BaseModel):
    video_id: str
    title: Optional[str] = None
    url: str
    lang: str
    cards: List[YouTubeCard]
    warnings: List[str]
    # Added for deck parity (additive, backwards-compatible)
    deck_id: Optional[str] = None
    # New fields for proper title handling
    videoTitle: Optional[str] = None  # Real YouTube title from oEmbed

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

async def fetch_youtube_title(url: str) -> Optional[str]:
    """
    Fetch YouTube video title using oEmbed API.
    Returns None on failure (graceful degradation).
    """
    oembed_url = "https://www.youtube.com/oembed"
    params = {"url": url, "format": "json"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(oembed_url, params=params)
            if resp.status_code != 200:
                logger.warning(f"oEmbed returned status {resp.status_code} for URL: {url}")
                return None
            data = resp.json()
            title = data.get("title")
            if isinstance(title, str):
                title = title.strip()
                return title if title else None
            return None
    except Exception as e:
        logger.warning(f"Failed to fetch YouTube title via oEmbed: {e}")
        return None

@router.post("/flashcards", response_model=YouTubeFlashcardsResponse)
async def generate_youtube_flashcards(
    request: YouTubeFlashcardsRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Generate flashcards from YouTube video transcript.
    
    Pipeline:
    1. Extract video ID + title
    2. Fetch raw VTT subtitles via yt-dlp
    3. Clean transcript via OpenAI
    4. Store cleaned transcript in Supabase
    5. Create deck in Supabase
    6. Generate flashcards from cleaned transcript (same as PDFs)
    7. Store flashcards in Supabase
    
    Optional header: X-User-Id - Supabase auth user ID for deck creation in "My Decks"
    """
    warnings = []
    try:
        # Log incoming request
        logger.info(f"Received YouTube flashcards request: url={request.url[:80]}, user_id={x_user_id}")
        
        # Clean and normalize the URL
        clean_url = clean_youtube_url(request.url)
        logger.info(f"Cleaned YouTube URL: {request.url[:80]}... -> {clean_url[:80]}...")
        
        # Step 1: Extract video ID + title using yt-dlp metadata
        try:
            logger.info(f"Fetching YouTube metadata for: {clean_url[:80]}...")
            metadata = fetch_youtube_metadata(clean_url)
            video_id = metadata["id"]
            video_title = metadata["title"]
            logger.info(f"Got metadata: id={video_id}, title={video_title[:50]}...")
        except YTDlpError as e:
            logger.error(f"Failed to fetch YouTube metadata: {e}")
            # If it's a transcript/subtitle related error, use the standard message
            error_msg = str(e).lower()
            if "subtitle" in error_msg or "transcript" in error_msg or "caption" in error_msg:
                message = "No transcript available for this video/language. You can switch to Manual transcript mode and paste the transcript yourself (for example, by using yt-dlp to download subtitles and cleaning them with ChatGPT)."
            else:
                message = f"Could not retrieve video information: {str(e)}"
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "message": message
                }
            )
        
        if not video_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": "Invalid YouTube URL: could not extract video ID"
                }
            )
        
        # Step 2: Fetch raw VTT subtitles via yt-dlp
        try:
            logger.info(f"Fetching raw VTT subtitles for: {video_id}")
            raw_vtt = fetch_raw_vtt_with_ytdlp(clean_url, lang="en")
            logger.info(f"Fetched raw VTT: {len(raw_vtt)} characters")
        except YTDlpError as e:
            logger.error(f"Failed to fetch raw VTT: {e}")
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "message": "No transcript available for this video/language. You can switch to Manual transcript mode and paste the transcript yourself (for example, by using yt-dlp to download subtitles and cleaning them with ChatGPT)."
                }
            )
        
        # Step 3: Clean transcript via OpenAI
        try:
            logger.info(f"Cleaning transcript via OpenAI: {len(raw_vtt)} chars raw VTT")
            cleaned_transcript = clean_transcript_with_openai(raw_vtt)
            logger.info(f"Cleaned transcript: {len(cleaned_transcript)} characters")
        except TranscriptCleaningError as e:
            logger.error(f"Failed to clean transcript: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"Failed to process transcript: {str(e)}"
                }
            )
        
        if not cleaned_transcript or not cleaned_transcript.strip():
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "message": "Transcript is empty after cleaning. The video may not have usable subtitles."
                }
            )
        
        # Step 4: Create/ensure deck in Supabase (must exist before transcript due to FK constraint)
        deck_id = video_id  # Use video_id as stable deck_id
        deck_title = f"YouTube: {video_title}"
        source_label = video_title or clean_url[:80]
        
        logger.info(f"Creating YouTube deck in Supabase: deck_id={deck_id}, title={deck_title}, user_id={x_user_id}")
        deck_created = create_deck_in_supabase(
            deck_id=deck_id,
            title=deck_title,
            source_type="youtube",
            source_label=source_label,
            user_id=x_user_id  # may be None, function handles gracefully
        )
        
        if not deck_created:
            logger.warning(f"Failed to create deck in Supabase for {deck_id}, but continuing with flashcard generation")
            warnings.append("Deck creation failed")
        
        # Step 5: Store cleaned transcript in Supabase (requires user_id and deck to exist)
        if not x_user_id:
            logger.warning("No user_id provided - skipping transcript storage")
            warnings.append("Transcript not saved (user authentication required)")
        else:
            try:
                logger.info(f"Storing cleaned transcript in Supabase: {len(cleaned_transcript)} chars")
                transcript_saved = save_cleaned_transcript_to_supabase(
                    deck_id=deck_id,
                    user_id=x_user_id,
                    source_type="youtube",
                    source_url=clean_url,
                    cleaned_transcript=cleaned_transcript
                )
                
                if transcript_saved:
                    logger.info(f"Successfully saved cleaned transcript for deck {deck_id}")
                else:
                    logger.warning(f"Failed to save cleaned transcript for deck {deck_id}")
                    warnings.append("Transcript storage failed")
            except Exception as transcript_err:
                logger.error(f"Error storing transcript: {transcript_err}", exc_info=True)
                warnings.append("Transcript storage failed")
        
        # Step 6: Generate flashcards from cleaned transcript (same function as PDFs)
        try:
            logger.info(f"Generating flashcards from cleaned transcript: {len(cleaned_transcript)} chars")
            flashcards_data = generate_flashcards(cleaned_transcript)
            logger.info(f"Generated {len(flashcards_data)} flashcards")
        except Exception as e:
            logger.error(f"Flashcard generation failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"Failed to generate flashcards: {str(e)}"
                }
            )
        
        if not flashcards_data:
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "message": "No flashcards could be generated from this transcript."
                }
            )
        
        # Convert to YouTubeCard format for response
        final_cards = []
        for card in flashcards_data:
            final_cards.append(YouTubeCard(
                front=card.get("question", ""),
                back=card.get("answer", ""),
                tags=["youtube"]
            ))
        
        # Step 7: Store flashcards in Supabase
        try:
            # Delete existing flashcards for this deck (in case of regeneration)
            delete_flashcards(deck_id)
            
            # Insert flashcards into Supabase
            for idx, card in enumerate(flashcards_data, start=1):
                upsert_flashcard(
                    pdf_id=deck_id,  # deck_id
                    question=card.get("question", ""),
                    answer=card.get("answer", ""),
                    card_number=idx
                )
            
            logger.info(f"Auto-saved {len(flashcards_data)} YouTube cards to Supabase deck {deck_id}")
        except Exception as persist_err:
            logger.error(f"Failed to auto-save YouTube cards to Supabase deck: {persist_err}", exc_info=True)
            warnings.append("Flashcard storage failed")
        
        # Log success
        logger.info(
            f"Successfully generated {len(final_cards)} flashcards for video {video_id}",
            extra={
                "event": "youtube_flashcards",
                "video_id": video_id,
                "cards": len(final_cards),
                "warnings": warnings
            }
        )
        
        return YouTubeFlashcardsResponse(
            video_id=video_id,
            title=video_title,
            url=clean_url,
            lang="en",  # We always use English from yt-dlp
            cards=final_cards,
            warnings=warnings,
            deck_id=deck_id,
            videoTitle=video_title
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in YouTube flashcards generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Failed to process this YouTube video. Please try again later."
            }
        )

@router.post("/transcript-flashcards", response_model=YouTubeFlashcardsResponse)
async def generate_flashcards_from_manual_transcript(
    request: ManualTranscriptRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Generate flashcards from manually pasted transcript text.
    This endpoint allows users to paste transcript text when automatic YouTube caption fetching fails.
    
    Optional header: X-User-Id - Supabase auth user ID for deck creation in "My Decks"
    """
    try:
        # Validate transcript is non-empty
        transcript_text = request.transcript.strip()
        if not transcript_text:
            raise HTTPException(status_code=400, detail="Transcript text is empty.")
        
        logger.info(f"Received manual transcript request: url={request.url}, title={request.title}, transcript_length={len(transcript_text)}")
        
        # Extract video ID from URL if provided (for metadata)
        video_id = None
        clean_url = request.url or ""
        if request.url:
            try:
                from services.youtube_transcript import extract_video_id
                clean_url = clean_youtube_url(request.url)
                video_id = extract_video_id(clean_url)
            except Exception as e:
                logger.warning(f"Could not extract video ID from URL: {e}")
        
        # Use provided title or generate a fallback
        video_title = request.title
        if not video_title and video_id:
            video_title = f"YouTube: {video_id}"
        elif not video_title:
            video_title = "YouTube: Manual Transcript"
        
        # Process transcript text similar to how YouTube segments are processed
        # Convert transcript to segments format for consistency
        # For manual transcripts, we'll treat the entire text as one segment
        # and then use semantic windows to extract key points
        
        from services.cardify import (
            merge_small_segments,
            semantic_windows,
            select_key_points,
            prepare_excerpts_for_llm,
            deduplicate_cards,
            truncate_answer
        )
        
        # Create a simple segment structure from the transcript text
        # Split by sentences or paragraphs for better processing
        import re
        # Split by double newlines (paragraphs) or single newlines (lines)
        segments = []
        if "\n\n" in transcript_text:
            # Paragraph-based splitting
            paragraphs = transcript_text.split("\n\n")
            current_time = 0.0
            for para in paragraphs:
                para = para.strip()
                if para:
                    # Estimate duration: ~150 words per minute, ~2.5 words per second
                    word_count = len(para.split())
                    duration = word_count / 2.5
                    segments.append({
                        'text': para,
                        'start': current_time,
                        'end': current_time + duration
                    })
                    current_time += duration
        else:
            # Line-based splitting
            lines = transcript_text.split("\n")
            current_time = 0.0
            for line in lines:
                line = line.strip()
                if line:
                    word_count = len(line.split())
                    duration = max(1.0, word_count / 2.5)  # Minimum 1 second
                    segments.append({
                        'text': line,
                        'start': current_time,
                        'end': current_time + duration
                    })
                    current_time += duration
        
        if not segments:
            raise HTTPException(status_code=400, detail="Could not parse transcript into segments.")
        
        # Process segments into semantic windows (same as YouTube flow)
        merged_segments = merge_small_segments(segments)
        windows = semantic_windows(merged_segments)
        
        if not windows:
            raise HTTPException(status_code=422, detail="No suitable content windows found in transcript.")
        
        # Force exactly 10 cards (same as YouTube flow)
        target_count = 10
        
        # Select key points for flashcard generation
        key_windows = select_key_points(windows, target_count)
        
        if not key_windows:
            raise HTTPException(status_code=422, detail="No key points selected for flashcard generation.")
        
        # Prepare excerpts for LLM
        excerpts_json = prepare_excerpts_for_llm(key_windows)
        
        # Generate flashcards using LLM (same as YouTube flow)
        try:
            raw_cards = generate_flashcards_from_excerpts(excerpts_json, target_count, target_count)
        except Exception as e:
            logger.error(f"LLM flashcard generation failed for manual transcript: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate flashcards from transcript.")
        
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
        
        # Limit to target count (enforce exactly 10)
        final_cards = final_cards[:int(target_count)]
        
        # Automatically save cards to Supabase deck for parity with PDF/YouTube flow
        # Use video_id if available, otherwise generate a UUID
        import uuid
        deck_id = video_id if video_id else str(uuid.uuid4())
        try:
            # Build deck title
            deck_title = f"YouTube: {video_title}" if video_title else "YouTube: Manual Transcript"
            
            # Build source label for reference
            source_label = video_title or clean_url[:80] if clean_url else "Manual Transcript"
            
            # Create deck in Supabase (same as PDF flow) - this is required for "My Decks"
            logger.info(f"Creating manual transcript deck in Supabase: deck_id={deck_id}, title={deck_title}, user_id={x_user_id}")
            deck_created = create_deck_in_supabase(
                deck_id=deck_id,
                title=deck_title,
                source_type="youtube",
                source_label=source_label,
                user_id=x_user_id  # may be None, function handles gracefully
            )
            
            if not deck_created:
                logger.warning(f"Failed to create deck in Supabase for {deck_id}, but continuing with flashcard insert")
            
            # Delete existing flashcards for this deck (in case of regeneration)
            delete_flashcards(deck_id)
            
            # Insert flashcards into Supabase
            for idx, card in enumerate(final_cards, start=1):
                upsert_flashcard(
                    pdf_id=deck_id,  # deck_id
                    question=card.front,
                    answer=card.back,
                    card_number=idx
                )
            
            logger.info(f"Auto-saved {len(final_cards)} manual transcript cards to Supabase deck {deck_id}")
            
        except Exception as persist_err:
            # Log but do not break the generation response
            logger.error(f"Failed to auto-save manual transcript cards to Supabase deck: {persist_err}", exc_info=True)
            # Keep deck_id for frontend navigation even if save failed
        
        # Return response in same format as YouTube flashcards endpoint
        return YouTubeFlashcardsResponse(
            video_id=video_id or "manual",
            title=video_title,
            url=clean_url or "",
            lang="manual",
            cards=final_cards,
            warnings=[],
            deck_id=deck_id,
            videoTitle=video_title
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in manual transcript flashcard generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate flashcards from transcript.")

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
