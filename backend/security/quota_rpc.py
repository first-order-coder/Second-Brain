"""
Supabase RPC-Based Quota Enforcement

This module provides race-safe quota enforcement using Supabase's
consume_quota() RPC function for atomic check-and-increment operations.

SECURITY:
- Quota check runs BEFORE any OpenAI call or expensive preprocessing
- Authentication is required for all quota-protected endpoints
- Uses atomic RPC to prevent race conditions
- Falls back safely if Supabase is unavailable
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Header

from security.auth import require_auth
from services.supabase_client import consume_quota, SUPABASE_CONFIGURED

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration (via environment variables)
# ============================================================================

# Default quota limits
DAILY_REQUEST_LIMIT = int(os.getenv("QUOTA_DAILY_REQUESTS", "50"))
MONTHLY_TOKEN_LIMIT = int(os.getenv("QUOTA_MONTHLY_TOKENS", "2000000"))
QUOTA_RESERVED_TOKENS = int(os.getenv("QUOTA_RESERVED_TOKENS", "2000"))

# Anonymous user limits (stricter)
ANON_DAILY_REQUEST_LIMIT = int(os.getenv("QUOTA_ANON_DAILY_REQUESTS", "5"))
ANON_MONTHLY_TOKEN_LIMIT = int(os.getenv("QUOTA_ANON_MONTHLY_TOKENS", "10000"))

# Fallback behavior when Supabase is unavailable
QUOTA_FALLBACK_ALLOW = os.getenv("QUOTA_FALLBACK_ALLOW", "false").lower() == "true"


class QuotaExceededError(Exception):
    """Raised when user exceeds their quota."""
    
    def __init__(
        self,
        message: str,
        reason: str = "unknown",
        daily_used: int = 0,
        monthly_used: int = 0,
        daily_limit: int = 0,
        monthly_limit: int = 0
    ):
        super().__init__(message)
        self.reason = reason
        self.daily_used = daily_used
        self.monthly_used = monthly_used
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit


class QuotaCheckError(Exception):
    """Raised when quota check fails (RPC error, etc.)."""
    pass


# ============================================================================
# Quota Enforcement Functions
# ============================================================================

def get_user_limits(user_id: str) -> tuple:
    """
    Get quota limits for a user.
    Anonymous users have stricter limits.
    
    Returns:
        (daily_request_limit, monthly_token_limit, reserved_tokens)
    """
    if user_id == "anonymous" or not user_id:
        return (ANON_DAILY_REQUEST_LIMIT, ANON_MONTHLY_TOKEN_LIMIT, QUOTA_RESERVED_TOKENS)
    return (DAILY_REQUEST_LIMIT, MONTHLY_TOKEN_LIMIT, QUOTA_RESERVED_TOKENS)


async def enforce_quota_rpc(user_id: str) -> Dict[str, Any]:
    """
    Enforce quota using Supabase RPC (atomic check + increment).
    
    This function:
    1. Calls the consume_quota RPC function
    2. If allowed, the quota has already been consumed (atomic)
    3. If denied, raises QuotaExceededError
    
    Args:
        user_id: The authenticated user's ID
        
    Returns:
        Dict with quota usage info
        
    Raises:
        QuotaExceededError: If quota is exceeded
        QuotaCheckError: If quota check fails
    """
    if not user_id:
        raise QuotaCheckError("User ID required for quota check")
    
    daily_limit, monthly_limit, reserved_tokens = get_user_limits(user_id)
    
    try:
        result = consume_quota(
            user_id=user_id,
            reserved_tokens=reserved_tokens,
            daily_request_limit=daily_limit,
            monthly_token_limit=monthly_limit
        )
        
        # Check if this was a fallback (Supabase not configured)
        if result.get("fallback"):
            logger.warning(f"Quota check using fallback for user {user_id}")
            return {
                "allowed": True,
                "daily_requests_used": 0,
                "monthly_tokens_used": 0,
                "fallback": True
            }
        
        allowed = result.get("allowed", False)
        reason = result.get("reason")
        daily_used = result.get("daily_requests_used", 0)
        monthly_used = result.get("monthly_tokens_used", 0)
        
        if not allowed:
            logger.warning(
                f"Quota exceeded for user {user_id}: reason={reason}, "
                f"daily={daily_used}/{daily_limit}, monthly={monthly_used}/{monthly_limit}"
            )
            raise QuotaExceededError(
                message=f"Quota exceeded: {reason or 'limit reached'}",
                reason=reason or "limit_exceeded",
                daily_used=daily_used,
                monthly_used=monthly_used,
                daily_limit=daily_limit,
                monthly_limit=monthly_limit
            )
        
        logger.debug(
            f"Quota check passed for user {user_id}: "
            f"daily={daily_used}/{daily_limit}, monthly={monthly_used}/{monthly_limit}"
        )
        
        return {
            "allowed": True,
            "daily_requests_used": daily_used,
            "daily_requests_limit": daily_limit,
            "monthly_tokens_used": monthly_used,
            "monthly_tokens_limit": monthly_limit,
        }
        
    except QuotaExceededError:
        raise  # Re-raise quota exceeded
    except Exception as e:
        logger.error(f"Quota check failed for user {user_id}: {e}")
        
        if QUOTA_FALLBACK_ALLOW:
            # Allow but log warning
            logger.warning(f"Allowing request despite quota check failure (fallback enabled)")
            return {
                "allowed": True,
                "fallback": True,
                "error": str(e)
            }
        else:
            # Deny on error (fail closed)
            raise QuotaCheckError(f"Quota check failed: {str(e)}")


# ============================================================================
# FastAPI Dependency
# ============================================================================

async def enforce_quota(
    user_id: str = Depends(require_auth)
) -> str:
    """
    FastAPI dependency that enforces quota before processing.
    
    This dependency:
    1. Requires authentication (via require_auth)
    2. Checks and consumes quota atomically
    3. Returns user_id if allowed
    4. Raises HTTPException if quota exceeded or check fails
    
    Usage:
        @app.post("/expensive-endpoint")
        async def endpoint(user_id: str = Depends(enforce_quota)):
            # Quota already consumed, proceed with OpenAI call
            ...
    """
    try:
        await enforce_quota_rpc(user_id)
        return user_id
        
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error_code": "QUOTA_EXCEEDED",
                "message": str(e),
                "reason": e.reason,
                "daily_used": e.daily_used,
                "daily_limit": e.daily_limit,
                "monthly_used": e.monthly_used,
                "monthly_limit": e.monthly_limit
            }
        )
        
    except QuotaCheckError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "QUOTA_CHECK_FAILED",
                "message": "Quota check failed. Please try again later."
            }
        )


# ============================================================================
# Utility Functions
# ============================================================================

async def get_quota_status(user_id: str) -> Dict[str, Any]:
    """
    Get current quota status without consuming quota.
    Useful for UI display.
    """
    from services.supabase_client import get_user_quota_status
    
    daily_limit, monthly_limit, _ = get_user_limits(user_id)
    status = get_user_quota_status(user_id)
    
    return {
        "user_id": user_id,
        "daily": {
            "used": status.get("daily_requests_used", 0),
            "limit": daily_limit,
            "remaining": max(0, daily_limit - status.get("daily_requests_used", 0))
        },
        "monthly": {
            "used": status.get("monthly_tokens_used", 0),
            "limit": monthly_limit,
            "remaining": max(0, monthly_limit - status.get("monthly_tokens_used", 0))
        }
    }

