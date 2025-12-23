"""
Resource Ownership Verification (IDOR Protection)

Provides functions to verify user ownership of:
- Decks (deck_id)
- Sources/PDFs (source_id / pdf_id)
- Files

Prevents unauthorized access to resources via guessable IDs.
"""

import os
import logging
import requests
from typing import Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Feature flag: set to false to disable ownership checks (for dev/testing)
ENFORCE_OWNERSHIP = os.getenv("ENFORCE_OWNERSHIP", "true").lower() == "true"


def _get_supabase_headers() -> dict:
    """Get headers for Supabase REST API calls."""
    if not SUPABASE_SERVICE_ROLE_KEY:
        return {}
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def _get_base_url() -> str:
    """Get Supabase REST API base URL."""
    if not SUPABASE_URL:
        return ""
    if SUPABASE_URL.endswith("/rest/v1"):
        return SUPABASE_URL
    return f"{SUPABASE_URL}/rest/v1"


async def check_deck_owner(deck_id: str, user_id: str) -> bool:
    """
    Check if user owns the specified deck.
    
    Looks up user_decks table in Supabase.
    Returns True if user is owner, False otherwise.
    """
    if not ENFORCE_OWNERSHIP:
        return True
    
    if not deck_id or not user_id:
        return False
    
    # Anonymous users cannot own decks
    if user_id == "anonymous":
        return False
    
    base_url = _get_base_url()
    if not base_url:
        # Supabase not configured - allow access (local dev)
        logger.warning("Supabase not configured, skipping ownership check")
        return True
    
    try:
        url = f"{base_url}/user_decks"
        params = {
            "deck_id": f"eq.{deck_id}",
            "user_id": f"eq.{user_id}",
            "select": "deck_id"
        }
        
        resp = requests.get(url, headers=_get_supabase_headers(), params=params, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            return len(data) > 0
        else:
            logger.error(f"Supabase user_decks lookup failed: {resp.status_code} {resp.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking deck ownership: {e}")
        # On error, deny access (fail closed)
        return False


async def assert_deck_owner(deck_id: str, user_id: str):
    """
    Assert that user owns the deck. Raises 403 if not.
    
    Usage:
        await assert_deck_owner(deck_id, user_id)
        # If we get here, user owns the deck
    """
    if not ENFORCE_OWNERSHIP:
        return
    
    is_owner = await check_deck_owner(deck_id, user_id)
    
    if not is_owner:
        logger.warning(f"IDOR attempt: user {user_id} tried to access deck {deck_id}")
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "FORBIDDEN",
                "message": "You do not have access to this deck."
            }
        )


async def check_source_owner(source_id: str, user_id: str) -> bool:
    """
    Check if user owns the specified source (PDF/YouTube).
    
    Sources are linked to decks, so we check deck ownership.
    source_id == deck_id in this system.
    """
    return await check_deck_owner(source_id, user_id)


async def assert_source_owner(source_id: str, user_id: str):
    """
    Assert that user owns the source. Raises 403 if not.
    """
    if not ENFORCE_OWNERSHIP:
        return
    
    is_owner = await check_source_owner(source_id, user_id)
    
    if not is_owner:
        logger.warning(f"IDOR attempt: user {user_id} tried to access source {source_id}")
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "FORBIDDEN",
                "message": "You do not have access to this resource."
            }
        )


async def check_resource_access(
    resource_type: str,
    resource_id: str, 
    user_id: str,
    action: str = "read"
) -> bool:
    """
    Generic resource access check.
    
    Args:
        resource_type: "deck", "source", "pdf", "flashcards"
        resource_id: The resource ID
        user_id: The user ID
        action: "read", "write", "delete"
    
    Returns:
        True if access allowed, False otherwise
    """
    if not ENFORCE_OWNERSHIP:
        return True
    
    # Map resource types to ownership checks
    if resource_type in ("deck", "source", "pdf", "flashcards"):
        return await check_deck_owner(resource_id, user_id)
    
    # Unknown resource type - deny access
    logger.warning(f"Unknown resource type for ownership check: {resource_type}")
    return False


async def assert_resource_access(
    resource_type: str,
    resource_id: str,
    user_id: str,
    action: str = "read"
):
    """
    Assert user has access to resource. Raises 403 if not.
    """
    if not ENFORCE_OWNERSHIP:
        return
    
    has_access = await check_resource_access(resource_type, resource_id, user_id, action)
    
    if not has_access:
        logger.warning(
            f"IDOR attempt: user {user_id} tried to {action} {resource_type} {resource_id}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "FORBIDDEN",
                "message": f"You do not have permission to {action} this {resource_type}."
            }
        )

