import re
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

_PATTERNS = [
    r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_\-]{6,})',
    r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([A-Za-z0-9_\-]{6,})',
    r'(?:https?://)?(?:www\.)?youtu\.be/([A-Za-z0-9_\-]{6,})',
    r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_\-]{6,})',
]
_RX = [re.compile(p) for p in _PATTERNS]

def extract_video_id(url: str) -> Optional[str]:
    url = url.split('&')[0].split('?t=')[0].split('#')[0]
    for rx in _RX:
        m = rx.search(url)
        if m:
            return m.group(1)
    return None

def clean_youtube_url(raw_url: str) -> str:
    """
    Clean and normalize YouTube URLs.
    Fixes duplicated URLs and normalizes various YouTube URL formats.
    """
    s = raw_url.strip()
    
    # Fix "urlurl" duplication
    if len(s) % 2 == 0:
        half = len(s) // 2
        if s[:half] == s[half:]:
            s = s[:half]
    
    parsed = urlparse(s)
    
    # Normalize youtu.be → youtube.com/watch?v=...
    if parsed.netloc in {"youtu.be", "m.youtu.be"}:
        video_id = parsed.path.lstrip("/")
        if video_id:
            query = urlencode({"v": video_id})
            return f"https://www.youtube.com/watch?{query}"
    
    # Normalize youtube.com/watch
    if parsed.netloc in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            v = qs.get("v", [None])[0]
            if v:
                query = urlencode({"v": v})
                return f"https://www.youtube.com/watch?{query}"
        elif parsed.path.startswith("/shorts/"):
            video_id = parsed.path.replace("/shorts/", "").split("/")[0]
            if video_id:
                query = urlencode({"v": video_id})
                return f"https://www.youtube.com/watch?{query}"
    
    return s
