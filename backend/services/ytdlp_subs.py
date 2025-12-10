"""
yt-dlp based YouTube subtitle and metadata fetching.

Provides robust subtitle extraction using yt-dlp binary (no API keys needed).
Uses tempfile for safe server/Docker operation.
"""
import os
import subprocess
import shutil
import tempfile
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    import webvtt
except ImportError:
    webvtt = None

logger = logging.getLogger(__name__)


class YTDlpError(Exception):
    """Custom exception for yt-dlp related errors with user-friendly messages."""
    pass


def _env(name: str, default: str = "") -> str:
    """Get environment variable with default."""
    v = os.getenv(name)
    return v if v is not None else default


def _get_ytdlp_binary() -> str:
    """Get yt-dlp binary path from env or default."""
    ytdlp = _env("YT_YTDLP_PATH", "yt-dlp")
    if shutil.which(ytdlp) is None:
        raise YTDlpError(
            "yt-dlp binary not found on server. "
            "Please install yt-dlp in the backend environment."
        )
    return ytdlp


def _get_cookies_arg() -> List[str]:
    """Get cookies argument if configured."""
    cookies = _env("YT_COOKIES_FILE", "").strip()
    if cookies and os.path.exists(cookies):
        return ["--cookies", cookies]
    return []


def fetch_youtube_metadata(url: str) -> Dict:
    """
    Fetch minimal metadata (id, title) for a YouTube video using yt-dlp.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Dict with 'id' and 'title' keys
        
    Raises:
        YTDlpError: If metadata extraction fails
    """
    ytdlp = _get_ytdlp_binary()
    
    cmd = [ytdlp, "--skip-download", "--print-json", "--no-warnings"]
    cmd.extend(_get_cookies_arg())
    cmd.append(url)
    
    logger.info(f"Fetching YouTube metadata for: {url[:80]}...")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )
    except subprocess.TimeoutExpired:
        raise YTDlpError("Timed out while fetching video metadata. Please try again.")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        logger.error(f"yt-dlp metadata error: {stderr}")
        
        # Parse common error patterns
        stderr_lower = stderr.lower()
        if "private video" in stderr_lower:
            raise YTDlpError("This video is private and cannot be accessed.")
        if "video unavailable" in stderr_lower or "not available" in stderr_lower:
            raise YTDlpError("This video is unavailable. It may have been removed or is restricted in your region.")
        if "age" in stderr_lower or "confirm your age" in stderr_lower:
            raise YTDlpError("This video requires age verification. Try providing cookies.")
        if "sign in" in stderr_lower or "members only" in stderr_lower:
            raise YTDlpError("This video requires sign-in or membership access.")
        
        raise YTDlpError(f"Failed to fetch video metadata: {stderr.strip()[:200] or 'unknown error'}")
    
    try:
        info = json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        raise YTDlpError("Failed to parse video metadata response.")
    
    video_id = info.get("id")
    title = info.get("title") or "YouTube video"
    
    if not video_id:
        raise YTDlpError("Could not extract video ID from yt-dlp metadata.")
    
    logger.info(f"Got metadata: id={video_id}, title={title[:50]}...")
    
    return {
        "id": video_id,
        "title": title,
        "channel": info.get("channel") or info.get("uploader"),
        "duration": info.get("duration"),
    }


def fetch_youtube_transcript_with_ytdlp(
    url: str, 
    lang: str = "en"
) -> Tuple[str, List[Dict]]:
    """
    Use yt-dlp to download auto-generated subtitles in VTT format for the given YouTube URL.
    
    Args:
        url: YouTube video URL
        lang: Language code for subtitles (default: "en")
        
    Returns:
        Tuple of:
            - full_text: single plain-text transcript string
            - segments: list of {"start": float, "end": float, "text": str}
            
    Raises:
        YTDlpError: With a human-readable message on failure
    """
    if webvtt is None:
        raise YTDlpError("webvtt-py library not installed. Cannot parse VTT subtitles.")
    
    ytdlp = _get_ytdlp_binary()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        output_template = str(tmp_path / "%(id)s.%(ext)s")
        
        # Try manual subtitles first, then auto-generated
        for sub_type, sub_flag in [("manual", "--write-subs"), ("auto", "--write-auto-subs")]:
            cmd = [
                ytdlp,
                "--skip-download",
                sub_flag,
                "--sub-langs", lang,
                "--sub-format", "vtt",
                "--no-warnings",
                "--output", output_template,
            ]
            cmd.extend(_get_cookies_arg())
            cmd.append(url)
            
            logger.info(f"Trying {sub_type} subtitles for: {url[:60]}...")
            
            try:
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout fetching {sub_type} subtitles")
                continue
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to fetch {sub_type} subtitles: {e.stderr[:200] if e.stderr else 'unknown'}")
                continue
            
            # Look for generated VTT files
            vtt_files = list(tmp_path.glob("*.vtt"))
            if vtt_files:
                logger.info(f"Found {len(vtt_files)} VTT file(s) using {sub_type} subtitles")
                break
        else:
            # Neither manual nor auto worked
            raise YTDlpError(
                f"No {lang} subtitles (manual or auto-generated) found for this video. "
                "The video may not have captions enabled."
            )
        
        # Parse the VTT file
        vtt_path = vtt_files[0]
        segments: List[Dict] = []
        full_text_parts: List[str] = []
        seen_texts = set()  # Deduplicate repeated captions
        
        try:
            for cue in webvtt.read(str(vtt_path)):
                text = cue.text.strip()
                if not text:
                    continue
                
                # Clean up text (remove duplicate lines common in auto-captions)
                clean_text = " ".join(text.split())
                
                # Skip if we've seen this exact text recently (auto-captions repeat)
                if clean_text in seen_texts:
                    continue
                seen_texts.add(clean_text)
                
                # Limit seen_texts size to avoid memory issues with long videos
                if len(seen_texts) > 1000:
                    seen_texts = set(list(seen_texts)[-500:])
                
                segments.append({
                    "start": cue.start_in_seconds,
                    "end": cue.end_in_seconds,
                    "text": clean_text,
                })
                full_text_parts.append(clean_text)
                
        except Exception as e:
            logger.error(f"Failed to parse VTT file: {e}")
            raise YTDlpError("Failed to parse subtitle file. The captions may be corrupted.")
        
        full_text = " ".join(full_text_parts).strip()
        
        if not full_text:
            raise YTDlpError("Transcript is empty after parsing VTT subtitles.")
        
        logger.info(f"Extracted {len(segments)} segments, {len(full_text)} chars of transcript")
        
        return full_text, segments


def fetch_raw_vtt_with_ytdlp(url: str, lang: str = "en") -> str:
    """
    Use yt-dlp to download auto-generated subtitles in VTT format for the given YouTube URL.
    Returns the raw VTT content as a string (with timestamps, not parsed).
    
    This is used for sending to OpenAI to clean up the transcript.
    
    Args:
        url: YouTube video URL
        lang: Language code for subtitles (default: "en")
        
    Returns:
        Raw VTT file content as string
        
    Raises:
        YTDlpError: With a human-readable message on failure
    """
    ytdlp = _get_ytdlp_binary()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        output_template = str(tmp_path / "%(id)s.%(ext)s")
        
        # Try manual subtitles first, then auto-generated
        for sub_type, sub_flag in [("manual", "--write-subs"), ("auto", "--write-auto-subs")]:
            cmd = [
                ytdlp,
                "--skip-download",
                sub_flag,
                "--sub-langs", lang,
                "--sub-format", "vtt",
                "--no-warnings",
                "--output", output_template,
            ]
            cmd.extend(_get_cookies_arg())
            cmd.append(url)
            
            logger.info(f"Fetching raw {sub_type} VTT subtitles for: {url[:60]}...")
            
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout fetching {sub_type} subtitles")
                continue
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to fetch {sub_type} subtitles: {e.stderr[:200] if e.stderr else 'unknown'}")
                continue
            
            # Look for generated VTT files
            vtt_files = list(tmp_path.glob("*.vtt"))
            if vtt_files:
                logger.info(f"Found VTT file using {sub_type} subtitles")
                break
        else:
            raise YTDlpError(
                f"No {lang} subtitles (manual or auto-generated) found for this video. "
                "The video may not have captions enabled."
            )
        
        # Read the raw VTT content
        vtt_path = vtt_files[0]
        try:
            raw_vtt = vtt_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Failed to read VTT file: {e}")
            raise YTDlpError("Failed to read subtitle file.")
        
        if not raw_vtt.strip():
            raise YTDlpError("Subtitle file is empty.")
        
        logger.info(f"Fetched raw VTT content: {len(raw_vtt)} characters")
        return raw_vtt


# Legacy function for backwards compatibility
def fetch_subs_via_ytdlp(url: str, lang_pref: str = "en") -> List[Dict]:
    """
    Legacy wrapper for backwards compatibility with existing code.
    
    Returns segments in the format expected by youtube_transcripts.py:
    [{"text": str, "start": float, "duration": float}, ...]
    """
    try:
        _, segments = fetch_youtube_transcript_with_ytdlp(url, lang=lang_pref)
        
        # Convert to legacy format with duration instead of end
        legacy_segments = []
        for seg in segments:
            legacy_segments.append({
                "text": seg["text"],
                "start": seg["start"],
                "duration": max(0.0, seg["end"] - seg["start"]),
            })
        
        return legacy_segments
        
    except YTDlpError as e:
        # Convert to RuntimeError for backwards compatibility
        raise RuntimeError(str(e))
