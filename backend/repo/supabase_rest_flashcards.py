"""
Supabase REST API helpers for flashcards and PDFs.

This module uses Supabase's PostgREST API over HTTPS to read/write flashcards
and PDF metadata. This avoids direct Postgres connections (psycopg) which have
caused production issues (connection errors, IPv6 host problems, etc.).

Supabase REST is the single source of truth for flashcards. The local SQLite DB
is no longer used for flashcards and can be safely ignored for that purpose.
"""

import os
import logging
import requests
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

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
        "Prefer": "return=representation"  # Return inserted/updated rows
    }

def _get_rest_url(table: str) -> str:
    """Get the full REST API URL for a table"""
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL not configured")
    
    # Remove trailing slash if present
    base_url = SUPABASE_URL.rstrip('/')
    return f"{base_url}/rest/v1/{table}"

def get_pdf_status_from_supabase(pdf_id: str) -> Optional[str]:
    """
    Get PDF status from Supabase using REST API.
    
    Args:
        pdf_id: The PDF ID (UUID string)
    
    Returns:
        Status string (e.g., "uploaded", "processing", "completed") or None if not found
    """
    try:
        url = _get_rest_url("pdfs")
        headers = _headers()
        
        # Query: GET /rest/v1/pdfs?id=eq.<pdf_id>&select=status&limit=1
        params = {
            "id": f"eq.{pdf_id}",
            "select": "status",
            "limit": "1"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0].get("status")
            return None
        elif response.status_code == 404:
            return None
        else:
            logger.error(f"Failed to get PDF status from Supabase: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error getting PDF status from Supabase: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting PDF status from Supabase: {e}")
        return None

def upsert_pdf_in_supabase(pdf_id: str, filename: str, status: str = "uploaded") -> bool:
    """
    Upsert PDF record in Supabase using REST API.
    
    Args:
        pdf_id: The PDF ID (UUID string)
        filename: PDF filename
        status: Status (e.g., "uploaded", "processing", "completed")
    
    Returns:
        True if successful, False otherwise
    """
    try:
        url = _get_rest_url("pdfs")
        headers = _headers()
        
        # Use POST with upsert (ON CONFLICT) via Prefer header
        payload = {
            "id": pdf_id,
            "filename": filename,
            "status": status,
            "upload_date": datetime.utcnow().isoformat() + "Z"
        }
        
        # Use upsert: POST with Prefer: resolution=merge-duplicates
        headers_upsert = headers.copy()
        headers_upsert["Prefer"] = "resolution=merge-duplicates,return=representation"
        
        response = requests.post(url, headers=headers_upsert, json=payload, timeout=10)
        
        if response.status_code in (200, 201):
            logger.info(f"Successfully upserted PDF {pdf_id} in Supabase")
            return True
        else:
            logger.error(f"Failed to upsert PDF in Supabase: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error upserting PDF in Supabase: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error upserting PDF in Supabase: {e}")
        return False

def get_flashcards_from_supabase(pdf_id: str) -> List[Dict[str, Any]]:
    """
    Get all flashcards for a PDF from Supabase using REST API.
    
    Args:
        pdf_id: The PDF ID (UUID string)
    
    Returns:
        List of flashcard dictionaries with keys: id, pdf_id, question, answer, card_number
        Returns empty list if not found or on error.
    """
    try:
        url = _get_rest_url("flashcards")
        headers = _headers()
        
        # Query: GET /rest/v1/flashcards?pdf_id=eq.<pdf_id>&select=id,question,answer,card_number&order=card_number.asc
        params = {
            "pdf_id": f"eq.{pdf_id}",
            "select": "id,pdf_id,question,answer,card_number",
            "order": "card_number.asc"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Convert to list of dicts
            flashcards = []
            for item in data:
                flashcards.append({
                    "id": str(item.get("id")),  # Convert UUID to string
                    "pdf_id": str(item.get("pdf_id")),
                    "question": item.get("question", ""),
                    "answer": item.get("answer", ""),
                    "card_number": item.get("card_number", 0)
                })
            return flashcards
        elif response.status_code == 404:
            return []
        else:
            logger.error(f"Failed to get flashcards from Supabase: {response.status_code} - {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error getting flashcards from Supabase: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting flashcards from Supabase: {e}")
        return []

def delete_flashcards_in_supabase(pdf_id: str) -> bool:
    """
    Delete all flashcards for a PDF from Supabase using REST API.
    
    Args:
        pdf_id: The PDF ID (UUID string)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        url = _get_rest_url("flashcards")
        headers = _headers()
        
        # DELETE /rest/v1/flashcards?pdf_id=eq.<pdf_id>
        params = {
            "pdf_id": f"eq.{pdf_id}"
        }
        
        response = requests.delete(url, headers=headers, params=params, timeout=10)
        
        if response.status_code in (200, 204):
            logger.info(f"Successfully deleted flashcards for PDF {pdf_id} from Supabase")
            return True
        else:
            logger.error(f"Failed to delete flashcards from Supabase: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error deleting flashcards from Supabase: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting flashcards from Supabase: {e}")
        return False

def insert_flashcard_in_supabase(pdf_id: str, question: str, answer: str, card_number: int) -> bool:
    """
    Insert a single flashcard into Supabase using REST API.
    
    Args:
        pdf_id: The PDF ID (UUID string)
        question: Flashcard question text
        answer: Flashcard answer text
        card_number: Card number (1-indexed)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        url = _get_rest_url("flashcards")
        headers = _headers()
        
        payload = {
            "pdf_id": pdf_id,
            "question": question,
            "answer": answer,
            "card_number": card_number
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code in (200, 201):
            logger.debug(f"Successfully inserted flashcard {card_number} for PDF {pdf_id} in Supabase")
            return True
        else:
            logger.error(f"Failed to insert flashcard in Supabase: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error inserting flashcard in Supabase: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error inserting flashcard in Supabase: {e}")
        return False

def get_pdf_filename_from_supabase(pdf_id: str) -> Optional[str]:
    """
    Get PDF filename from Supabase using REST API.
    
    Args:
        pdf_id: The PDF ID (UUID string)
    
    Returns:
        Filename string or None if not found
    """
    try:
        url = _get_rest_url("pdfs")
        headers = _headers()
        
        params = {
            "id": f"eq.{pdf_id}",
            "select": "filename",
            "limit": "1"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0].get("filename")
            return None
        elif response.status_code == 404:
            return None
        else:
            logger.error(f"Failed to get PDF filename from Supabase: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error getting PDF filename from Supabase: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting PDF filename from Supabase: {e}")
        return None

def update_pdf_status_in_supabase(pdf_id: str, status: str) -> bool:
    """
    Update PDF status in Supabase using REST API (PATCH).
    
    Args:
        pdf_id: The PDF ID (UUID string)
        status: New status (e.g., "processing", "completed", "error")
    
    Returns:
        True if successful, False otherwise
    """
    try:
        url = _get_rest_url("pdfs")
        headers = _headers()
        
        # Use PATCH to update only the status field
        # PATCH /rest/v1/pdfs?id=eq.<pdf_id>
        params = {
            "id": f"eq.{pdf_id}"
        }
        payload = {
            "status": status
        }
        
        response = requests.patch(url, headers=headers, params=params, json=payload, timeout=10)
        
        if response.status_code in (200, 204):
            logger.debug(f"Successfully updated PDF {pdf_id} status to {status} in Supabase")
            return True
        else:
            logger.error(f"Failed to update PDF status in Supabase: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error updating PDF status in Supabase: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating PDF status in Supabase: {e}")
        return False

