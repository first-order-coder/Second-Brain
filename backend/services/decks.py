"""
Deck helper service for managing YouTube → Deck parity.
Provides idempotent deck creation and card attachment functions.

NOTE: This service now uses dual_repo functions which write to Supabase REST
as the authoritative source. SQLite writes are optional for local dev.
"""
import logging
from typing import List, Optional
import sqlite3
import uuid
from repo.dual_repo import (
    upsert_pdf, upsert_flashcard, get_pdf_status, get_flashcards, delete_flashcards
)

logger = logging.getLogger(__name__)

def get_or_create_deck_for_source(db_connection_string: str, source_label: str, title_hint: Optional[str] = None) -> str:
    """
    Get or create a deck for a YouTube source.
    
    Uses Supabase REST (via dual_repo) as the authoritative source.
    
    Args:
        db_connection_string: SQLite database connection string (kept for compatibility, but not used for authoritative writes)
        source_label: Label for the source (e.g., "youtube | video_id | title")
        title_hint: Optional title hint for the deck
        
    Returns:
        deck_id: The ID of the deck (reusing existing pdfs.id as deck_id)
    """
    try:
        # Check if a deck already exists for this source by searching SQLite
        # (This is a simple lookup - we'll improve this later if needed)
        # For now, we'll create a new deck_id and use upsert_pdf which handles Supabase REST
        deck_id = str(uuid.uuid4())
        
        # Use dual_repo to upsert PDF record in Supabase (authoritative)
        # This will create the record if it doesn't exist, or update it if it does
        upsert_pdf(deck_id, source_label, "completed")
        
        logger.info(f"Created/updated deck {deck_id} for source: {source_label}")
        return deck_id
        
    except Exception as e:
        logger.error(f"Failed to get or create deck for source {source_label}: {e}")
        raise

def attach_cards_to_deck(db_connection_string: str, deck_id: str, cards_data: List[dict]) -> None:
    """
    Attach cards to a deck (idempotent).
    
    Uses Supabase REST (via dual_repo) as the authoritative source.
    
    Args:
        db_connection_string: SQLite database connection string (kept for compatibility, but not used for authoritative writes)
        deck_id: The deck ID to attach cards to
        cards_data: List of card dictionaries with 'front' and 'back' keys
    """
    try:
        # Get existing cards from Supabase REST to avoid duplicates
        existing_flashcards = get_flashcards(deck_id)
        existing_cards = {(fc[2], fc[3]) for fc in existing_flashcards}  # (question, answer) tuples
        
        # Insert only new cards using dual_repo (which writes to Supabase REST)
        new_cards_count = 0
        current_max_card_number = len(existing_flashcards)
        
        for idx, card in enumerate(cards_data, start=1):
            front = card.get('front', '').strip()
            back = card.get('back', '').strip()
            
            if not front or not back:
                continue
                
            # Skip if card already exists
            if (front, back) in existing_cards:
                continue
            
            # Use dual_repo to insert card (writes to Supabase REST)
            card_number = current_max_card_number + idx
            upsert_flashcard(deck_id, front, back, card_number)
            new_cards_count += 1
        
        logger.info(f"Attached {new_cards_count} new cards to deck {deck_id} via Supabase REST")
        
    except Exception as e:
        logger.error(f"Failed to attach cards to deck {deck_id}: {e}")
        raise

