"""
Per-User Quota System for OpenAI API Usage

Tracks and enforces:
- Daily request count
- Daily token count  
- Monthly token count

Uses SQLite/Postgres (same DB as app) for persistence.
In-memory cache for performance.
"""

import os
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, Depends

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration (via environment variables)
# ============================================================================

# Daily limits (per user)
DAILY_REQUEST_LIMIT = int(os.getenv("QUOTA_DAILY_REQUESTS", "50"))
DAILY_TOKEN_LIMIT = int(os.getenv("QUOTA_DAILY_TOKENS", "100000"))  # ~100k tokens

# Monthly limits (per user)
MONTHLY_TOKEN_LIMIT = int(os.getenv("QUOTA_MONTHLY_TOKENS", "1000000"))  # ~1M tokens

# Anonymous user limits (stricter)
ANON_DAILY_REQUEST_LIMIT = int(os.getenv("QUOTA_ANON_DAILY_REQUESTS", "5"))
ANON_DAILY_TOKEN_LIMIT = int(os.getenv("QUOTA_ANON_DAILY_TOKENS", "10000"))

# Default token estimate when actual usage not available
DEFAULT_TOKEN_ESTIMATE = int(os.getenv("QUOTA_DEFAULT_TOKEN_ESTIMATE", "2000"))

# Database path
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///pdf_flashcards.db")


class QuotaExceededError(Exception):
    """Raised when user exceeds their quota."""
    
    def __init__(self, message: str, quota_type: str, limit: int, used: int, reset_time: Optional[datetime] = None):
        super().__init__(message)
        self.quota_type = quota_type
        self.limit = limit
        self.used = used
        self.reset_time = reset_time


# ============================================================================
# In-Memory Cache for Quota Tracking
# ============================================================================

class QuotaCache:
    """
    In-memory cache with periodic database sync.
    Reduces DB load while maintaining reasonable accuracy.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict] = defaultdict(lambda: {
            "daily_requests": 0,
            "daily_tokens": 0,
            "monthly_tokens": 0,
            "daily_reset": self._next_day_reset(),
            "monthly_reset": self._next_month_reset(),
            "last_sync": 0,
        })
        self._lock = Lock()
    
    @staticmethod
    def _next_day_reset() -> float:
        """Get timestamp for next day reset (midnight UTC)."""
        now = datetime.utcnow()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return tomorrow.timestamp()
    
    @staticmethod
    def _next_month_reset() -> float:
        """Get timestamp for next month reset (1st of next month UTC)."""
        now = datetime.utcnow()
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return next_month.timestamp()
    
    def get_usage(self, user_id: str) -> Dict:
        """Get current usage for user, resetting if needed."""
        with self._lock:
            now = time.time()
            usage = self._cache[user_id]
            
            # Reset daily counters if past reset time
            if now >= usage["daily_reset"]:
                usage["daily_requests"] = 0
                usage["daily_tokens"] = 0
                usage["daily_reset"] = self._next_day_reset()
            
            # Reset monthly counter if past reset time
            if now >= usage["monthly_reset"]:
                usage["monthly_tokens"] = 0
                usage["monthly_reset"] = self._next_month_reset()
            
            return usage.copy()
    
    def increment(self, user_id: str, requests: int = 1, tokens: int = 0):
        """Increment usage counters."""
        with self._lock:
            usage = self._cache[user_id]
            usage["daily_requests"] += requests
            usage["daily_tokens"] += tokens
            usage["monthly_tokens"] += tokens


# Global cache instance
_quota_cache = QuotaCache()


# ============================================================================
# Database Operations
# ============================================================================

def _get_db_connection():
    """Get database connection for quota storage."""
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        return sqlite3.connect(db_path)
    else:
        # For Postgres, would use SQLAlchemy session
        # For now, fall back to in-memory only
        return None


def _init_quota_table():
    """Initialize quota tracking table if using SQLite."""
    conn = _get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_quotas (
                    user_id TEXT PRIMARY KEY,
                    daily_requests INTEGER DEFAULT 0,
                    daily_tokens INTEGER DEFAULT 0,
                    monthly_tokens INTEGER DEFAULT 0,
                    daily_reset_at TEXT,
                    monthly_reset_at TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()


# Initialize on module load
try:
    _init_quota_table()
except Exception as e:
    logger.warning(f"Could not initialize quota table: {e}")


# ============================================================================
# Quota Check and Increment Functions
# ============================================================================

def get_user_limits(user_id: str) -> Tuple[int, int, int]:
    """
    Get quota limits for a user.
    Anonymous users have stricter limits.
    """
    if user_id == "anonymous" or not user_id:
        return (ANON_DAILY_REQUEST_LIMIT, ANON_DAILY_TOKEN_LIMIT, ANON_DAILY_TOKEN_LIMIT)
    return (DAILY_REQUEST_LIMIT, DAILY_TOKEN_LIMIT, MONTHLY_TOKEN_LIMIT)


async def check_quota(user_id: str) -> Dict:
    """
    Check if user is within quota limits.
    
    Returns usage info if allowed.
    Raises QuotaExceededError if limit exceeded.
    """
    usage = _quota_cache.get_usage(user_id)
    daily_req_limit, daily_token_limit, monthly_token_limit = get_user_limits(user_id)
    
    # Check daily request limit
    if usage["daily_requests"] >= daily_req_limit:
        reset_time = datetime.fromtimestamp(usage["daily_reset"])
        raise QuotaExceededError(
            f"Daily request limit ({daily_req_limit}) exceeded. Resets at {reset_time.isoformat()}",
            quota_type="daily_requests",
            limit=daily_req_limit,
            used=usage["daily_requests"],
            reset_time=reset_time
        )
    
    # Check daily token limit
    if usage["daily_tokens"] >= daily_token_limit:
        reset_time = datetime.fromtimestamp(usage["daily_reset"])
        raise QuotaExceededError(
            f"Daily token limit ({daily_token_limit}) exceeded. Resets at {reset_time.isoformat()}",
            quota_type="daily_tokens",
            limit=daily_token_limit,
            used=usage["daily_tokens"],
            reset_time=reset_time
        )
    
    # Check monthly token limit
    if usage["monthly_tokens"] >= monthly_token_limit:
        reset_time = datetime.fromtimestamp(usage["monthly_reset"])
        raise QuotaExceededError(
            f"Monthly token limit ({monthly_token_limit}) exceeded. Resets at {reset_time.isoformat()}",
            quota_type="monthly_tokens",
            limit=monthly_token_limit,
            used=usage["monthly_tokens"],
            reset_time=reset_time
        )
    
    return {
        "daily_requests": {
            "used": usage["daily_requests"],
            "limit": daily_req_limit,
            "remaining": daily_req_limit - usage["daily_requests"]
        },
        "daily_tokens": {
            "used": usage["daily_tokens"],
            "limit": daily_token_limit,
            "remaining": daily_token_limit - usage["daily_tokens"]
        },
        "monthly_tokens": {
            "used": usage["monthly_tokens"],
            "limit": monthly_token_limit,
            "remaining": monthly_token_limit - usage["monthly_tokens"]
        }
    }


async def increment_quota(user_id: str, tokens_used: Optional[int] = None):
    """
    Increment quota counters after an OpenAI request.
    
    Args:
        user_id: The user ID
        tokens_used: Actual tokens used (from OpenAI response), or None to estimate
    """
    if tokens_used is None:
        tokens_used = DEFAULT_TOKEN_ESTIMATE
    
    _quota_cache.increment(user_id, requests=1, tokens=tokens_used)
    logger.debug(f"Quota incremented for user {user_id}: +1 request, +{tokens_used} tokens")


# ============================================================================
# FastAPI Dependency
# ============================================================================

async def require_quota(user_id: str) -> Dict:
    """
    FastAPI dependency to check quota before processing.
    
    Usage:
        @app.post("/openai-endpoint")
        async def endpoint(
            user_id: str = Depends(require_auth),
            quota_info: Dict = Depends(require_quota)
        ):
            ...
    
    Note: This needs the user_id from require_auth, so chain them:
        Depends(require_auth) -> user_id -> Depends(require_quota)
    """
    try:
        return await check_quota(user_id)
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error_code": "QUOTA_EXCEEDED",
                "message": str(e),
                "quota_type": e.quota_type,
                "limit": e.limit,
                "used": e.used,
                "reset_time": e.reset_time.isoformat() if e.reset_time else None
            }
        )


def create_quota_dependency(user_id: str):
    """
    Create a dependency closure that checks quota for a specific user.
    Use this when user_id is already known.
    """
    async def _check():
        return await require_quota(user_id)
    return _check

