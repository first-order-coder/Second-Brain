"""
Supabase REST API helpers for flashcards table only.

This module uses Supabase's PostgREST API over HTTPS to read/write flashcards.
It ONLY works with the `flashcards` table (not `pdfs`).

Important: In Supabase, `deck_id` is used (which equals `pdf_id` in the backend).
"""

import os
import logging
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def _headers() -> Dict[str, str]:
    """Get headers for Supabase REST API requests"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase environment variables missing: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
    
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

def insert_flashcard_in_supabase(deck_id: str, question: str, answer: str, card_number: int) -> None:
    """
    Insert a single flashcard into Supabase flashcards table.
    
    Args:
        deck_id: The deck ID (same as pdf_id in backend)
        question: Flashcard question text
        answer: Flashcard answer text
        card_number: Card number (1-indexed)
    """
    try:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/flashcards"
        payload = {
            "deck_id": deck_id,
            "question": question,
            "answer": answer,
            "card_number": card_number,
        }
        resp = requests.post(url, headers=_headers(), json=payload, timeout=10)
        if resp.status_code not in (200, 201):
            logger.error(f"Supabase insert_flashcard failed ({resp.status_code}): {resp.text}")
    except Exception as e:
        logger.error(f"Supabase insert_flashcard exception: {e}")

def delete_flashcards_in_supabase(deck_id: str) -> None:
    """
    Delete all flashcards for a deck from Supabase.
    
    Args:
        deck_id: The deck ID (same as pdf_id in backend)
    """
    try:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/flashcards"
        params = {"deck_id": f"eq.{deck_id}"}
        headers = _headers()
        headers["Prefer"] = "return=minimal"
        resp = requests.delete(url, headers=headers, params=params, timeout=10)
        if resp.status_code not in (200, 204):
            logger.error(f"Supabase delete_flashcards failed ({resp.status_code}): {resp.text}")
    except Exception as e:
        logger.error(f"Supabase delete_flashcards exception: {e}")

def get_flashcards_from_supabase(deck_id: str) -> List[Dict]:
    """
    Get all flashcards for a deck from Supabase.
    
    Args:
        deck_id: The deck ID (same as pdf_id in backend)
    
    Returns:
        List of flashcard dictionaries with keys: id, question, answer, card_number
        Returns empty list if not found or on error.
    """
    try:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/flashcards"
        params = {
            "deck_id": f"eq.{deck_id}",
            "select": "id,question,answer,card_number",
            "order": "card_number.asc",
        }
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        if resp.status_code != 200:
            logger.error(f"Supabase get_flashcards failed ({resp.status_code}): {resp.text}")
            return []
        return resp.json()
    except Exception as e:
        logger.error(f"Supabase get_flashcards exception: {e}")
        return []
