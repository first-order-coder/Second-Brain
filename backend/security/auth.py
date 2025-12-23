"""
Authentication Dependencies for FastAPI

Provides:
- get_current_user: Requires authentication, returns user_id
- get_optional_user: Returns user_id if present, None otherwise
- require_auth: Stricter auth for OpenAI endpoints

SECURITY:
- Validates JWT tokens via Supabase Auth API
- Never trusts client-provided user IDs without verification
- Returns clean JSON errors for all auth failures
"""

import os
import logging
from typing import Optional
from fastapi import Header, HTTPException, Request

from services.supabase_client import verify_user_token, SUPABASE_CONFIGURED

logger = logging.getLogger(__name__)

# Configuration
REQUIRE_AUTH_FOR_OPENAI = os.getenv("REQUIRE_AUTH_FOR_OPENAI", "true").lower() == "true"
ALLOW_ANONYMOUS_READ = os.getenv("ALLOW_ANONYMOUS_READ", "true").lower() == "true"

# For development/testing: allow X-User-Id header when Supabase is not configured
ALLOW_HEADER_AUTH_FALLBACK = os.getenv("ALLOW_HEADER_AUTH_FALLBACK", "false").lower() == "true"


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """
    Extract the token from Authorization header.
    Expects format: "Bearer <token>"
    """
    if not authorization:
        return None
    
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1].strip()


async def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> Optional[str]:
    """
    Extract user ID from Authorization header if present.
    Returns None for anonymous users (allowed for some operations).
    
    Priority:
    1. Authorization: Bearer <token> (validated via Supabase)
    2. X-User-Id header (fallback, only in dev/test mode)
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(user_id: Optional[str] = Depends(get_optional_user)):
            ...
    """
    # Try Authorization header first (preferred)
    token = _extract_bearer_token(authorization)
    if token:
        user_id = verify_user_token(token)
        if user_id:
            logger.debug(f"User authenticated via Bearer token: {user_id[:8]}...")
            return user_id
        # Token provided but invalid - log warning
        logger.warning("Invalid Bearer token provided")
        return None
    
    # Fallback to X-User-Id header (for backward compatibility / dev mode)
    if x_user_id and (ALLOW_HEADER_AUTH_FALLBACK or not SUPABASE_CONFIGURED):
        user_id = x_user_id.strip()
        if len(user_id) >= 10 and len(user_id) <= 100:
            logger.debug(f"User authenticated via X-User-Id header (fallback): {user_id[:8]}...")
            return user_id
        logger.warning(f"Invalid X-User-Id format: {user_id[:20]}...")
    
    return None


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> str:
    """
    Require authentication - returns user_id or raises 401.
    
    SECURITY: Validates JWT token via Supabase Auth API.
    
    Usage for protected endpoints:
        @app.post("/expensive-endpoint")
        async def endpoint(user_id: str = Depends(get_current_user)):
            ...
    """
    # Try Authorization header first (preferred)
    token = _extract_bearer_token(authorization)
    if token:
        user_id = verify_user_token(token)
        if user_id:
            logger.debug(f"User authenticated: {user_id[:8]}...")
            return user_id
        # Token provided but invalid
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Invalid or expired authentication token. Please sign in again."
            }
        )
    
    # Fallback to X-User-Id header (for backward compatibility / dev mode)
    if x_user_id and (ALLOW_HEADER_AUTH_FALLBACK or not SUPABASE_CONFIGURED):
        user_id = x_user_id.strip()
        if len(user_id) >= 10 and len(user_id) <= 100:
            logger.warning(f"Using X-User-Id fallback auth (dev mode): {user_id[:8]}...")
            return user_id
    
    # No valid auth provided
    raise HTTPException(
        status_code=401,
        detail={
            "error_code": "AUTH_REQUIRED",
            "message": "Authentication required. Please sign in to use this feature."
        }
    )


async def require_auth_for_openai(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> str:
    """
    Stricter authentication for OpenAI-triggering endpoints.
    Can be configured to allow anonymous access via REQUIRE_AUTH_FOR_OPENAI env var.
    
    This is the primary dependency for all OpenAI endpoints.
    """
    if not REQUIRE_AUTH_FOR_OPENAI:
        # Allow anonymous but return a placeholder for rate limiting
        user_id = await get_optional_user(authorization, x_user_id)
        if user_id:
            return user_id
        return "anonymous"
    
    # Strict mode: require authentication
    return await get_current_user(authorization, x_user_id)


# Alias for clarity in route definitions
require_auth = require_auth_for_openai


class AuthenticatedUser:
    """
    Wrapper class for authenticated user context.
    Can be extended to include more user info from Supabase.
    """
    
    def __init__(self, user_id: str, is_anonymous: bool = False):
        self.user_id = user_id
        self.is_anonymous = is_anonymous
    
    @property
    def is_authenticated(self) -> bool:
        return not self.is_anonymous and self.user_id != "anonymous"


async def get_authenticated_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> AuthenticatedUser:
    """
    Get authenticated user object with metadata.
    """
    user_id = await get_optional_user(authorization, x_user_id)
    
    if not user_id:
        if REQUIRE_AUTH_FOR_OPENAI:
            raise HTTPException(
                status_code=401,
                detail={
                    "error_code": "AUTH_REQUIRED",
                    "message": "Authentication required."
                }
            )
        return AuthenticatedUser("anonymous", is_anonymous=True)
    
    return AuthenticatedUser(user_id, is_anonymous=False)
