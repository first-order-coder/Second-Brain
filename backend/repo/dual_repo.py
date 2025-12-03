import os
import logging
from contextlib import contextmanager
from typing import List, Any, Optional
import sqlite3
from sqlalchemy import text
from db.supabase_engine import SessionSupabase, SUPABASE_ENABLED

logger = logging.getLogger(__name__)

# Import Supabase REST helpers for flashcards
try:
    from repo.supabase_rest_flashcards import (
        get_pdf_status_from_supabase,
        upsert_pdf_in_supabase,
        get_flashcards_from_supabase,
        delete_flashcards_in_supabase,
        insert_flashcard_in_supabase,
        get_pdf_filename_from_supabase,
        update_pdf_status_in_supabase,
    )
    SUPABASE_REST_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Supabase REST helpers not available, falling back to SQLAlchemy: {e}")
    SUPABASE_REST_AVAILABLE = False

# Environment configuration
DB_READ_PRIMARY = os.getenv("DB_READ_PRIMARY", "sqlite").lower()
WRITE_SUPABASE = os.getenv("DB_WRITE_SUPABASE", "true").lower() == "true" and SUPABASE_ENABLED
WRITE_SQLITE = os.getenv("DB_WRITE_SQLITE", "true").lower() == "true"

# Log configuration on startup
logger.info(f"Database configuration: read_primary={DB_READ_PRIMARY}, write_sqlite={WRITE_SQLITE}, write_supabase={WRITE_SUPABASE}, supabase_enabled={SUPABASE_ENABLED}")

@contextmanager
def get_read_session():
    """Get read session based on DB_READ_PRIMARY setting"""
    if DB_READ_PRIMARY == "supabase" and SUPABASE_ENABLED:
        try:
            with SessionSupabase() as s:
                yield s
        except Exception as e:
            logger.warning(f"Supabase read failed, falling back to SQLite: {e}")
            # Fallback to SQLite
            conn = sqlite3.connect("pdf_flashcards.db")
            try:
                yield conn
            finally:
                conn.close()
    else:
        # Default to SQLite
        conn = sqlite3.connect("pdf_flashcards.db")
        try:
            yield conn
        finally:
            conn.close()

@contextmanager
def get_write_sessions():
    """Get write sessions for dual-write fanout"""
    sessions = []
    try:
        if WRITE_SQLITE:
            sqlite_conn = sqlite3.connect("pdf_flashcards.db")
            sessions.append(("sqlite", sqlite_conn))
        
        if WRITE_SUPABASE and SessionSupabase:
            supabase_session = SessionSupabase()
            sessions.append(("supabase", supabase_session))
        
        yield sessions
        
        # Commit all sessions
        for db_type, session in sessions:
            try:
                if db_type == "sqlite":
                    session.commit()
                else:  # supabase
                    session.commit()
            except Exception as e:
                logger.error(f"Failed to commit {db_type} session: {e}")
                raise
                
    except Exception as e:
        # Rollback all sessions on error
        for db_type, session in sessions:
            try:
                if db_type == "sqlite":
                    session.rollback()
                else:  # supabase
                    session.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback {db_type} session: {rollback_error}")
        raise
    finally:
        # Close all sessions
        for db_type, session in sessions:
            try:
                if db_type == "sqlite":
                    session.close()
                else:  # supabase
                    session.close()
            except Exception as close_error:
                logger.error(f"Failed to close {db_type} session: {close_error}")

def execute_dual_write_sql(sql: str, params: tuple = None) -> List[Any]:
    """Execute SQL on both databases and return results from primary"""
    if params is None:
        params = ()
    
    results = []
    with get_write_sessions() as sessions:
        for db_type, session in sessions:
            try:
                if db_type == "sqlite":
                    cursor = session.cursor()
                    cursor.execute(sql, params)
                    result = cursor.fetchall() if sql.strip().upper().startswith('SELECT') else cursor.lastrowid
                    results.append(result)
                else:  # supabase
                    # Convert SQLite-style placeholders (?) to PostgreSQL-style named parameters
                    pg_sql, params_dict = convert_sqlite_to_postgres(sql, params)
                    if params_dict:
                        result = session.execute(text(pg_sql), params_dict)
                    else:
                        result = session.execute(text(pg_sql))
                    if sql.strip().upper().startswith('SELECT'):
                        results.append(result.fetchall())
                    else:
                        # SQLAlchemy 2.x Result doesn't have lastrowid
                        # For INSERT/UPDATE/DELETE, use rowcount or None
                        results.append(result.rowcount if hasattr(result, 'rowcount') else None)
            except Exception as e:
                logger.error(f"Failed to execute SQL on {db_type}: {e}")
                raise
    
    # Return result from first session (usually SQLite for compatibility)
    return results[0] if results else None

def convert_sqlite_to_postgres(sql: str, params: tuple) -> tuple:
    """Convert SQLite-style placeholders to PostgreSQL-style with named parameters
    
    Returns:
        tuple: (converted_sql, params_dict) where params_dict is a dictionary
                with named parameters for SQLAlchemy 2.0
    """
    if not params:
        return (sql, {})
    
    # Convert ? placeholders to :param1, :param2, etc. and create a dict
    pg_sql = sql
    params_dict = {}
    for i in range(len(params)):
        param_name = f"param_{i+1}"
        pg_sql = pg_sql.replace('?', f':{param_name}', 1)
        params_dict[param_name] = params[i]
    
    return (pg_sql, params_dict)

def upsert_pdf(pdf_id: str, filename: str, status: str = "uploaded") -> str:
    """
    Upsert PDF record using Supabase REST API (authoritative source).
    
    NOTE: Supabase REST is now the single source of truth for flashcards and PDFs.
    SQLite writes are optional for local dev but Supabase REST is authoritative.
    """
    # Write to Supabase via REST (authoritative)
    if SUPABASE_REST_AVAILABLE:
        success = upsert_pdf_in_supabase(pdf_id, filename, status)
        if not success:
            logger.warning(f"Failed to upsert PDF {pdf_id} in Supabase via REST, continuing with SQLite fallback")
    
    # Optional: Also write to SQLite for local dev (non-authoritative)
    if WRITE_SQLITE:
        try:
            sqlite_sql = """
                INSERT OR REPLACE INTO pdfs (id, filename, status, upload_date) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """
            params = (pdf_id, filename, status)
            conn = sqlite3.connect("pdf_flashcards.db")
            try:
                cursor = conn.cursor()
                cursor.execute(sqlite_sql, params)
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"Failed to upsert PDF in SQLite (non-critical): {e}")
    
    return pdf_id

def upsert_flashcard(pdf_id: str, question: str, answer: str, card_number: int) -> int:
    """
    Insert flashcard record using Supabase REST API (authoritative source).
    
    NOTE: Supabase REST is now the single source of truth for flashcards.
    SQLite writes are optional for local dev but Supabase REST is authoritative.
    """
    # Write to Supabase via REST (authoritative)
    if SUPABASE_REST_AVAILABLE:
        success = insert_flashcard_in_supabase(pdf_id, question, answer, card_number)
        if not success:
            logger.warning(f"Failed to insert flashcard {card_number} for PDF {pdf_id} in Supabase via REST")
    
    # Optional: Also write to SQLite for local dev (non-authoritative)
    result = None
    if WRITE_SQLITE:
        try:
            sql = """
                INSERT INTO flashcards (pdf_id, question, answer, card_number) 
                VALUES (?, ?, ?, ?)
            """
            params = (pdf_id, question, answer, card_number)
            conn = sqlite3.connect("pdf_flashcards.db")
            try:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                result = cursor.lastrowid
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"Failed to insert flashcard in SQLite (non-critical): {e}")
    
    return result if result else card_number

def get_pdf_status(pdf_id: str) -> Optional[str]:
    """
    Get PDF status from Supabase REST API (authoritative source).
    
    NOTE: Supabase REST is now the single source of truth for flashcards and PDFs.
    Falls back to SQLite only if Supabase REST is unavailable.
    """
    # Try Supabase REST first (authoritative)
    if SUPABASE_REST_AVAILABLE:
        status = get_pdf_status_from_supabase(pdf_id)
        if status is not None:
            return status
        # If REST returns None, it means not found - don't fall back to SQLite
        # (we want Supabase to be the source of truth)
        return None
    
    # Fallback to SQLite only if REST is unavailable
    sql = "SELECT status FROM pdfs WHERE id = ?"
    params = (pdf_id,)
    
    with get_read_session() as session:
        if isinstance(session, sqlite3.Connection):
            cursor = session.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchone()
        else:  # supabase session
            pg_sql, params_dict = convert_sqlite_to_postgres(sql, params)
            if params_dict:
                result = session.execute(text(pg_sql), params_dict).fetchone()
            else:
                result = session.execute(text(pg_sql)).fetchone()
    
    return result[0] if result else None

def get_pdf_filename(pdf_id: str) -> Optional[str]:
    """
    Get PDF filename from Supabase REST API (authoritative source).
    
    NOTE: Supabase REST is now the single source of truth for flashcards and PDFs.
    Falls back to SQLite only if Supabase REST is unavailable.
    """
    # Try Supabase REST first (authoritative)
    if SUPABASE_REST_AVAILABLE:
        filename = get_pdf_filename_from_supabase(pdf_id)
        if filename is not None:
            return filename
        # If REST returns None, it means not found - don't fall back to SQLite
        return None
    
    # Fallback to SQLite only if REST is unavailable
    sql = "SELECT filename FROM pdfs WHERE id = ?"
    params = (pdf_id,)
    
    with get_read_session() as session:
        if isinstance(session, sqlite3.Connection):
            cursor = session.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchone()
        else:  # supabase session
            pg_sql, params_dict = convert_sqlite_to_postgres(sql, params)
            if params_dict:
                result = session.execute(text(pg_sql), params_dict).fetchone()
            else:
                result = session.execute(text(pg_sql)).fetchone()
    
    return result[0] if result else None

def get_flashcards(pdf_id: str) -> List[tuple]:
    """
    Get flashcards from Supabase REST API (authoritative source).
    
    Returns list of tuples in format: (id, pdf_id, question, answer, card_number)
    to maintain compatibility with existing code.
    
    NOTE: Supabase REST is now the single source of truth for flashcards.
    Falls back to SQLite only if Supabase REST is unavailable.
    """
    # Try Supabase REST first (authoritative)
    if SUPABASE_REST_AVAILABLE:
        flashcards_dicts = get_flashcards_from_supabase(pdf_id)
        # Convert dicts to tuples for compatibility: (id, pdf_id, question, answer, card_number)
        result = [
            (
                fc.get("id"),
                fc.get("pdf_id"),
                fc.get("question", ""),
                fc.get("answer", ""),
                fc.get("card_number", 0)
            )
            for fc in flashcards_dicts
        ]
        return result
    
    # Fallback to SQLite only if REST is unavailable
    sql = "SELECT * FROM flashcards WHERE pdf_id = ? ORDER BY card_number"
    params = (pdf_id,)
    
    with get_read_session() as session:
        if isinstance(session, sqlite3.Connection):
            cursor = session.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchall()
        else:  # supabase session
            pg_sql, params_dict = convert_sqlite_to_postgres(sql, params)
            if params_dict:
                result = session.execute(text(pg_sql), params_dict).fetchall()
            else:
                result = session.execute(text(pg_sql)).fetchall()
    
    return result

def delete_flashcards(pdf_id: str) -> None:
    """
    Delete flashcards for a PDF using Supabase REST API (authoritative source).
    
    NOTE: Supabase REST is now the single source of truth for flashcards.
    SQLite deletes are optional for local dev but Supabase REST is authoritative.
    """
    # Delete from Supabase via REST (authoritative)
    if SUPABASE_REST_AVAILABLE:
        success = delete_flashcards_in_supabase(pdf_id)
        if not success:
            logger.warning(f"Failed to delete flashcards for PDF {pdf_id} in Supabase via REST")
    
    # Optional: Also delete from SQLite for local dev (non-authoritative)
    if WRITE_SQLITE:
        try:
            sql = "DELETE FROM flashcards WHERE pdf_id = ?"
            params = (pdf_id,)
            conn = sqlite3.connect("pdf_flashcards.db")
            try:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"Failed to delete flashcards from SQLite (non-critical): {e}")

def update_pdf_status(pdf_id: str, status: str) -> None:
    """
    Update PDF status using Supabase REST API (authoritative source).
    
    NOTE: Supabase REST is now the single source of truth for PDFs.
    SQLite updates are optional for local dev but Supabase REST is authoritative.
    """
    # Update in Supabase via REST (authoritative)
    if SUPABASE_REST_AVAILABLE:
        success = update_pdf_status_in_supabase(pdf_id, status)
        if not success:
            logger.warning(f"Failed to update PDF {pdf_id} status to {status} in Supabase via REST")
    
    # Optional: Also update in SQLite for local dev (non-authoritative)
    if WRITE_SQLITE:
        try:
            sql = "UPDATE pdfs SET status = ? WHERE id = ?"
            params = (status, pdf_id)
            conn = sqlite3.connect("pdf_flashcards.db")
            try:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"Failed to update PDF status in SQLite (non-critical): {e}")

def create_deck_in_supabase(deck_id: str, title: str, source_type: str, source_label: Optional[str], user_id: str) -> bool:
    """
    Create a deck entry in Supabase decks and user_decks tables.
    
    Args:
        deck_id: The deck ID (typically the PDF ID)
        title: Human-readable deck title
        source_type: Source type (e.g., 'pdf', 'youtube')
        source_label: Source label (e.g., filename or YouTube title)
        user_id: Supabase auth user ID (UUID string)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not WRITE_SUPABASE or not SUPABASE_ENABLED:
        logger.warning("Supabase not enabled, skipping deck creation")
        return False
    
    try:
        with SessionSupabase() as session:
            # First, upsert the deck metadata
            deck_sql = """
                INSERT INTO public.decks (deck_id, title, source_type, source_label, created_at)
                VALUES (:deck_id, :title, :source_type, :source_label, NOW())
                ON CONFLICT (deck_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    source_type = EXCLUDED.source_type,
                    source_label = EXCLUDED.source_label
            """
            deck_params = {
                "deck_id": deck_id,
                "title": title,
                "source_type": source_type,
                "source_label": source_label
            }
            session.execute(text(deck_sql), deck_params)
            
            # Then, upsert the user_decks relationship
            user_deck_sql = """
                INSERT INTO public.user_decks (user_id, deck_id, role, created_at)
                VALUES (:user_id, :deck_id, 'owner', NOW())
                ON CONFLICT (user_id, deck_id) DO UPDATE SET
                    role = EXCLUDED.role
            """
            user_deck_params = {
                "user_id": user_id,
                "deck_id": deck_id
            }
            session.execute(text(user_deck_sql), user_deck_params)
            
            session.commit()
            logger.info(f"Successfully created deck {deck_id} in Supabase for user {user_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to create deck in Supabase for PDF {deck_id}: {e}")
        return False
