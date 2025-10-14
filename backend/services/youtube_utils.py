import re
from typing import Optional

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
