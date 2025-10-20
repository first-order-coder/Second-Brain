#!/usr/bin/env python3
"""
Backfill script to copy data from SQLite to Supabase
Run this once after setting up Supabase to migrate existing data
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import sqlite3
from backend.db.supabase_engine import SessionSupabase, SUPABASE_ENABLED
from backend.models import Summary, SummarySentence, SummarySentenceCitation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def copy_table_data(table_name: str, copy_func):
    """Copy data from SQLite to Supabase for a specific table"""
    logger.info(f"Copying {table_name}...")
    count = copy_func()
    logger.info(f"Copied {count} records from {table_name}")
    return count

def copy_pdfs():
    """Copy PDFs from SQLite to Supabase"""
    count = 0
    with sqlite3.connect("pdf_flashcards.db") as sqlite_conn, SessionSupabase() as supabase_session:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, filename, upload_date, status FROM pdfs")
        
        for row in cursor.fetchall():
            pdf_id, filename, upload_date, status = row
            
            # Check if already exists
            existing = supabase_session.execute(
                "SELECT id FROM pdfs WHERE id = %s", (pdf_id,)
            ).fetchone()
            
            if not existing:
                supabase_session.execute(
                    """
                    INSERT INTO pdfs (id, filename, upload_date, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (pdf_id, filename, upload_date, status, upload_date, upload_date)
                )
                count += 1
        
        supabase_session.commit()
    return count

def copy_flashcards():
    """Copy flashcards from SQLite to Supabase"""
    count = 0
    with sqlite3.connect("pdf_flashcards.db") as sqlite_conn, SessionSupabase() as supabase_session:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, pdf_id, question, answer, card_number FROM flashcards")
        
        for row in cursor.fetchall():
            flashcard_id, pdf_id, question, answer, card_number = row
            
            # Check if already exists
            existing = supabase_session.execute(
                "SELECT id FROM flashcards WHERE id = %s", (flashcard_id,)
            ).fetchone()
            
            if not existing:
                supabase_session.execute(
                    """
                    INSERT INTO flashcards (id, pdf_id, question, answer, card_number, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    (flashcard_id, pdf_id, question, answer, card_number)
                )
                count += 1
        
        supabase_session.commit()
    return count

def copy_summaries():
    """Copy summaries from SQLite to Supabase using SQLAlchemy models"""
    count = 0
    with sqlite3.connect("pdf_flashcards.db") as sqlite_conn, SessionSupabase() as supabase_session:
        # Get summaries from SQLAlchemy (they're stored in the same SQLite DB)
        summaries = supabase_session.query(Summary).all()
        
        for summary in summaries:
            # Check if already exists in Supabase
            existing = supabase_session.execute(
                "SELECT id FROM summaries WHERE id = %s", (summary.id,)
            ).fetchone()
            
            if not existing:
                supabase_session.execute(
                    """
                    INSERT INTO summaries (id, source_id, text, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (summary.id, summary.source_id, summary.text, summary.created_at, summary.updated_at)
                )
                count += 1
        
        supabase_session.commit()
    return count

def copy_summary_sentences():
    """Copy summary sentences from SQLite to Supabase"""
    count = 0
    with sqlite3.connect("pdf_flashcards.db") as sqlite_conn, SessionSupabase() as supabase_session:
        sentences = supabase_session.query(SummarySentence).all()
        
        for sentence in sentences:
            existing = supabase_session.execute(
                "SELECT id FROM summary_sentences WHERE id = %s", (sentence.id,)
            ).fetchone()
            
            if not existing:
                supabase_session.execute(
                    """
                    INSERT INTO summary_sentences (id, summary_id, order_index, sentence_text, support_status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (sentence.id, sentence.summary_id, sentence.order_index, sentence.sentence_text, sentence.support_status, sentence.created_at)
                )
                count += 1
        
        supabase_session.commit()
    return count

def copy_summary_citations():
    """Copy summary citations from SQLite to Supabase"""
    count = 0
    with sqlite3.connect("pdf_flashcards.db") as sqlite_conn, SessionSupabase() as supabase_session:
        citations = supabase_session.query(SummarySentenceCitation).all()
        
        for citation in citations:
            existing = supabase_session.execute(
                "SELECT id FROM summary_sentence_citations WHERE id = %s", (citation.id,)
            ).fetchone()
            
            if not existing:
                supabase_session.execute(
                    """
                    INSERT INTO summary_sentence_citations (id, sentence_id, chunk_id, start_char, end_char, score, preview_text, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (citation.id, citation.sentence_id, citation.chunk_id, citation.start_char, citation.end_char, citation.score, citation.preview_text, citation.created_at)
                )
                count += 1
        
        supabase_session.commit()
    return count

def verify_data_integrity():
    """Verify that data was copied correctly"""
    logger.info("Verifying data integrity...")
    
    with sqlite3.connect("pdf_flashcards.db") as sqlite_conn, SessionSupabase() as supabase_session:
        # Check PDFs
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT COUNT(*) FROM pdfs")
        sqlite_pdf_count = sqlite_cursor.fetchone()[0]
        
        supabase_pdf_count = supabase_session.execute("SELECT COUNT(*) FROM pdfs").fetchone()[0]
        
        logger.info(f"PDFs: SQLite={sqlite_pdf_count}, Supabase={supabase_pdf_count}")
        
        # Check flashcards
        sqlite_cursor.execute("SELECT COUNT(*) FROM flashcards")
        sqlite_flashcard_count = sqlite_cursor.fetchone()[0]
        
        supabase_flashcard_count = supabase_session.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0]
        
        logger.info(f"Flashcards: SQLite={sqlite_flashcard_count}, Supabase={supabase_flashcard_count}")
        
        # Check summaries
        sqlite_cursor.execute("SELECT COUNT(*) FROM summaries")
        sqlite_summary_count = sqlite_cursor.fetchone()[0]
        
        supabase_summary_count = supabase_session.execute("SELECT COUNT(*) FROM summaries").fetchone()[0]
        
        logger.info(f"Summaries: SQLite={sqlite_summary_count}, Supabase={supabase_summary_count}")
        
        if (sqlite_pdf_count == supabase_pdf_count and 
            sqlite_flashcard_count == supabase_flashcard_count and
            sqlite_summary_count == supabase_summary_count):
            logger.info("✅ Data integrity check passed!")
            return True
        else:
            logger.error("❌ Data integrity check failed!")
            return False

def main():
    """Main backfill function"""
    if not SUPABASE_ENABLED:
        logger.error("Supabase is not enabled. Please configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        sys.exit(1)
    
    logger.info("Starting backfill from SQLite to Supabase...")
    
    try:
        # Copy data in order (respecting foreign key constraints)
        total_copied = 0
        total_copied += copy_table_data("pdfs", copy_pdfs)
        total_copied += copy_table_data("flashcards", copy_flashcards)
        total_copied += copy_table_data("summaries", copy_summaries)
        total_copied += copy_table_data("summary_sentences", copy_summary_sentences)
        total_copied += copy_table_data("summary_sentence_citations", copy_summary_citations)
        
        logger.info(f"Total records copied: {total_copied}")
        
        # Verify data integrity
        if verify_data_integrity():
            logger.info("🎉 Backfill completed successfully!")
        else:
            logger.error("❌ Backfill completed with integrity issues!")
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"Backfill failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
