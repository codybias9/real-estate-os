#!/bin/bash
set -e

# API Cross-Tenant Isolation Verification Script
# Tests that API endpoints enforce tenant isolation via RLS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}\")\" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/isolation"

echo "========================================"
echo "API Cross-Tenant Isolation Test"
echo "========================================"
echo ""

# Ensure artifacts directory exists
mkdir -p "$ARTIFACTS_DIR"

# Load environment
if [ -f "$PROJECT_ROOT/.env.staging" ]; then
  source "$PROJECT_ROOT/.env.staging"
fi

API_URL="${API_URL:-http://localhost:8000}"
OUTPUT_FILE="$ARTIFACTS_DIR/negative-tests-api.txt"

echo "Testing API isolation at: $API_URL" | tee "$OUTPUT_FILE"
echo "Time: $(date)" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Test tenant UUIDs
TENANT_A="11111111-1111-1111-1111-111111111111"
TENANT_B="22222222-2222-2222-2222-222222222222"

echo "Test Tenants:" | tee -a "$OUTPUT_FILE"
echo "  Tenant A: $TENANT_A" | tee -a "$OUTPUT_FILE"
echo "  Tenant B: $TENANT_B" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# Prerequisites Check
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "Prerequisites Check" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Check if Keycloak is available
if ! curl -sf "$KEYCLOAK_SERVER_URL/health" > /dev/null 2>&1; then
  echo "⚠ WARNING: Keycloak not available at $KEYCLOAK_SERVER_URL" | tee -a "$OUTPUT_FILE"
  echo "Cannot obtain JWT tokens for testing." | tee -a "$OUTPUT_FILE"
  echo "" | tee -a "$OUTPUT_FILE"
  echo "To complete this test:" | tee -a "$OUTPUT_FILE"
  echo "  1. Start Keycloak: docker compose up -d keycloak" | tee -a "$OUTPUT_FILE"
  echo "  2. Create realm: real-estate-os" | tee -a "$OUTPUT_FILE"
  echo "  3. Create test users with tenant_id claims:" | tee -a "$OUTPUT_FILE"
  echo "     - user_a (tenant_id=$TENANT_A)" | tee -a "$OUTPUT_FILE"
  echo "     - user_b (tenant_id=$TENANT_B)" | tee -a "$OUTPUT_FILE"
  echo "  4. Re-run this script" | tee -a "$OUTPUT_FILE"
  echo "" | tee -a "$OUTPUT_FILE"
  exit 0
fi

echo "✓ Keycloak is available" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# Get JWT Tokens for Both Tenants
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "Obtaining JWT Tokens" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Tenant A token
echo "Getting token for Tenant A user..." | tee -a "$OUTPUT_FILE"
TOKEN_A=$(curl -sf -X POST "$KEYCLOAK_TOKEN_URL" \
  -d "grant_type=password" \
  -d "client_id=$KEYCLOAK_CLIENT_ID" \
  -d "client_secret=$KEYCLOAK_CLIENT_SECRET" \
  -d "username=test_user_a" \
  -d "password=test123" \
  | jq -r '.access_token' 2>/dev/null || echo "")

if [ -z "$TOKEN_A" ] || [ "$TOKEN_A" = "null" ]; then
  echo "✗ Failed to get token for Tenant A" | tee -a "$OUTPUT_FILE"
  echo "  Create user 'test_user_a' with tenant_id=$TENANT_A" | tee -a "$OUTPUT_FILE"
  TOKEN_A=""
else
  echo "✓ Token obtained for Tenant A" | tee -a "$OUTPUT_FILE"
fi

# Tenant B token
echo "Getting token for Tenant B user..." | tee -a "$OUTPUT_FILE"
TOKEN_B=$(curl -sf -X POST "$KEYCLOAK_TOKEN_URL" \
  -d "grant_type=password" \
  -d "client_id=$KEYCLOAK_CLIENT_ID" \
  -d "client_secret=$KEYCLOAK_CLIENT_SECRET" \
  -d "username=test_user_b" \
  -d "password=test123" \
  | jq -r '.access_token' 2>/dev/null || echo "")

if [ -z "$TOKEN_B" ] || [ "$TOKEN_B" = "null" ]; then
  echo "✗ Failed to get token for Tenant B" | tee -a "$OUTPUT_FILE"
  echo "  Create user 'test_user_b' with tenant_id=$TENANT_B" | tee -a "$OUTPUT_FILE"
  TOKEN_B=""
else
  echo "✓ Token obtained for Tenant B" | tee -a "$OUTPUT_FILE"
fi

echo "" | tee -a "$OUTPUT_FILE"

if [ -z "$TOKEN_A" ] || [ -z "$TOKEN_B" ]; then
  echo "Cannot proceed without test user tokens." | tee -a "$OUTPUT_FILE"
  echo "See setup instructions above." | tee -a "$OUTPUT_FILE"
  exit 0
fi

# ========================================
# Create Test Properties via API
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "Creating Test Data via API" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Create properties for Tenant A
echo "Creating 3 properties for Tenant A..." | tee -a "$OUTPUT_FILE"
for i in {1..3}; do
  RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/properties" \
    -H "Authorization: Bearer $TOKEN_A" \
    -H "Content-Type: application/json" \
    -d "{
      \"address\": \"$i Tenant A Street\",
      \"city\": \"City A\",
      \"state\": \"CA\",
      \"zip_code\": \"90001\",
      \"property_type\": \"Residential\",
      \"list_price\": $((500000 + i * 100000))
    }" 2>&1 || echo "error")

  if echo "$RESPONSE" | grep -q "error"; then
    echo "  Property $i: Failed" | tee -a "$OUTPUT_FILE"
  else
    echo "  Property $i: Created" | tee -a "$OUTPUT_FILE"
  fi
done

# Create properties for Tenant B
echo "Creating 3 properties for Tenant B..." | tee -a "$OUTPUT_FILE"
for i in {1..3}; do
  RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/properties" \
    -H "Authorization: Bearer $TOKEN_B" \
    -H "Content-Type: application/json" \
    -d "{
      \"address\": \"$i Tenant B Avenue\",
      \"city\": \"City B\",
      \"state\": \"CA\",
      \"zip_code\": \"90002\",
      \"property_type\": \"Commercial\",
      \"list_price\": $((1000000 + i * 100000))
    }" 2>&1 || echo "error")

  if echo "$RESPONSE" | grep -q "error"; then
    echo "  Property $i: Failed" | tee -a "$OUTPUT_FILE"
  else
    echo "  Property $i: Created" | tee -a "$OUTPUT_FILE"
  fi
done

echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 1: Tenant A Can See Their Properties
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 1: Tenant A can see their properties" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Request: GET /api/v1/properties (Tenant A token)" | tee -a "$OUTPUT_FILE"
RESPONSE=$(curl -sf -X GET "$API_URL/api/v1/properties" \
  -H "Authorization: Bearer $TOKEN_A")

COUNT_A=$(echo "$RESPONSE" | jq 'length' 2>/dev/null || echo "0")

echo "Result: $COUNT_A properties returned" | tee -a "$OUTPUT_FILE"

if [ "$COUNT_A" -ge 3 ]; then
  echo "✓ PASS: Tenant A can see their properties" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: Expected ≥3 properties, got $COUNT_A" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 2: Tenant B Can See Their Properties
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 2: Tenant B can see their properties" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Request: GET /api/v1/properties (Tenant B token)" | tee -a "$OUTPUT_FILE"
RESPONSE=$(curl -sf -X GET "$API_URL/api/v1/properties" \
  -H "Authorization: Bearer $TOKEN_B")

COUNT_B=$(echo "$RESPONSE" | jq 'length' 2>/dev/null || echo "0")

echo "Result: $COUNT_B properties returned" | tee -a "$OUTPUT_FILE"

if [ "$COUNT_B" -ge 3 ]; then
  echo "✓ PASS: Tenant B can see their properties" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: Expected ≥3 properties, got $COUNT_B" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 3: Tenant A Cannot See Tenant B Data
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 3: Tenant A CANNOT see Tenant B data" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Request: GET /api/v1/properties (Tenant A token)" | tee -a "$OUTPUT_FILE"
RESPONSE=$(curl -sf -X GET "$API_URL/api/v1/properties" \
  -H "Authorization: Bearer $TOKEN_A")

# Check if response contains any Tenant B addresses
CROSS_TENANT_LEAK=$(echo "$RESPONSE" | jq -r '.[].address' 2>/dev/null | grep -c "Tenant B" || true)

echo "Tenant B addresses visible to Tenant A: $CROSS_TENANT_LEAK" | tee -a "$OUTPUT_FILE"

if [ "$CROSS_TENANT_LEAK" -eq 0 ]; then
  echo "✓ PASS: RLS blocks Tenant A from seeing Tenant B data" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: RLS FAILED - Tenant A can see $CROSS_TENANT_LEAK of Tenant B's properties" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 4: Tenant A Cannot Update Tenant B Data
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 4: Tenant A CANNOT update Tenant B data" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Get a property ID from Tenant B's list
PROPERTY_B_ID=$(curl -sf -X GET "$API_URL/api/v1/properties" \
  -H "Authorization: Bearer $TOKEN_B" \
  | jq -r '.[0].id' 2>/dev/null || echo "")

if [ -n "$PROPERTY_B_ID" ] && [ "$PROPERTY_B_ID" != "null" ]; then
  echo "Attempting to update Tenant B property $PROPERTY_B_ID using Tenant A token..." | tee -a "$OUTPUT_FILE"

  RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PATCH "$API_URL/api/v1/properties/$PROPERTY_B_ID" \
    -H "Authorization: Bearer $TOKEN_A" \
    -H "Content-Type: application/json" \
    -d '{"list_price": 999999}')

  HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
  echo "Status: $HTTP_STATUS" | tee -a "$OUTPUT_FILE"

  if [ "$HTTP_STATUS" -eq 404 ] || [ "$HTTP_STATUS" -eq 403 ]; then
    echo "✓ PASS: RLS blocks cross-tenant update (404/403)" | tee -a "$OUTPUT_FILE"
  else
    echo "✗ FAIL: Expected 404/403, got $HTTP_STATUS" | tee -a "$OUTPUT_FILE"
  fi
else
  echo "⚠ SKIP: No Tenant B property found for update test" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 5: Tenant A Cannot Delete Tenant B Data
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 5: Tenant A CANNOT delete Tenant B data" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

if [ -n "$PROPERTY_B_ID" ] && [ "$PROPERTY_B_ID" != "null" ]; then
  echo "Attempting to delete Tenant B property $PROPERTY_B_ID using Tenant A token..." | tee -a "$OUTPUT_FILE"

  RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X DELETE "$API_URL/api/v1/properties/$PROPERTY_B_ID" \
    -H "Authorization: Bearer $TOKEN_A")

  HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
  echo "Status: $HTTP_STATUS" | tee -a "$OUTPUT_FILE"

  if [ "$HTTP_STATUS" -eq 404 ] || [ "$HTTP_STATUS" -eq 403 ]; then
    echo "✓ PASS: RLS blocks cross-tenant delete (404/403)" | tee -a "$OUTPUT_FILE"
  else
    echo "✗ FAIL: Expected 404/403, got $HTTP_STATUS" | tee -a "$OUTPUT_FILE"
  fi
else
  echo "⚠ SKIP: No Tenant B property found for delete test" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# Summary
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "API Isolation Verification Complete" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Artifact generated: $OUTPUT_FILE"
echo ""
echo "Next: Verify vector/object storage isolation with:"
echo "  - scripts/ops/verify_qdrant_isolation.sh"
echo "  - scripts/ops/verify_minio_isolation.sh"
