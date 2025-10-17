"""
Deck helper service for managing YouTube → Deck parity.
Provides idempotent deck creation and card attachment functions.
"""
import logging
from typing import List, Optional
import sqlite3
import uuid

logger = logging.getLogger(__name__)

def get_or_create_deck_for_source(db_connection_string: str, source_label: str, title_hint: Optional[str] = None) -> str:
    """
    Get or create a deck for a YouTube source.
    
    Args:
        db_connection_string: SQLite database connection string
        source_label: Label for the source (e.g., "youtube | video_id | title")
        title_hint: Optional title hint for the deck
        
    Returns:
        deck_id: The ID of the deck (reusing existing pdfs.id as deck_id)
    """
    try:
        conn = sqlite3.connect(db_connection_string)
        cursor = conn.cursor()
        
        # Check if a deck already exists for this source
        cursor.execute(
            "SELECT id FROM pdfs WHERE filename = ? AND status = 'completed'",
            (source_label,)
        )
        existing_deck = cursor.fetchone()
        
        if existing_deck:
            deck_id = existing_deck[0]
            logger.info(f"Reusing existing deck {deck_id} for source: {source_label}")
            conn.close()
            return deck_id
        
        # Create a new deck
        deck_id = str(uuid.uuid4())
        
        # Insert source row as completed to mirror PDF completed state
        cursor.execute(
            "INSERT INTO pdfs (id, filename, status) VALUES (?, ?, ?)",
            (deck_id, source_label, "completed")
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created new deck {deck_id} for source: {source_label}")
        return deck_id
        
    except Exception as e:
        logger.error(f"Failed to get or create deck for source {source_label}: {e}")
        raise

def attach_cards_to_deck(db_connection_string: str, deck_id: str, cards_data: List[dict]) -> None:
    """
    Attach cards to a deck (idempotent).
    
    Args:
        db_connection_string: SQLite database connection string
        deck_id: The deck ID to attach cards to
        cards_data: List of card dictionaries with 'front' and 'back' keys
    """
    try:
        conn = sqlite3.connect(db_connection_string)
        cursor = conn.cursor()
        
        # Check existing cards for this deck to avoid duplicates
        cursor.execute(
            "SELECT question, answer FROM flashcards WHERE pdf_id = ?",
            (deck_id,)
        )
        existing_cards = {(row[0], row[1]) for row in cursor.fetchall()}
        
        # Insert only new cards
        new_cards_count = 0
        for idx, card in enumerate(cards_data, start=1):
            front = card.get('front', '').strip()
            back = card.get('back', '').strip()
            
            if not front or not back:
                continue
                
            # Skip if card already exists
            if (front, back) in existing_cards:
                continue
                
            cursor.execute(
                "INSERT INTO flashcards (pdf_id, question, answer, card_number) VALUES (?, ?, ?, ?)",
                (deck_id, front, back, idx)
            )
            new_cards_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"Attached {new_cards_count} new cards to deck {deck_id}")
        
    except Exception as e:
        logger.error(f"Failed to attach cards to deck {deck_id}: {e}")
        raise

