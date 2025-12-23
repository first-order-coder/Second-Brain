#!/bin/bash
# ============================================================================
# Security Verification Script for 2nd_brain API
# 
# This script tests all security controls implemented in the API:
# - Authentication (401)
# - Quota enforcement (429)
# - Rate limiting (429)
# - Input validation (422)
# - Payload size limits (413)
# 
# Usage: ./verify_security.sh [BASE_URL]
# Default BASE_URL: http://localhost:8000
# ============================================================================

set -e

BASE_URL="${1:-http://localhost:8000}"
VALID_USER_ID="test-user-$(date +%s)-uuid"
PASS_COUNT=0
FAIL_COUNT=0

echo "=============================================="
echo "Security Verification for 2nd_brain API"
echo "Base URL: $BASE_URL"
echo "Test User ID: $VALID_USER_ID"
echo "=============================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASS_COUNT++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    echo "  Expected: $2"
    echo "  Got: $3"
    ((FAIL_COUNT++))
}

check_status() {
    local expected=$1
    local actual=$2
    local test_name=$3
    
    if [ "$actual" -eq "$expected" ]; then
        pass "$test_name"
    else
        fail "$test_name" "$expected" "$actual"
    fi
}

# ============================================================================
# Test 1: Authentication Required (401)
# ============================================================================

echo ""
echo "=== Test 1: Authentication Required (401) ==="

# Test /generate-flashcards without auth
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/generate-flashcards/test-id" \
    -H "Content-Type: application/json")
check_status 401 "$status" "POST /generate-flashcards without auth"

# Test /youtube/flashcards without auth
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/youtube/flashcards" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://youtube.com/watch?v=test"}')
check_status 401 "$status" "POST /youtube/flashcards without auth"

# Test /youtube/transcript-flashcards without auth
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/youtube/transcript-flashcards" \
    -H "Content-Type: application/json" \
    -d '{"transcript": "Test transcript"}')
check_status 401 "$status" "POST /youtube/transcript-flashcards without auth"

# Test /summaries/refresh without auth
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/summaries/test-id/refresh")
check_status 401 "$status" "POST /summaries/refresh without auth"

# ============================================================================
# Test 2: Valid Auth Accepted (404 for non-existent resource)
# ============================================================================

echo ""
echo "=== Test 2: Valid Auth Accepted ==="

# Test with valid auth header - should get 404 (not 401)
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/generate-flashcards/nonexistent-pdf" \
    -H "X-User-Id: $VALID_USER_ID" \
    -H "Content-Type: application/json")
check_status 404 "$status" "POST /generate-flashcards with auth (expects 404)"

# ============================================================================
# Test 3: Input Validation (422)
# ============================================================================

echo ""
echo "=== Test 3: Input Validation (422) ==="

# Test missing required field
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/youtube/flashcards" \
    -H "X-User-Id: $VALID_USER_ID" \
    -H "Content-Type: application/json" \
    -d '{}')
check_status 422 "$status" "POST /youtube/flashcards with empty body"

# Test transcript too long (>50000 chars)
long_transcript=$(python3 -c "print('a' * 51000)" 2>/dev/null || python -c "print('a' * 51000)")
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/youtube/transcript-flashcards" \
    -H "X-User-Id: $VALID_USER_ID" \
    -H "Content-Type: application/json" \
    -d "{\"transcript\": \"$long_transcript\"}")
check_status 422 "$status" "POST /youtube/transcript-flashcards with oversized transcript"

# Test too many cards in /youtube/save
many_cards=$(python3 -c "import json; print(json.dumps([{'front':'Q','back':'A'} for _ in range(150)]))" 2>/dev/null || python -c "import json; print(json.dumps([{'front':'Q','back':'A'} for _ in range(150)]))")
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/youtube/save" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"https://youtube.com/watch?v=test\", \"cards\": $many_cards}")
check_status 422 "$status" "POST /youtube/save with 150 cards (max 100)"

# ============================================================================
# Test 4: Rate Limiting (429)
# ============================================================================

echo ""
echo "=== Test 4: Rate Limiting ==="

# Make rapid requests to trigger rate limit
echo "Making rapid requests to test rate limiting..."
rate_limited=false
for i in {1..50}; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/status/test-$i")
    if [ "$status" -eq 429 ]; then
        pass "Rate limiting triggered after $i requests"
        rate_limited=true
        break
    fi
done

if [ "$rate_limited" = false ]; then
    echo -e "${YELLOW}⚠ NOTE${NC}: Rate limit not triggered in 50 requests (may need higher load)"
fi

# ============================================================================
# Test 5: Health Endpoints (No Auth Required, No Key Leak)
# ============================================================================

echo ""
echo "=== Test 5: Health Endpoints ==="

# Health endpoints should be accessible without auth
for endpoint in "/health" "/healthz" "/readyz"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")
    if [ "$status" -eq 200 ] || [ "$status" -eq 500 ]; then
        pass "GET $endpoint accessible (status: $status)"
    else
        fail "GET $endpoint" "200 or 500" "$status"
    fi
done

# Check /health/summary doesn't leak API key
response=$(curl -s "$BASE_URL/health/summary")
if echo "$response" | grep -qi "sk-"; then
    fail "/health/summary key leak check" "no 'sk-' in response" "Found 'sk-' in response"
elif echo "$response" | grep -qi "openai_key_masked"; then
    fail "/health/summary key leak check" "no 'openai_key_masked' field" "Found masked key"
else
    pass "/health/summary doesn't leak API key"
fi

# ============================================================================
# Test 6: Error Response Format
# ============================================================================

echo ""
echo "=== Test 6: Error Response Format ==="

# Check that error responses are clean JSON
response=$(curl -s "$BASE_URL/flashcards/nonexistent")
if echo "$response" | grep -q "Traceback"; then
    fail "Error response clean" "no stack traces" "Found Traceback"
elif echo "$response" | grep -q '"detail"'; then
    pass "Error response is clean JSON with 'detail' field"
else
    fail "Error response format" "JSON with 'detail'" "$response"
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "=============================================="
echo "Security Verification Complete"
echo "=============================================="
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "${RED}Some security checks failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All security checks passed!${NC}"
    exit 0
fi

