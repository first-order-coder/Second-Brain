"""
Authentication Dependencies for FastAPI

Provides:
- get_current_user: Requires authentication, returns user_id
- get_optional_user: Returns user_id if present, None otherwise
- require_auth: Stricter auth for OpenAI endpoints

The authentication is based on the X-User-Id header which is set by the
frontend after Supabase authentication. In production, this should be
validated against Supabase's auth service.
"""

import os
import logging
from typing import Optional
from fastapi import Header, HTTPException, Request

logger = logging.getLogger(__name__)

# Configuration
REQUIRE_AUTH_FOR_OPENAI = os.getenv("REQUIRE_AUTH_FOR_OPENAI", "true").lower() == "true"
ALLOW_ANONYMOUS_READ = os.getenv("ALLOW_ANONYMOUS_READ", "true").lower() == "true"


async def get_optional_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> Optional[str]:
    """
    Extract user ID from header if present.
    Returns None for anonymous users (allowed for some operations).
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(user_id: Optional[str] = Depends(get_optional_user)):
            ...
    """
    if x_user_id:
        # Basic validation: UUID format expected
        user_id = x_user_id.strip()
        if len(user_id) < 10 or len(user_id) > 100:
            logger.warning(f"Invalid user_id format: {user_id[:20]}...")
            return None
        return user_id
    return None


async def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> str:
    """
    Require authentication - returns user_id or raises 401.
    
    Usage for protected endpoints:
        @app.post("/expensive-endpoint")
        async def endpoint(user_id: str = Depends(get_current_user)):
            ...
    """
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "AUTH_REQUIRED",
                "message": "Authentication required. Please sign in to use this feature."
            }
        )
    
    user_id = x_user_id.strip()
    
    # Basic validation
    if len(user_id) < 10 or len(user_id) > 100:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "INVALID_AUTH",
                "message": "Invalid authentication token."
            }
        )
    
    return user_id


async def require_auth_for_openai(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> str:
    """
    Stricter authentication for OpenAI-triggering endpoints.
    Can be configured to allow anonymous access via REQUIRE_AUTH_FOR_OPENAI env var.
    
    This is the primary dependency for all OpenAI endpoints.
    """
    if not REQUIRE_AUTH_FOR_OPENAI:
        # Allow anonymous but return a placeholder for rate limiting
        if not x_user_id:
            return "anonymous"
        return x_user_id.strip()
    
    # Strict mode: require authentication
    return await get_current_user(x_user_id)


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
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> AuthenticatedUser:
    """
    Get authenticated user object with metadata.
    """
    if not x_user_id:
        if REQUIRE_AUTH_FOR_OPENAI:
            raise HTTPException(
                status_code=401,
                detail={
                    "error_code": "AUTH_REQUIRED",
                    "message": "Authentication required."
                }
            )
        return AuthenticatedUser("anonymous", is_anonymous=True)
    
    return AuthenticatedUser(x_user_id.strip(), is_anonymous=False)

