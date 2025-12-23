"""
Supabase Client Module (Server-Side Only)

Provides authenticated Supabase clients for:
- Admin operations (RPC calls, privileged DB ops) using SERVICE_ROLE_KEY
- User token verification using ANON_KEY (if needed)

SECURITY: 
- This module must NEVER be imported in frontend code
- Keys are loaded from environment variables only
- No logging of keys or tokens
"""

import os
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration (from environment variables)
# ============================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Check if Supabase is configured
SUPABASE_CONFIGURED = bool(SUPABASE_URL) and bool(SUPABASE_SERVICE_ROLE_KEY)

if SUPABASE_CONFIGURED:
    logger.info("Supabase client configured (URL and SERVICE_ROLE_KEY present)")
else:
    logger.warning("Supabase client NOT configured - quota enforcement will use fallback")


# ============================================================================
# REST API Helpers
# ============================================================================

def _get_rest_base_url() -> str:
    """Get Supabase REST API base URL."""
    if not SUPABASE_URL:
        return ""
    if SUPABASE_URL.endswith("/rest/v1"):
        return SUPABASE_URL
    return f"{SUPABASE_URL}/rest/v1"


def _get_admin_headers() -> Dict[str, str]:
    """Get headers for admin (service role) operations."""
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured")
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def _get_anon_headers(access_token: Optional[str] = None) -> Dict[str, str]:
    """Get headers for anon key operations (with optional user token)."""
    if not SUPABASE_ANON_KEY:
        raise RuntimeError("SUPABASE_ANON_KEY not configured")
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


# ============================================================================
# RPC Function Calls
# ============================================================================

def call_rpc(
    function_name: str,
    params: Dict[str, Any],
    use_service_role: bool = True,
    timeout: int = 10
) -> Dict[str, Any]:
    """
    Call a Supabase RPC function.
    
    Args:
        function_name: Name of the RPC function
        params: Parameters to pass to the function
        use_service_role: Use service role key (default) or anon key
        timeout: Request timeout in seconds
        
    Returns:
        The RPC function result
        
    Raises:
        RuntimeError: If Supabase is not configured or RPC fails
    """
    if not SUPABASE_CONFIGURED:
        raise RuntimeError("Supabase not configured")
    
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
    headers = _get_admin_headers() if use_service_role else _get_anon_headers()
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=params,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return {}  # No content
        else:
            error_text = response.text[:200] if response.text else "Unknown error"
            logger.error(
                f"RPC {function_name} failed: status={response.status_code}, error={error_text}"
            )
            raise RuntimeError(f"RPC call failed: {response.status_code}")
            
    except requests.exceptions.Timeout:
        logger.error(f"RPC {function_name} timed out after {timeout}s")
        raise RuntimeError("RPC call timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"RPC {function_name} request failed: {e}")
        raise RuntimeError(f"RPC call failed: {str(e)}")


# ============================================================================
# Quota-Specific Functions
# ============================================================================

def consume_quota(
    user_id: str,
    reserved_tokens: int = 2000,
    daily_request_limit: int = 50,
    monthly_token_limit: int = 2000000
) -> Dict[str, Any]:
    """
    Call the consume_quota RPC function.
    
    This is an atomic check-and-increment operation that:
    1. Checks if user is within quota limits
    2. If allowed, increments the request count and reserves tokens
    3. Returns whether the operation is allowed
    
    Args:
        user_id: The user's UUID
        reserved_tokens: Tokens to reserve for this request
        daily_request_limit: Max requests per day
        monthly_token_limit: Max tokens per month
        
    Returns:
        Dict with 'allowed' (bool), 'reason' (str if denied),
        'daily_requests_used', 'monthly_tokens_used'
        
    Raises:
        RuntimeError: If RPC fails (only in strict mode)
    """
    if not SUPABASE_CONFIGURED:
        # Fallback: allow with warning when Supabase is not configured
        logger.debug(f"Supabase not configured - allowing quota for user {user_id} (fallback mode)")
        return {
            "allowed": True,
            "reason": None,
            "daily_requests_used": 0,
            "monthly_tokens_used": 0,
            "fallback": True
        }
    
    params = {
        "p_user_id": user_id,
        "p_reserved_tokens": reserved_tokens,
        "p_daily_request_limit": daily_request_limit,
        "p_monthly_token_limit": monthly_token_limit
    }
    
    try:
        result = call_rpc("consume_quota", params)
        logger.debug(f"consume_quota result for {user_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"consume_quota RPC failed for user {user_id}: {e}")
        
        # Check if we should allow on RPC failure (testing/dev mode)
        quota_fallback_allow = os.getenv("QUOTA_FALLBACK_ALLOW", "false").lower() == "true"
        if quota_fallback_allow:
            logger.warning(f"Allowing request despite RPC failure (QUOTA_FALLBACK_ALLOW=true)")
            return {
                "allowed": True,
                "reason": None,
                "daily_requests_used": 0,
                "monthly_tokens_used": 0,
                "fallback": True,
                "error": str(e)
            }
        
        # On RPC failure, deny by default for safety in production
        raise RuntimeError(f"Quota check failed: {str(e)}")


def get_user_quota_status(user_id: str) -> Dict[str, Any]:
    """
    Get current quota status for a user (read-only).
    
    Args:
        user_id: The user's UUID
        
    Returns:
        Dict with quota information
    """
    if not SUPABASE_CONFIGURED:
        return {
            "daily_requests_used": 0,
            "daily_requests_limit": 50,
            "monthly_tokens_used": 0,
            "monthly_tokens_limit": 2000000,
            "fallback": True
        }
    
    try:
        url = f"{_get_rest_base_url()}/user_quotas"
        params = {
            "user_id": f"eq.{user_id}",
            "select": "daily_requests,monthly_tokens,last_reset_day,last_reset_month"
        }
        
        response = requests.get(
            url,
            headers=_get_admin_headers(),
            params=params,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                row = data[0]
                return {
                    "daily_requests_used": row.get("daily_requests", 0),
                    "monthly_tokens_used": row.get("monthly_tokens", 0),
                    "last_reset_day": row.get("last_reset_day"),
                    "last_reset_month": row.get("last_reset_month"),
                }
            return {
                "daily_requests_used": 0,
                "monthly_tokens_used": 0,
            }
        else:
            logger.error(f"Failed to get quota status: {response.status_code}")
            return {}
            
    except Exception as e:
        logger.error(f"Error getting quota status for {user_id}: {e}")
        return {}


# ============================================================================
# User Token Verification (if using Supabase Auth)
# ============================================================================

def verify_user_token(access_token: str) -> Optional[str]:
    """
    Verify a Supabase access token and return the user ID.
    
    Args:
        access_token: The JWT access token from the frontend
        
    Returns:
        The user ID (UUID string) if valid, None otherwise
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logger.warning("Supabase not configured for token verification")
        return None
    
    try:
        url = f"{SUPABASE_URL}/auth/v1/user"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {access_token}",
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get("id")
            if user_id:
                return user_id
        
        logger.debug(f"Token verification failed: {response.status_code}")
        return None
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None

