from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
import os
from services.youtube_utils import extract_video_id

router = APIRouter(prefix="/ingest/debug", tags=["ingest-debug"])

class YtIn(BaseModel):
    url: str

@router.post("/tracks")
def list_tracks(payload: YtIn):
    vid = extract_video_id(payload.url or "")
    if not vid:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    cookies = (os.getenv("YT_COOKIES_FILE") or "").strip() or None
    
    try:
        listing = YouTubeTranscriptApi.list_transcripts(vid, cookies=cookies)
        tracks = []
        for t in list(listing):
            code = getattr(t, "language_code", None)
            tracks.append({
                "language": getattr(t, "language", None),
                "language_code": code,
                "base_lang": (code or "").split("-")[0].lower(),
                "is_generated": bool(getattr(t, "is_generated", False)),
            })
        return {"video_id": vid, "tracks": tracks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tracks: {str(e)}")


