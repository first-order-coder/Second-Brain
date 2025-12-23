"""
Supabase Transcripts Repository

Handles storage of cleaned transcripts in Supabase.
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _get_headers() -> dict:
    """Get Supabase REST API headers."""
    if not SUPABASE_SERVICE_ROLE_KEY:
        return {}
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }


def _get_base_url() -> str:
    """Get Supabase REST API base URL."""
    if not SUPABASE_URL:
        return ""
    if SUPABASE_URL.endswith("/rest/v1"):
        return SUPABASE_URL
    return f"{SUPABASE_URL}/rest/v1"


def save_cleaned_transcript_to_supabase(
    deck_id: str,
    user_id: str,
    source_type: str,
    source_url: str,
    cleaned_transcript: str
) -> bool:
    """
    Save cleaned transcript to Supabase transcripts table.
    
    Args:
        deck_id: The deck ID (foreign key)
        user_id: The user ID
        source_type: Source type (e.g., 'youtube', 'pdf')
        source_url: Original source URL
        cleaned_transcript: The cleaned transcript text
    
    Returns:
        True if saved successfully, False otherwise
    """
    base_url = _get_base_url()
    if not base_url:
        logger.warning("Supabase not configured - transcript not saved")
        return False
    
    try:
        url = f"{base_url}/transcripts"
        payload = {
            "deck_id": deck_id,
            "user_id": user_id,
            "source_type": source_type,
            "source_url": source_url,
            "cleaned_text": cleaned_transcript[:100000],  # Limit size
        }
        
        resp = requests.post(
            url,
            headers=_get_headers(),
            json=payload,
            timeout=10
        )
        
        if resp.status_code in (200, 201, 204):
            logger.info(f"Saved transcript for deck {deck_id}")
            return True
        elif resp.status_code == 409:
            # Conflict - transcript already exists, try update
            logger.info(f"Transcript exists for deck {deck_id}, updating...")
            update_url = f"{base_url}/transcripts?deck_id=eq.{deck_id}"
            update_resp = requests.patch(
                update_url,
                headers=_get_headers(),
                json={"cleaned_text": cleaned_transcript[:100000]},
                timeout=10
            )
            return update_resp.status_code in (200, 204)
        else:
            logger.error(f"Failed to save transcript: {resp.status_code} {resp.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error saving transcript: {e}")
        return False


def get_transcript_from_supabase(deck_id: str) -> Optional[str]:
    """
    Retrieve cleaned transcript from Supabase.
    
    Args:
        deck_id: The deck ID
    
    Returns:
        The cleaned transcript text, or None if not found
    """
    base_url = _get_base_url()
    if not base_url:
        return None
    
    try:
        url = f"{base_url}/transcripts"
        params = {
            "deck_id": f"eq.{deck_id}",
            "select": "cleaned_text"
        }
        
        resp = requests.get(
            url,
            headers=_get_headers(),
            params=params,
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                return data[0].get("cleaned_text")
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving transcript: {e}")
        return None

