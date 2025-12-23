# Security Configuration Guide

This document describes all security controls implemented in the 2nd_brain API.

## Quick Reference: Security Status by Endpoint

| Method | Route | Auth | Quota | RateLimit | IDOR | Notes |
|--------|-------|------|-------|-----------|------|-------|
| POST | `/upload-pdf` | ❌ Optional | ❌ No | ✅ Yes | ❌ No | File upload only |
| POST | `/generate-flashcards/{pdf_id}` | ✅ **Required** | ✅ **Yes** | ✅ Yes (3x) | ⚠️ Partial | **CALLS OPENAI** |
| GET | `/status/{pdf_id}` | ❌ No | ❌ No | ✅ Yes | ❌ No | Read only |
| GET | `/flashcards/{pdf_id}` | ❌ No | ❌ No | ✅ Yes | ❌ No | Read only |
| POST | `/youtube/save` | ❌ Optional | ❌ No | ✅ Yes | ❌ No | DB write |
| POST | `/youtube/flashcards` | ✅ **Required** | ✅ **Yes** | ✅ Yes (3x) | ❌ No | **CALLS OPENAI 2x** |
| POST | `/youtube/transcript-flashcards` | ✅ **Required** | ✅ **Yes** | ✅ Yes (3x) | ❌ No | **CALLS OPENAI** |
| POST | `/summaries/{source_id}/refresh` | ✅ **Required** | ✅ **Yes** | ✅ Yes (3x) | ⚠️ Partial | **CALLS OPENAI** |
| GET | `/summaries/{source_id}` | ❌ No | ❌ No | ✅ Yes | ❌ No | Read only |
| GET | `/health*` | ❌ No | ❌ No | ❌ No | ❌ No | Health checks |

---

## Environment Variables

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `REQUIRE_AUTH_FOR_OPENAI` | `true` | Require X-User-Id for OpenAI endpoints |
| `ALLOW_ANONYMOUS_READ` | `true` | Allow anonymous read operations |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_RPM` | 30 | Requests per minute per IP |
| `RATE_LIMIT_RPH` | 300 | Requests per hour per IP |
| `RATE_LIMIT_BURST` | 10 | Maximum burst (token bucket) |
| `OPENAI_RATE_LIMIT_RPM` | 10 | Rate limit for OpenAI endpoints |
| `OPENAI_CONCURRENT_LIMIT` | 5 | Max concurrent OpenAI requests globally |

### Per-User Quotas

| Variable | Default | Description |
|----------|---------|-------------|
| `QUOTA_DAILY_REQUESTS` | 50 | Daily OpenAI requests per authenticated user |
| `QUOTA_DAILY_TOKENS` | 100000 | Daily tokens per authenticated user |
| `QUOTA_MONTHLY_TOKENS` | 1000000 | Monthly tokens per authenticated user |
| `QUOTA_ANON_DAILY_REQUESTS` | 5 | Daily requests for anonymous users |
| `QUOTA_ANON_DAILY_TOKENS` | 10000 | Daily tokens for anonymous users |
| `QUOTA_DEFAULT_TOKEN_ESTIMATE` | 2000 | Token estimate when actual unknown |

### Request Size Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_BODY_SIZE_BYTES` | 5242880 (5MB) | Maximum request body size |
| `MAX_TRANSCRIPT_CHARS` | 50000 | Maximum transcript length |
| `MAX_INPUT_CHARS` | 8000 | Maximum PDF text to OpenAI |

### OpenAI Protection

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_TIMEOUT_SECONDS` | 60 | Timeout for OpenAI API calls |

### IDOR Protection

| Variable | Default | Description |
|----------|---------|-------------|
| `ENFORCE_OWNERSHIP` | `true` | Enable deck ownership verification |

---

## Security Modules

### `security/auth.py` - Authentication

**Dependencies:**
- `get_current_user` - Returns user_id or raises 401
- `get_optional_user` - Returns user_id or None
- `require_auth` - Stricter auth for OpenAI endpoints

**Usage:**

```python
from security.auth import require_auth

@app.post("/expensive-endpoint")
async def endpoint(user_id: str = Depends(require_auth)):
    # user_id is guaranteed to be valid
    ...
```

### `security/quotas.py` - Per-User Quotas

**Functions:**
- `check_quota(user_id)` - Check if user within limits
- `increment_quota(user_id, tokens)` - Increment usage counters

**Quota Types:**
- `daily_requests` - Requests per day
- `daily_tokens` - Tokens per day  
- `monthly_tokens` - Tokens per month

**Usage:**

```python
from security.quotas import check_quota, increment_quota, QuotaExceededError

# Before expensive operation
try:
    await check_quota(user_id)
except QuotaExceededError as e:
    raise HTTPException(status_code=429, detail=str(e))

# After OpenAI call
await increment_quota(user_id, tokens_used=response.usage.total_tokens)
```

### `security/ownership.py` - IDOR Protection

**Functions:**
- `check_deck_owner(deck_id, user_id)` - Returns bool
- `assert_deck_owner(deck_id, user_id)` - Raises 403 if not owner
- `assert_source_owner(source_id, user_id)` - Same for sources

**Usage:**

```python
from security.ownership import assert_deck_owner

@app.delete("/decks/{deck_id}")
async def delete_deck(deck_id: str, user_id: str = Depends(require_auth)):
    await assert_deck_owner(deck_id, user_id)  # Raises 403 if not owner
    # Proceed with deletion
```

### `middleware/security.py` - Rate Limiting & Size Limits

**Middleware:**
- `RateLimitMiddleware` - Per-IP rate limiting
- `RequestSizeLimitMiddleware` - Body size limits

---

## Testing Security Controls

### 1. Test Authentication (401)

```bash
# Should return 401
curl -X POST http://localhost:8000/generate-flashcards/test-id
curl -X POST http://localhost:8000/youtube/flashcards \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=test"}'
```

Expected: `401 {"detail": {"error_code": "AUTH_REQUIRED", ...}}`

### 2. Test Rate Limiting (429)

```bash
# Rapid requests should eventually trigger 429
for i in {1..50}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/status/test
done
```

Expected: Eventually returns `429`

### 3. Test Quota Exceeded (429)

```bash
# Set low quota for testing: QUOTA_DAILY_REQUESTS=2
# After 2 requests:
curl -X POST http://localhost:8000/generate-flashcards/test \
  -H "X-User-Id: test-user-uuid"
```

Expected: `429 {"error_code": "QUOTA_EXCEEDED", ...}`

### 4. Test Payload Size (413)

```bash
# Create oversized payload (>5MB)
python -c "print('a'*6000000)" > /tmp/big.txt
curl -X POST http://localhost:8000/youtube/transcript-flashcards \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  --data-binary @/tmp/big.txt
```

Expected: `413 Payload Too Large`

### 5. Test Input Validation (422)

```bash
# Missing required field
curl -X POST http://localhost:8000/youtube/flashcards \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -d '{}'
```

Expected: `422 Validation Error`

### 6. Test Health - No Key Leak

```bash
curl http://localhost:8000/health/summary | jq
```

Expected: No `openai_key_masked` or `api_key` fields

---

## Production Deployment Checklist

### Required

- [ ] Set `REQUIRE_AUTH_FOR_OPENAI=true`
- [ ] Set reasonable quota limits
- [ ] Configure `CORS_ORIGINS` to your domains only
- [ ] Set `DEBUG=false`
- [ ] Ensure `OPENAI_API_KEY` is never in client bundles

### Recommended

- [ ] Use Redis for rate limiting (`REDIS_URL`)
- [ ] Enable `ENFORCE_OWNERSHIP=true`
- [ ] Set up monitoring for 429 responses
- [ ] Configure log aggregation (no sensitive data logged)

---

## Known Limitations

### In-Memory Rate Limiting

Rate limiting uses in-memory storage per-process. In multi-worker deployments:
- Each worker has its own bucket
- Total effective limit = limit × workers
- For true distributed limiting, configure `REDIS_URL`

### Quota Persistence

Quotas use in-memory cache with optional SQLite persistence:
- Resets on server restart if SQLite not used
- For production, ensure database persistence

### IDOR Protection

Ownership verification requires Supabase:
- Checks `user_decks` table via REST API
- Falls back to allow access if Supabase not configured
- Set `ENFORCE_OWNERSHIP=true` in production

---

## Error Codes Reference

| Code | Status | Description |
|------|--------|-------------|
| `AUTH_REQUIRED` | 401 | Authentication header missing |
| `INVALID_AUTH` | 401 | Invalid authentication token |
| `FORBIDDEN` | 403 | User does not own resource |
| `QUOTA_EXCEEDED` | 429 | User exceeded usage quota |
| `RATE_LIMITED` | 429 | Too many requests |
| `VALIDATION_ERROR` | 422 | Invalid request payload |
| `PAYLOAD_TOO_LARGE` | 413 | Request body exceeds limit |
| `INTERNAL_ERROR` | 500 | Server error (details hidden) |
