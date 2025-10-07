"""
Simple database migration script to add missing columns
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def migrate_database():
    """Add missing columns to existing tables"""
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    
    try:
        # Check if preview_text column exists in summary_sentence_citations
        cursor.execute("PRAGMA table_info(summary_sentence_citations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'preview_text' not in columns:
            log.info("Adding preview_text column to summary_sentence_citations table")
            cursor.execute("ALTER TABLE summary_sentence_citations ADD COLUMN preview_text TEXT")
            conn.commit()
            log.info("✅ Added preview_text column")
        else:
            log.info("✅ preview_text column already exists")
        
        # Check if support_status has correct default
        cursor.execute("PRAGMA table_info(summary_sentences)")
        columns = cursor.fetchall()
        support_status_col = None
        for col in columns:
            if col[1] == 'support_status':
                support_status_col = col
                break
        
        if support_status_col and support_status_col[4] != 'insufficient':
            log.info("Support status column exists but may need default value update")
            # SQLite doesn't support changing column defaults easily, so we'll leave it as is
            # The application code handles the default value
        
        log.info("✅ Database migration completed successfully")
        
    except Exception as e:
        log.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
