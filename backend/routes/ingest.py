from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import logging
from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from services.youtube_utils import extract_video_id
from services.youtube_transcripts import (
    fetch_best_transcript_or_fallback,
    NoTranscriptAvailable,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = logging.getLogger("ingest")

class IngestUrlIn(BaseModel):
    url: HttpUrl
    kind: str = "youtube"

@router.post("/url")
async def ingest_url(payload: IngestUrlIn):
    if payload.kind != "youtube":
        raise HTTPException(status_code=400, detail="Only YouTube links supported here")
    url = str(payload.url)
    vid = extract_video_id(url)
    if not vid:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        segments = fetch_best_transcript_or_fallback(url, vid)
    except VideoUnavailable:
        raise HTTPException(status_code=404, detail="Video unavailable")
    except TranscriptsDisabled:
        raise HTTPException(status_code=422, detail="Transcripts are disabled for this video")
    except NoTranscriptFound:
        raise HTTPException(status_code=422, detail="No transcript found in requested languages")
    except NoTranscriptAvailable as e:
        logger.info(f"NoTranscriptAvailable: requested={e.requested_langs}; available={e.available}")
        return JSONResponse(
            {"ok": False, "error": "no_transcript", "detail": "No transcript matched your language settings.",
             "requested_langs": e.requested_langs, "available_tracks": e.available},
            status_code=422
        )
    except RuntimeError as e:
        logger.warning(f"Transcript listing/fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch transcript: {e}")
    except Exception as e:
        logger.exception("Unexpected ingest error")
        raise HTTPException(status_code=500, detail="Unexpected error during YouTube ingest")

    if not segments:
        raise HTTPException(status_code=422, detail="Transcript is empty")

    # TODO: your existing chunking + flashcard generation can be called here (unchanged)
    return {"ok": True, "segments_count": len(segments), "message": "Transcript fetched successfully"}


