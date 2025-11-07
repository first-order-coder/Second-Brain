import os
import logging
from contextlib import contextmanager
from typing import List, Any, Optional
import sqlite3
from sqlalchemy import text
from db.supabase_engine import SessionSupabase, SUPABASE_ENABLED

logger = logging.getLogger(__name__)

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
                        result = session.execute(text(pg_sql), **params_dict)
                    else:
                        result = session.execute(text(pg_sql))
                    if sql.strip().upper().startswith('SELECT'):
                        results.append(result.fetchall())
                    else:
                        results.append(result.lastrowid)
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
    """Upsert PDF record in both databases"""
    sql = """
        INSERT INTO pdfs (id, filename, status, upload_date) 
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET 
            filename = excluded.filename,
            status = excluded.status
    """
    params = (pdf_id, filename, status)
    
    with get_write_sessions() as sessions:
        for db_type, session in sessions:
            try:
                if db_type == "sqlite":
                    # SQLite doesn't support ON CONFLICT, use INSERT OR REPLACE
                    sqlite_sql = """
                        INSERT OR REPLACE INTO pdfs (id, filename, status, upload_date) 
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """
                    cursor = session.cursor()
                    cursor.execute(sqlite_sql, params)
                else:  # supabase
                    pg_sql, params_dict = convert_sqlite_to_postgres(sql, params)
                    if params_dict:
                        session.execute(text(pg_sql), **params_dict)
                    else:
                        session.execute(text(pg_sql))
            except Exception as e:
                logger.error(f"Failed to upsert PDF on {db_type}: {e}")
                raise
    
    return pdf_id

def upsert_flashcard(pdf_id: str, question: str, answer: str, card_number: int) -> int:
    """Upsert flashcard record in both databases"""
    sql = """
        INSERT INTO flashcards (pdf_id, question, answer, card_number) 
        VALUES (?, ?, ?, ?)
    """
    params = (pdf_id, question, answer, card_number)
    
    with get_write_sessions() as sessions:
        for db_type, session in sessions:
            try:
                if db_type == "sqlite":
                    cursor = session.cursor()
                    cursor.execute(sql, params)
                    result = cursor.lastrowid
                else:  # supabase
                    pg_sql, params_dict = convert_sqlite_to_postgres(sql, params)
                    if params_dict:
                        result = session.execute(text(pg_sql), **params_dict)
                    else:
                        result = session.execute(text(pg_sql))
                    result = result.lastrowid
            except Exception as e:
                logger.error(f"Failed to upsert flashcard on {db_type}: {e}")
                raise
    
    return result

def get_pdf_status(pdf_id: str) -> Optional[str]:
    """Get PDF status from primary read database"""
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
                result = session.execute(text(pg_sql), **params_dict).fetchone()
            else:
                result = session.execute(text(pg_sql)).fetchone()
    
    return result[0] if result else None

def get_flashcards(pdf_id: str) -> List[tuple]:
    """Get flashcards from primary read database"""
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
                result = session.execute(text(pg_sql), **params_dict).fetchall()
            else:
                result = session.execute(text(pg_sql)).fetchall()
    
    return result

def delete_flashcards(pdf_id: str) -> None:
    """Delete flashcards for a PDF from both databases"""
    sql = "DELETE FROM flashcards WHERE pdf_id = ?"
    params = (pdf_id,)
    
    with get_write_sessions() as sessions:
        for db_type, session in sessions:
            try:
                if db_type == "sqlite":
                    cursor = session.cursor()
                    cursor.execute(sql, params)
                else:  # supabase
                    pg_sql, params_dict = convert_sqlite_to_postgres(sql, params)
                    if params_dict:
                        session.execute(text(pg_sql), **params_dict)
                    else:
                        session.execute(text(pg_sql))
            except Exception as e:
                logger.error(f"Failed to delete flashcards on {db_type}: {e}")
                raise
