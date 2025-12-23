"""
Security Middleware for FastAPI

Provides:
- Rate limiting (per-IP and global)
- Request body size limiting
- Request timeout protection
- Concurrency limiting for expensive endpoints

NOTE: This uses in-memory storage by default. For production with multiple
workers/replicas, use Redis-backed storage (see REDIS_URL env var).
"""

import os
import time
import asyncio
import logging
from typing import Dict, Callable, Optional
from collections import defaultdict
from functools import wraps
from fastapi import Request, HTTPException, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

# Rate limit settings (can be overridden via env vars)
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_RPM", "30"))
RATE_LIMIT_REQUESTS_PER_HOUR = int(os.getenv("RATE_LIMIT_RPH", "300"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))

# Request body size limit (default 5MB for most endpoints)
MAX_BODY_SIZE_BYTES = int(os.getenv("MAX_BODY_SIZE_BYTES", str(5 * 1024 * 1024)))

# OpenAI endpoint-specific limits (stricter)
OPENAI_RATE_LIMIT_RPM = int(os.getenv("OPENAI_RATE_LIMIT_RPM", "10"))
OPENAI_CONCURRENT_LIMIT = int(os.getenv("OPENAI_CONCURRENT_LIMIT", "5"))

# Endpoints that trigger OpenAI calls (need stricter limits)
OPENAI_ENDPOINTS = {
    "/generate-flashcards/",
    "/youtube/flashcards",
    "/youtube/transcript-flashcards",
    "/summaries/",  # refresh endpoint
}

# ============================================================================
# In-Memory Rate Limiter (Token Bucket Algorithm)
# ============================================================================

class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using token bucket algorithm.
    
    WARNING: This is per-process only. In a multi-worker deployment,
    each worker has its own bucket. For true rate limiting, use Redis.
    """
    
    def __init__(self):
        self._buckets: Dict[str, Dict] = defaultdict(lambda: {
            "tokens": RATE_LIMIT_BURST,
            "last_update": time.time(),
            "minute_count": 0,
            "minute_reset": time.time() + 60,
            "hour_count": 0,
            "hour_reset": time.time() + 3600,
        })
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, cost: int = 1) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.
        Returns (allowed: bool, info: dict with remaining/reset times)
        """
        async with self._lock:
            now = time.time()
            bucket = self._buckets[key]
            
            # Refill tokens based on time passed
            elapsed = now - bucket["last_update"]
            refill = elapsed * (RATE_LIMIT_REQUESTS_PER_MINUTE / 60)
            bucket["tokens"] = min(RATE_LIMIT_BURST, bucket["tokens"] + refill)
            bucket["last_update"] = now
            
            # Reset minute/hour counters if window passed
            if now >= bucket["minute_reset"]:
                bucket["minute_count"] = 0
                bucket["minute_reset"] = now + 60
            if now >= bucket["hour_reset"]:
                bucket["hour_count"] = 0
                bucket["hour_reset"] = now + 3600
            
            # Check limits
            info = {
                "remaining_burst": int(bucket["tokens"]),
                "remaining_minute": RATE_LIMIT_REQUESTS_PER_MINUTE - bucket["minute_count"],
                "remaining_hour": RATE_LIMIT_REQUESTS_PER_HOUR - bucket["hour_count"],
                "reset_minute": int(bucket["minute_reset"] - now),
                "reset_hour": int(bucket["hour_reset"] - now),
            }
            
            if bucket["tokens"] < cost:
                return False, info
            if bucket["minute_count"] >= RATE_LIMIT_REQUESTS_PER_MINUTE:
                return False, info
            if bucket["hour_count"] >= RATE_LIMIT_REQUESTS_PER_HOUR:
                return False, info
            
            # Consume tokens
            bucket["tokens"] -= cost
            bucket["minute_count"] += 1
            bucket["hour_count"] += 1
            
            return True, info


class OpenAIConcurrencyLimiter:
    """
    Limits concurrent OpenAI requests globally and per-user.
    """
    
    def __init__(self, max_global: int = OPENAI_CONCURRENT_LIMIT, max_per_user: int = 2):
        self._global_count = 0
        self._per_user: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        self._max_global = max_global
        self._max_per_user = max_per_user
    
    async def acquire(self, user_key: str) -> bool:
        """Try to acquire a slot. Returns True if successful."""
        async with self._lock:
            if self._global_count >= self._max_global:
                return False
            if self._per_user[user_key] >= self._max_per_user:
                return False
            self._global_count += 1
            self._per_user[user_key] += 1
            return True
    
    async def release(self, user_key: str):
        """Release a slot."""
        async with self._lock:
            self._global_count = max(0, self._global_count - 1)
            self._per_user[user_key] = max(0, self._per_user[user_key] - 1)


# Global instances
rate_limiter = InMemoryRateLimiter()
openai_concurrency = OpenAIConcurrencyLimiter()


# ============================================================================
# Middleware Classes
# ============================================================================

def get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For for proxied requests."""
    # Check X-Forwarded-For header (common for proxies/load balancers)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP (used by some proxies)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection
    if request.client:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    
    Applies different limits for regular endpoints vs OpenAI-triggering endpoints.
    Returns 429 Too Many Requests when limits are exceeded.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/healthz", "/readyz", "/"):
            return await call_next(request)
        
        client_ip = get_client_ip(request)
        
        # Determine if this is an OpenAI endpoint (needs stricter limits)
        is_openai_endpoint = any(
            request.url.path.startswith(ep) for ep in OPENAI_ENDPOINTS
        )
        
        # Use stricter rate for OpenAI endpoints
        if is_openai_endpoint and request.method in ("POST", "PUT"):
            cost = 3  # Count as 3 regular requests
        else:
            cost = 1
        
        allowed, info = await rate_limiter.is_allowed(f"ip:{client_ip}", cost)
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for IP {client_ip} on {request.url.path}. "
                f"Remaining: burst={info['remaining_burst']}, min={info['remaining_minute']}"
            )
            return Response(
                content='{"detail": "Rate limit exceeded. Please slow down and try again later."}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(info["reset_minute"]),
                    "X-RateLimit-Remaining": str(info["remaining_minute"]),
                    "X-RateLimit-Reset": str(info["reset_minute"]),
                },
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Remaining"] = str(info["remaining_minute"])
        response.headers["X-RateLimit-Reset"] = str(info["reset_minute"])
        
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limits request body size to prevent memory exhaustion and cost attacks.
    Returns 413 Payload Too Large when exceeded.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip for GET, HEAD, OPTIONS (no body)
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                # Use larger limit for file uploads
                if request.url.path == "/upload-pdf":
                    max_size = 10 * 1024 * 1024  # 10MB for PDFs
                else:
                    max_size = MAX_BODY_SIZE_BYTES
                
                if size > max_size:
                    logger.warning(
                        f"Request body too large: {size} bytes > {max_size} bytes "
                        f"on {request.url.path}"
                    )
                    return Response(
                        content=f'{{"detail": "Request body too large. Maximum size is {max_size // (1024*1024)}MB."}}',
                        status_code=413,
                        headers={"Content-Type": "application/json"},
                    )
            except ValueError:
                pass  # Invalid Content-Length, let it proceed
        
        return await call_next(request)


# ============================================================================
# Dependencies for FastAPI
# ============================================================================

async def check_openai_concurrency(request: Request):
    """
    Dependency that checks and acquires an OpenAI concurrency slot.
    Use for endpoints that trigger OpenAI calls.
    """
    client_ip = get_client_ip(request)
    user_id = request.headers.get("x-user-id", client_ip)
    user_key = f"user:{user_id}"
    
    acquired = await openai_concurrency.acquire(user_key)
    if not acquired:
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent AI requests. Please wait for your previous request to complete."
        )
    
    # Store for cleanup
    request.state.openai_user_key = user_key


async def release_openai_concurrency(request: Request):
    """Release the OpenAI concurrency slot after request completes."""
    user_key = getattr(request.state, "openai_user_key", None)
    if user_key:
        await openai_concurrency.release(user_key)


def require_openai_concurrency():
    """
    Decorator for route handlers that trigger OpenAI calls.
    Manages concurrency slot acquisition and release.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request:
                await check_openai_concurrency(request)
                try:
                    return await func(*args, **kwargs)
                finally:
                    await release_openai_concurrency(request)
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator

