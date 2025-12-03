"""
Supabase REST API helpers for flashcards table only.

This module uses Supabase's PostgREST API over HTTPS to read/write flashcards.
It ONLY works with the `flashcards` table (not `pdfs`).

Important: In Supabase, `deck_id` is used (which equals `pdf_id` in the backend).
"""

import os
import requests
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def _base_rest_url() -> str:
    """
    Returns the base REST URL.
    If SUPABASE_URL already ends with '/rest/v1', don't append it again.
    Otherwise, append '/rest/v1'.
    """
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not set")
    if SUPABASE_URL.endswith("/rest/v1"):
        return SUPABASE_URL
    return f"{SUPABASE_URL}/rest/v1"

def _headers() -> Dict[str, str]:
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not set")
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        # default: return representation so we can see rows
        "Prefer": "return=representation",
    }

def insert_flashcard_in_supabase(deck_id: str, question: str, answer: str, card_number: int) -> None:
    """
    Insert a single flashcard into public.flashcards.
    Logs success or failure; never raises.
    """
    try:
        url = f"{_base_rest_url()}/flashcards"
        payload = {
            "deck_id": deck_id,
            "question": question,
            "answer": answer,
            "card_number": card_number,
        }
        resp = requests.post(url, headers=_headers(), json=payload, timeout=10)
        if resp.status_code not in (200, 201):
            logger.error(
                "Supabase insert_flashcard failed: status=%s body=%s payload=%s",
                resp.status_code,
                resp.text,
                payload,
            )
        else:
            logger.info("Supabase insert_flashcard OK: deck_id=%s card_number=%s", deck_id, card_number)
    except Exception as e:
        logger.error("Supabase insert_flashcard exception for deck_id=%s: %s", deck_id, e)

def delete_flashcards_in_supabase(deck_id: str) -> None:
    """
    Delete all flashcards for a deck_id. Logs errors, never raises.
    """
    try:
        url = f"{_base_rest_url()}/flashcards"
        params = {"deck_id": f"eq.{deck_id}"}
        headers = _headers()
        headers["Prefer"] = "return=minimal"
        resp = requests.delete(url, headers=headers, params=params, timeout=10)
        if resp.status_code not in (200, 204):
            logger.error(
                "Supabase delete_flashcards failed: status=%s body=%s deck_id=%s",
                resp.status_code,
                resp.text,
                deck_id,
            )
        else:
            logger.info("Supabase delete_flashcards OK: deck_id=%s", deck_id)
    except Exception as e:
        logger.error("Supabase delete_flashcards exception for deck_id=%s: %s", deck_id, e)

def get_flashcards_from_supabase(deck_id: str) -> List[Dict]:
    """
    Get all flashcards for a given deck_id, ordered by card_number.
    Returns [] on error and logs the problem.
    """
    try:
        url = f"{_base_rest_url()}/flashcards"
        params = {
            "deck_id": f"eq.{deck_id}",
            "select": "id,question,answer,card_number",
            "order": "card_number.asc",
        }
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        if resp.status_code != 200:
            logger.error(
                "Supabase get_flashcards failed: status=%s body=%s deck_id=%s",
                resp.status_code,
                resp.text,
                deck_id,
            )
            return []
        rows = resp.json()
        logger.info("Supabase get_flashcards OK: deck_id=%s count=%s", deck_id, len(rows))
        return rows
    except Exception as e:
        logger.error("Supabase get_flashcards exception for deck_id=%s: %s", deck_id, e)
        return []
