from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

# Environment variables
POSTGRES_URL = os.getenv("POSTGRES_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Check if Supabase is enabled
SUPABASE_ENABLED = bool(SUPABASE_URL) and bool(SUPABASE_SERVICE_ROLE_KEY) and bool(POSTGRES_URL)

if SUPABASE_ENABLED:
    try:
        # Create Supabase engine with connection pooling
        engine_supabase = create_engine(
            POSTGRES_URL, 
            pool_pre_ping=True, 
            future=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600
        )
        SessionSupabase = sessionmaker(bind=engine_supabase, autoflush=False, autocommit=False)
        logger.info("Supabase engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase engine: {e}")
        engine_supabase = None
        SessionSupabase = None
        SUPABASE_ENABLED = False
else:
    engine_supabase = None
    SessionSupabase = None
    logger.info("Supabase not enabled - missing environment variables")

# Log configuration on startup
logger.info(f"Supabase configuration: enabled={SUPABASE_ENABLED}, url_configured={bool(SUPABASE_URL)}, key_configured={bool(SUPABASE_SERVICE_ROLE_KEY)}, postgres_url_configured={bool(POSTGRES_URL)}")
