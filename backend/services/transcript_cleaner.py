"""
Transcript Cleaner Service

Cleans raw VTT/SRT transcripts using OpenAI to remove timestamps,
formatting artifacts, and produce readable text.

Security considerations:
- Input is truncated to prevent cost attacks
- Timeout configured for OpenAI calls
- Error handling for all OpenAI-related failures
"""

import os
import re
import logging
import httpx
from typing import Optional
from openai import OpenAI, RateLimitError, APITimeoutError, APIError, AuthenticationError

logger = logging.getLogger(__name__)

# Configuration
MAX_TRANSCRIPT_CHARS = int(os.getenv("MAX_TRANSCRIPT_CHARS", "50000"))  # ~12k tokens
OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))


class TranscriptCleaningError(Exception):
    """Raised when transcript cleaning fails."""
    pass


def get_openai_client() -> OpenAI:
    """
    Get OpenAI client with proper configuration.
    Includes timeout settings and custom HTTP client.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise TranscriptCleaningError("OpenAI API key not configured")
    
    # Create HTTP client with timeout
    http_client = httpx.Client(timeout=OPENAI_TIMEOUT_SECONDS)
    
    return OpenAI(api_key=api_key, http_client=http_client)


def clean_transcript_with_openai(raw_vtt: str) -> str:
    """
    Clean a raw VTT/SRT transcript using OpenAI.
    
    Removes:
    - Timestamps (00:00:00.000 --> 00:00:05.000)
    - VTT headers (WEBVTT, NOTE, etc.)
    - Duplicate lines
    - Formatting tags (<c>, <v>, etc.)
    
    Args:
        raw_vtt: Raw VTT/SRT content
        
    Returns:
        Cleaned, readable transcript text
        
    Raises:
        TranscriptCleaningError: If cleaning fails
    """
    if not raw_vtt or not raw_vtt.strip():
        raise TranscriptCleaningError("Empty transcript provided")
    
    # Truncate if too long (prevent cost attacks)
    original_length = len(raw_vtt)
    if len(raw_vtt) > MAX_TRANSCRIPT_CHARS:
        logger.warning(
            f"Truncating transcript from {original_length} to {MAX_TRANSCRIPT_CHARS} chars"
        )
        raw_vtt = raw_vtt[:MAX_TRANSCRIPT_CHARS]
    
    # First, try basic regex cleaning (faster, cheaper)
    cleaned = basic_clean_transcript(raw_vtt)
    
    # If basic cleaning produces reasonable output, use it
    if len(cleaned) > 100 and not needs_llm_cleaning(cleaned):
        logger.info(f"Basic cleaning sufficient: {len(cleaned)} chars")
        return cleaned
    
    # Use OpenAI for complex cleaning
    try:
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a transcript cleaner. Remove ALL timestamps, "
                        "formatting codes, speaker labels, and VTT/SRT artifacts. "
                        "Return ONLY the clean, readable text as natural paragraphs. "
                        "Preserve the original language. Do not summarize or modify content."
                    )
                },
                {
                    "role": "user",
                    "content": f"Clean this transcript:\n\n{raw_vtt}"
                }
            ],
            temperature=0.1,
            max_tokens=4000,
            timeout=OPENAI_TIMEOUT_SECONDS,
        )
        
        cleaned_text = response.choices[0].message.content.strip()
        
        if not cleaned_text:
            raise TranscriptCleaningError("OpenAI returned empty response")
        
        logger.info(f"OpenAI cleaned transcript: {original_length} -> {len(cleaned_text)} chars")
        return cleaned_text
        
    except RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded during transcript cleaning: {e}")
        raise TranscriptCleaningError("AI service rate limit exceeded. Please try again later.")
    except AuthenticationError as e:
        logger.error(f"OpenAI authentication failed: {e}")
        raise TranscriptCleaningError("AI service configuration error. Please contact support.")
    except APITimeoutError as e:
        logger.error(f"OpenAI timeout during transcript cleaning: {e}")
        raise TranscriptCleaningError("AI service timeout. Please try again.")
    except APIError as e:
        logger.error(f"OpenAI API error during transcript cleaning: {e}")
        raise TranscriptCleaningError("AI service error. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error during transcript cleaning: {e}")
        # Fall back to basic cleaning
        return basic_clean_transcript(raw_vtt)


def basic_clean_transcript(raw_vtt: str) -> str:
    """
    Basic regex-based transcript cleaning.
    Faster and cheaper than LLM, handles most common cases.
    """
    text = raw_vtt
    
    # Remove VTT header
    text = re.sub(r'^WEBVTT\s*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Kind:.*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Language:.*\n', '', text, flags=re.MULTILINE)
    
    # Remove NOTE sections
    text = re.sub(r'NOTE\s+.*?\n\n', '', text, flags=re.DOTALL)
    
    # Remove cue identifiers (numbered lines before timestamps)
    text = re.sub(r'^\d+\s*\n', '', text, flags=re.MULTILINE)
    
    # Remove timestamps (VTT format: 00:00:00.000 --> 00:00:05.000)
    text = re.sub(
        r'\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[.,]\d{3}.*?\n',
        '',
        text
    )
    
    # Remove SRT timestamps (00:00:00,000 --> 00:00:05,000)
    text = re.sub(
        r'\d{1,2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2},\d{3}.*?\n',
        '',
        text
    )
    
    # Remove positioning/styling tags
    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML-like tags
    text = re.sub(r'\{[^}]+\}', '', text)  # Remove ASS/SSA style tags
    text = re.sub(r'align:.*?(?=\n|$)', '', text)
    text = re.sub(r'position:.*?(?=\n|$)', '', text)
    
    # Remove speaker labels
    text = re.sub(r'^\[[^\]]+\]:\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[A-Z][A-Z\s]+:\s*', '', text, flags=re.MULTILINE)
    
    # Remove duplicate consecutive lines
    lines = text.split('\n')
    deduped = []
    prev_line = None
    for line in lines:
        line = line.strip()
        if line and line != prev_line:
            deduped.append(line)
            prev_line = line
    
    # Join and clean up whitespace
    result = ' '.join(deduped)
    result = re.sub(r'\s+', ' ', result)
    result = result.strip()
    
    return result


def needs_llm_cleaning(text: str) -> bool:
    """
    Heuristic to determine if basic cleaning is sufficient
    or if LLM cleaning is needed.
    """
    # Check for remaining timestamp-like patterns
    if re.search(r'\d{1,2}:\d{2}:\d{2}', text):
        return True
    
    # Check for remaining formatting artifacts
    if re.search(r'<[a-z]>', text, re.IGNORECASE):
        return True
    
    # Check for excessive repeated words (broken captions)
    words = text.split()
    if len(words) > 10:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:  # Too many repeated words
            return True
    
    return False

