"""
YouTube transcript extraction service with API and fallback support.
Handles manual captions, auto-generated captions, and yt-dlp fallback.
"""
import os
import re
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse, parse_qs

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import JSONFormatter
except ImportError:
    YouTubeTranscriptApi = None

try:
    import webvtt
except ImportError:
    webvtt = None

logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> str:
    """Parse 11-char ID from standard youtu.be and youtube.com URLs."""
    # Handle youtu.be format
    if 'youtu.be/' in url:
        match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
    
    # Handle youtube.com format
    if 'youtube.com/' in url:
        match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
    
    # Handle youtube.com/embed format
    match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    raise ValueError(f"Could not extract video ID from URL: {url}")

def _time_to_seconds(time_str: str) -> float:
    """Convert HH:MM:SS.mmm format to seconds."""
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        elif len(parts) == 2:
            minutes, seconds = parts
            return float(minutes) * 60 + float(seconds)
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return 0.0

def list_transcripts(video_id: str, cookies: str = None) -> List[Dict]:
    """
    List available transcript tracks for a video.
    Returns list of dicts with 'lang' and 'is_generated' keys.
    """
    if YouTubeTranscriptApi is None:
        raise ImportError("youtube-transcript-api not installed")
    
    try:
        # Create API instance with cookies if provided
        api = YouTubeTranscriptApi(cookies=cookies) if cookies else YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        tracks = []
        
        # Get manual transcripts
        for transcript in transcript_list._manually_created_transcripts.values():
            tracks.append({
                'lang': transcript.language_code,
                'is_generated': False
            })
        
        # Get auto-generated transcripts
        for transcript in transcript_list._generated_transcripts.values():
            tracks.append({
                'lang': transcript.language_code,
                'is_generated': True
            })
        
        return tracks
        
    except Exception as e:
        logger.error(f"Failed to list transcripts for {video_id}: {e}")
        raise

def get_transcript_api(
    video_id: str, 
    langs: List[str] = None, 
    allow_auto: bool = True, 
    use_cookies: bool = False
) -> Tuple[List[Dict], str, List[str]]:
    """
    Use youtube-transcript-api to get transcript.
    Returns (segments, chosen_lang, warnings).
    """
    if YouTubeTranscriptApi is None:
        raise ImportError("youtube-transcript-api not installed")
    
    warnings = []
    cookies_path = None
    
    if use_cookies:
        cookies_path = os.getenv('YT_COOKIES_PATH')
        if not cookies_path or not Path(cookies_path).exists():
            warnings.append("use_cookies=true but YT_COOKIES_PATH not set or file doesn't exist")
            cookies_path = None
    
    # Normalize language hints: map any 'en-*' to 'en'
    normalized_langs = []
    for lang in (langs or ['en']):
        if lang.startswith('en-'):
            normalized_langs.append('en')
        else:
            normalized_langs.append(lang)
    
    # Remove duplicates while preserving order
    normalized_langs = list(dict.fromkeys(normalized_langs))
    
    try:
        # Get available transcripts
        api = YouTubeTranscriptApi(cookies=cookies_path) if cookies_path else YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # Try manual transcripts first
        for lang in normalized_langs:
            try:
                transcript = transcript_list.find_manually_created_transcript([lang])
                segments = transcript.fetch()
                chosen_lang = transcript.language_code
                logger.info(f"Found manual transcript for {video_id} in {chosen_lang}")
                return segments, chosen_lang, warnings
            except:
                continue
        
        # If no manual transcripts and auto is allowed, try auto-generated
        if allow_auto:
            for lang in normalized_langs:
                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    segments = transcript.fetch()
                    chosen_lang = transcript.language_code
                    warnings.append("Used auto-generated captions.")
                    logger.info(f"Found auto-generated transcript for {video_id} in {chosen_lang}")
                    return segments, chosen_lang, warnings
                except:
                    continue
        
        raise Exception("No suitable transcript found")
        
    except Exception as e:
        logger.error(f"Transcript API failed for {video_id}: {e}")
        raise

def get_transcript_fallback(video_url: str) -> Tuple[List[Dict], str, List[str]]:
    """
    Use yt-dlp to download/convert VTT captions to segments.
    Returns (segments, "en", warnings).
    """
    if webvtt is None:
        raise ImportError("webvtt-py not installed")
    
    warnings = ["Used yt-dlp+webvtt fallback."]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        vtt_file = temp_path / "captions.vtt"
        
        try:
            # Use yt-dlp to extract subtitles
            cmd = [
                'yt-dlp',
                '--write-auto-sub',
                '--write-sub',
                '--sub-langs', 'en,en-US,en-GB',
                '--skip-download',
                '--output', str(vtt_file.with_suffix('.%(ext)s')),
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
            
            if result.returncode != 0:
                raise Exception(f"yt-dlp failed: {result.stderr}")
            
            # Find the generated VTT file
            vtt_files = list(temp_path.glob("*.vtt"))
            if not vtt_files:
                raise Exception("No VTT files generated")
            
            vtt_file = vtt_files[0]  # Use first VTT file found
            
            # Parse VTT file
            captions = webvtt.read(str(vtt_file))
            
            segments = []
            for caption in captions:
                segments.append({
                    "text": caption.text.strip(),
                    "start": caption.start_in_seconds,
                    "end": caption.end_in_seconds
                })
            
            logger.info(f"Fallback extracted {len(segments)} segments from {video_id}")
            return segments, "en", warnings
            
        except Exception as e:
            logger.error(f"Fallback failed for {video_url}: {e}")
            raise Exception(f"Fallback failed: {str(e)}")

def get_transcript(
    video_url: str,
    langs: List[str] = None,
    allow_auto: bool = True,
    use_cookies: bool = False,
    enable_fallback: bool = False
) -> Tuple[List[Dict], str, List[str]]:
    """
    Main function to get transcript with fallback support.
    Returns (segments, chosen_lang, warnings).
    """
    video_id = extract_video_id(video_url)
    warnings = []
    
    # Try API first
    try:
        segments, chosen_lang, api_warnings = get_transcript_api(
            video_id, langs, allow_auto, use_cookies
        )
        warnings.extend(api_warnings)
        return segments, chosen_lang, warnings
        
    except Exception as e:
        logger.warning(f"API transcript failed for {video_id}: {e}")
        
        if enable_fallback:
            try:
                segments, chosen_lang, fallback_warnings = get_transcript_fallback(video_url)
                warnings.extend(fallback_warnings)
                return segments, chosen_lang, warnings
            except Exception as fallback_e:
                logger.error(f"Fallback also failed for {video_id}: {fallback_e}")
                raise Exception("No transcript available for this video/language. Try enable_fallback or provide cookies.")
        else:
            raise Exception("No transcript available for this video/language. Try enable_fallback or provide cookies.")
