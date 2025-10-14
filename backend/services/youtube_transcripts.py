import os, time, logging
from typing import List, Dict, Optional, Tuple
from xml.etree.ElementTree import ParseError
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

log = logging.getLogger("yt-transcripts")

class NoTranscriptAvailable(Exception):
    def __init__(self, message: str, requested_langs: List[str], available: List[Dict]):
        super().__init__(message)
        self.requested_langs = requested_langs
        self.available = available

def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return default if v is None else v

def _langs() -> List[str]:
    raw = _env("YT_TRANSCRIPT_LANGS","en,en-US")
    return [x.strip() for x in raw.split(",") if x.strip()]

def _cookies_file() -> Optional[str]:
    v = _env("YT_COOKIES_FILE","").strip()
    return v or None

def _base_lang(code: Optional[str]) -> str:
    return (code or "").split("-")[0].lower()

def _listing_to_list(listing) -> List[object]:
    return list(listing)  # TranscriptList is iterable

def _build_available(listing) -> List[Dict]:
    items = _listing_to_list(listing)
    out: List[Dict] = []
    for t in items:
        code = getattr(t, "language_code", None)
        out.append({
            "language": getattr(t, "language", None),
            "language_code": code,
            "base_lang": _base_lang(code),
            "is_generated": bool(getattr(t, "is_generated", False)),
        })
    return out

def _choose_transcript(listing, preferred_langs: List[str], prefer_human: bool) -> Optional[Tuple[object, str]]:
    preferred_bases = {_base_lang(l) for l in preferred_langs}
    items = _listing_to_list(listing)
    manuals = [t for t in items if not bool(getattr(t, "is_generated", False))]
    autos   = [t for t in items if     bool(getattr(t, "is_generated", False))]

    def match_by_base(seq):
        return [t for t in seq if _base_lang(getattr(t, "language_code", None)) in preferred_bases]

    if prefer_human:
        mm = match_by_base(manuals)
        if mm: return mm[0], "manual:preferred_base"

    am = match_by_base(autos)
    if am: return am[0], "auto:preferred_base"

    if prefer_human and manuals: return manuals[0], "manual:any"
    if autos: return autos[0], "auto:any"
    return None

def _list_transcripts_resilient(video_id: str, cookies: Optional[str], attempts: int, delay_ms: int):
    last_err = None
    for i in range(1, attempts+1):
        try:
            return YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies)
        except (VideoUnavailable, TranscriptsDisabled, NoTranscriptFound):
            raise
        except ParseError as e:
            log.warning(f"[yt] ParseError on list_transcripts attempt {i} (consent/empty XML?): {e}")
            last_err = e
        except Exception as e:
            log.warning(f"[yt] list_transcripts transient attempt {i}: {e}")
            last_err = e
        time.sleep((delay_ms/1000.0) * i)
    raise RuntimeError(f"list_transcripts failed after {attempts} attempts: {last_err}")

def fetch_best_transcript(video_id: str) -> List[Dict]:
    langs = _langs()
    prefer_human = _env("YT_PREFER_HUMAN","true").lower() == "true"
    allow_any    = _env("YT_FALLBACK_ANY_LANG","true").lower() == "true"
    cookies      = _cookies_file()
    attempts     = int(_env("YT_RETRY_ATTEMPTS","3"))
    delay_ms     = int(_env("YT_RETRY_DELAY_MS","800"))

    listing = _list_transcripts_resilient(video_id, cookies, attempts, delay_ms)
    available = _build_available(listing)
    log.info(f"[yt] available tracks: {available}")

    chosen = _choose_transcript(listing, langs, prefer_human)
    if not chosen:
        if not allow_any:
            raise NoTranscriptAvailable(
                message=f"No transcript matched preferred languages; allow_any={allow_any}",
                requested_langs=langs, available=available
            )
        raise NoTranscriptAvailable(
            message="No transcript tracks available at all",
            requested_langs=langs, available=available
        )

    transcript_obj, reason = chosen
    log.info(f"[yt] chosen reason={reason} lang_code={getattr(transcript_obj,'language_code',None)} is_generated={getattr(transcript_obj,'is_generated',None)}")

    last_fetch_err = None
    for j in range(1, 4):  # 3 total attempts
        try:
            return transcript_obj.fetch()
        except ParseError as e:
            log.warning(f"[yt] ParseError on fetch attempt {j}: {e}")
            last_fetch_err = e
            if j < 3:
                time.sleep(0.5 * j)
    # After all retries failed, wrap in RuntimeError for clean route handling
    raise RuntimeError(f"Failed to fetch transcript after 3 attempts (consent/empty response): {last_fetch_err}")

def fetch_best_transcript_or_fallback(url: str, video_id: str) -> List[Dict]:
    use_ytdlp = _env("YT_USE_YTDLP_FALLBACK","true").lower() == "true"
    try:
        return fetch_best_transcript(video_id)
    except Exception as e:
        msg = str(e).lower()
        consent_like = any(k in msg for k in ["parseerror","consent","empty","failed to list transcripts"])
        if consent_like and use_ytdlp:
            try:
                from services.ytdlp_subs import fetch_subs_via_ytdlp
                log.info(f"[yt] Falling back to yt-dlp for {video_id}")
                return fetch_subs_via_ytdlp(url, lang_pref="en")
            except Exception as fallback_err:
                log.warning(f"[yt] yt-dlp fallback also failed: {fallback_err}")
                raise e  # Re-raise original error
        raise

