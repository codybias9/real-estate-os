#!/bin/bash
set -e

# API Authentication & Authorization Verification Script
# Tests JWT validation, RBAC, and rate limiting

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}\")\" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/api"

echo "========================================"
echo "API Auth & Rate Limit Verification"
echo "========================================"
echo ""

# Ensure artifacts directory exists
mkdir -p "$ARTIFACTS_DIR"

# Load environment
if [ -f "$PROJECT_ROOT/.env.staging" ]; then
  source "$PROJECT_ROOT/.env.staging"
fi

API_URL="${API_URL:-http://localhost:8000}"
OUTPUT_FILE="$ARTIFACTS_DIR/authz-test-transcripts.txt"
RATE_LIMIT_FILE="$ARTIFACTS_DIR/rate-limits-proof.txt"

echo "Testing API at: $API_URL" | tee "$OUTPUT_FILE"
echo "Time: $(date)" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 1: Unauthenticated Request (401)
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 1: Unauthenticated Request → 401" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Request: GET $API_URL/api/v1/properties (no token)" | tee -a "$OUTPUT_FILE"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "$API_URL/api/v1/properties")
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_STATUS")

echo "Status: $HTTP_STATUS" | tee -a "$OUTPUT_FILE"
echo "Body: $BODY" | tee -a "$OUTPUT_FILE"

if [ "$HTTP_STATUS" -eq 401 ]; then
  echo "✓ PASS: Returns 401 Unauthorized" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: Expected 401, got $HTTP_STATUS" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 2: Invalid Token (401)
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 2: Invalid Token → 401" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

INVALID_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbnZhbGlkIn0.invalid"
echo "Request: GET $API_URL/api/v1/properties (invalid token)" | tee -a "$OUTPUT_FILE"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -H "Authorization: Bearer $INVALID_TOKEN" "$API_URL/api/v1/properties")
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_STATUS")

echo "Status: $HTTP_STATUS" | tee -a "$OUTPUT_FILE"
echo "Body: $BODY" | tee -a "$OUTPUT_FILE"

if [ "$HTTP_STATUS" -eq 401 ]; then
  echo "✓ PASS: Returns 401 for invalid token" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: Expected 401, got $HTTP_STATUS" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 3: Valid Token, No tenant_id (403)
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 3: Token Without tenant_id → 403" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Note: This test requires a real Keycloak token without tenant_id claim
echo "SKIP: Requires Keycloak setup with test users" | tee -a "$OUTPUT_FILE"
echo "Manual Test:" | tee -a "$OUTPUT_FILE"
echo "  1. Create user in Keycloak without tenant_id claim" | tee -a "$OUTPUT_FILE"
echo "  2. Get token: curl -d 'grant_type=password&client_id=api-client&username=test&password=test' http://keycloak:8080/realms/real-estate-os/protocol/openid-connect/token" | tee -a "$OUTPUT_FILE"
echo "  3. Call API: curl -H 'Authorization: Bearer <token>' $API_URL/api/v1/properties" | tee -a "$OUTPUT_FILE"
echo "  4. Expected: 403 Forbidden with message 'No tenant_id in token'" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 4: Valid Token, Insufficient Role (403)
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 4: Insufficient Role → 403" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "SKIP: Requires Keycloak setup with test users" | tee -a "$OUTPUT_FILE"
echo "Manual Test:" | tee -a "$OUTPUT_FILE"
echo "  1. Create 'user' role in Keycloak (no 'admin' role)" | tee -a "$OUTPUT_FILE"
echo "  2. Assign to test user" | tee -a "$OUTPUT_FILE"
echo "  3. Get token and call admin endpoint: GET /api/v1/admin/tenants" | tee -a "$OUTPUT_FILE"
echo "  4. Expected: 403 Forbidden with message 'Required role: admin'" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 5: Valid Token, Authorized (200)
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 5: Valid Token → 200" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "SKIP: Requires Keycloak setup with test users" | tee -a "$OUTPUT_FILE"
echo "Manual Test:" | tee -a "$OUTPUT_FILE"
echo "  1. Create user with tenant_id claim in Keycloak" | tee -a "$OUTPUT_FILE"
echo "  2. Get valid token" | tee -a "$OUTPUT_FILE"
echo "  3. Call API: GET /api/v1/properties" | tee -a "$OUTPUT_FILE"
echo "  4. Expected: 200 OK with properties list filtered by tenant_id" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 6: Health Check (Public, No Auth)
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 6: Public Health Endpoint → 200" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Request: GET $API_URL/health" | tee -a "$OUTPUT_FILE"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "$API_URL/health")
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_STATUS")

echo "Status: $HTTP_STATUS" | tee -a "$OUTPUT_FILE"
echo "Body: $BODY" | tee -a "$OUTPUT_FILE"

if [ "$HTTP_STATUS" -eq 200 ]; then
  echo "✓ PASS: Health check accessible without auth" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: Expected 200, got $HTTP_STATUS" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 7: OpenAPI Docs (Public, No Auth)
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 7: OpenAPI Documentation → 200" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Request: GET $API_URL/docs" | tee -a "$OUTPUT_FILE"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "$API_URL/docs")
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)

echo "Status: $HTTP_STATUS" | tee -a "$OUTPUT_FILE"

if [ "$HTTP_STATUS" -eq 200 ]; then
  echo "✓ PASS: API docs accessible" | tee -a "$OUTPUT_FILE"

  # Download OpenAPI schema
  echo "Downloading OpenAPI schema..." | tee -a "$OUTPUT_FILE"
  curl -s "$API_URL/openapi.json" > "$ARTIFACTS_DIR/openapi.json"

  if [ -s "$ARTIFACTS_DIR/openapi.json" ]; then
    ENDPOINT_COUNT=$(jq '[.paths | to_entries[] | .value | to_entries[]] | length' "$ARTIFACTS_DIR/openapi.json")
    echo "✓ OpenAPI schema saved: $ARTIFACTS_DIR/openapi.json ($ENDPOINT_COUNT endpoints)" | tee -a "$OUTPUT_FILE"
  fi
else
  echo "✗ FAIL: Expected 200, got $HTTP_STATUS" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# RATE LIMITING TESTS
# ========================================
echo "========================================" | tee "$RATE_LIMIT_FILE"
echo "Rate Limiting Verification" | tee -a "$RATE_LIMIT_FILE"
echo "========================================" | tee -a "$RATE_LIMIT_FILE"
echo "" | tee -a "$RATE_LIMIT_FILE"

echo "Testing rate limits on health endpoint..." | tee -a "$RATE_LIMIT_FILE"
echo "" | tee -a "$RATE_LIMIT_FILE"

# Send 150 requests to exceed default rate limit (100/min)
RATE_EXCEEDED=false
for i in {1..150}; do
  RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "$API_URL/health" 2>/dev/null)
  HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)

  # Extract rate limit headers
  LIMIT=$(echo "$RESPONSE" | grep -i "x-ratelimit-limit" | cut -d: -f2 | tr -d ' \r\n')
  REMAINING=$(echo "$RESPONSE" | grep -i "x-ratelimit-remaining" | cut -d: -f2 | tr -d ' \r\n')

  if [ "$HTTP_STATUS" -eq 429 ]; then
    RATE_EXCEEDED=true
    echo "Request $i: 429 Too Many Requests" | tee -a "$RATE_LIMIT_FILE"
    BODY=$(echo "$RESPONSE" | grep -v "HTTP_STATUS" | grep -v "x-ratelimit")
    echo "Response: $BODY" | tee -a "$RATE_LIMIT_FILE"
    break
  fi

  # Log every 25 requests
  if [ $((i % 25)) -eq 0 ]; then
    echo "Request $i: $HTTP_STATUS (Limit: $LIMIT, Remaining: $REMAINING)" | tee -a "$RATE_LIMIT_FILE"
  fi

  # Small delay to avoid overwhelming local server
  sleep 0.01
done

echo "" | tee -a "$RATE_LIMIT_FILE"

if [ "$RATE_EXCEEDED" = true ]; then
  echo "✓ PASS: Rate limiting enforced (429 received)" | tee -a "$RATE_LIMIT_FILE"
else
  echo "⚠ WARNING: Rate limit not triggered after 150 requests" | tee -a "$RATE_LIMIT_FILE"
  echo "  This may be expected if rate limit is disabled or set very high" | tee -a "$RATE_LIMIT_FILE"
fi
echo "" | tee -a "$RATE_LIMIT_FILE"

# ========================================
# Summary
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "Verification Complete" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Artifacts generated:" | tee -a "$OUTPUT_FILE"
echo "  - $OUTPUT_FILE" | tee -a "$OUTPUT_FILE"
echo "  - $RATE_LIMIT_FILE" | tee -a "$OUTPUT_FILE"
if [ -f "$ARTIFACTS_DIR/openapi.json" ]; then
  echo "  - $ARTIFACTS_DIR/openapi.json" | tee -a "$OUTPUT_FILE"
fi
echo ""

echo "Next Steps:"
echo "  1. Deploy Keycloak: docker compose up -d keycloak"
echo "  2. Create realm 'real-estate-os' with test users"
echo "  3. Re-run this script with valid JWT tokens for full verification"
echo "  4. Verify cross-tenant isolation: bash scripts/ops/verify_api_isolation.sh"
