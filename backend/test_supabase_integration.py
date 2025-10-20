#!/usr/bin/env python3
"""
Test script for Supabase integration
Run this to verify dual-write functionality works correctly
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv()

from db.supabase_engine import SUPABASE_ENABLED, SessionSupabase
from repo.dual_repo import (
    upsert_pdf, upsert_flashcard, get_pdf_status, get_flashcards,
    DB_READ_PRIMARY, WRITE_SUPABASE, WRITE_SQLITE
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_supabase_connection():
    """Test Supabase connection"""
    logger.info("Testing Supabase connection...")
    
    if not SUPABASE_ENABLED:
        logger.warning("Supabase is not enabled. Skipping connection test.")
        return False
    
    try:
        with SessionSupabase() as s:
            result = s.execute("SELECT 1 as test").fetchone()
            logger.info(f"Supabase connection successful: {result}")
            return True
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")
        return False

def test_dual_write():
    """Test dual-write functionality"""
    logger.info("Testing dual-write functionality...")
    
    test_pdf_id = "test-supabase-integration-123"
    test_filename = "test-supabase.pdf"
    
    try:
        # Test PDF upsert
        logger.info("Testing PDF upsert...")
        upsert_pdf(test_pdf_id, test_filename, "test")
        
        # Test flashcard upsert
        logger.info("Testing flashcard upsert...")
        upsert_flashcard(test_pdf_id, "Test question?", "Test answer", 1)
        upsert_flashcard(test_pdf_id, "Another question?", "Another answer", 2)
        
        # Test read operations
        logger.info("Testing read operations...")
        status = get_pdf_status(test_pdf_id)
        logger.info(f"PDF status: {status}")
        
        flashcards = get_flashcards(test_pdf_id)
        logger.info(f"Found {len(flashcards)} flashcards")
        
        # Clean up test data
        logger.info("Cleaning up test data...")
        from repo.dual_repo import execute_dual_write_sql
        execute_dual_write_sql("DELETE FROM flashcards WHERE pdf_id = ?", (test_pdf_id,))
        execute_dual_write_sql("DELETE FROM pdfs WHERE id = ?", (test_pdf_id,))
        
        logger.info("✅ Dual-write test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Dual-write test failed: {e}")
        return False

def test_configuration():
    """Test configuration settings"""
    logger.info("Testing configuration...")
    
    logger.info(f"DB_READ_PRIMARY: {DB_READ_PRIMARY}")
    logger.info(f"WRITE_SQLITE: {WRITE_SQLITE}")
    logger.info(f"WRITE_SUPABASE: {WRITE_SUPABASE}")
    logger.info(f"SUPABASE_ENABLED: {SUPABASE_ENABLED}")
    
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    postgres_url = os.getenv("POSTGRES_URL")
    
    logger.info(f"SUPABASE_URL configured: {bool(supabase_url)}")
    logger.info(f"SUPABASE_SERVICE_ROLE_KEY configured: {bool(supabase_key)}")
    logger.info(f"POSTGRES_URL configured: {bool(postgres_url)}")
    
    return True

def main():
    """Main test function"""
    logger.info("Starting Supabase integration tests...")
    
    # Test configuration
    test_configuration()
    
    # Test Supabase connection
    supabase_ok = test_supabase_connection()
    
    # Test dual-write functionality
    dual_write_ok = test_dual_write()
    
    # Summary
    logger.info("=" * 50)
    logger.info("TEST SUMMARY:")
    logger.info(f"Configuration: ✅")
    logger.info(f"Supabase Connection: {'✅' if supabase_ok else '❌'}")
    logger.info(f"Dual-write Functionality: {'✅' if dual_write_ok else '❌'}")
    
    if supabase_ok and dual_write_ok:
        logger.info("🎉 All tests passed! Supabase integration is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the configuration and setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
