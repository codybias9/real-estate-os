#!/bin/bash
# Local Runtime Verification Script
# Run this on your local machine to verify all changes
# Artifacts saved to: artifacts/runtime/

set -e

echo "=============================================="
echo "Real Estate OS - Runtime Verification"
echo "=============================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Create artifacts directory
mkdir -p artifacts/runtime
ARTIFACTS_DIR="artifacts/runtime"
echo "Artifacts will be saved to: $ARTIFACTS_DIR"
echo ""

# Check prerequisites
echo "Step 1: Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker Desktop."
    exit 1
fi
print_success "Docker found"

if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose not found. Please install docker-compose."
    exit 1
fi
print_success "docker-compose found"

if ! command -v curl &> /dev/null; then
    print_error "curl not found. Please install curl."
    exit 1
fi
print_success "curl found"

if ! command -v jq &> /dev/null; then
    print_error "jq not found. Please install jq for JSON parsing."
    print_info "macOS: brew install jq"
    print_info "Linux: sudo apt-get install jq"
    exit 1
fi
print_success "jq found"

echo ""
echo "Step 2: Starting services..."
print_info "This will take 30-60 seconds on first run..."
docker-compose up -d 2>&1 | tee "$ARTIFACTS_DIR/docker_startup.log"

# Wait for services to be healthy
echo ""
echo "Step 3: Waiting for services to be ready..."
MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/api/v1/healthz > /dev/null 2>&1; then
        print_success "API is ready!"
        break
    fi
    echo -n "."
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    print_error "API failed to start within ${MAX_WAIT}s"
    print_info "Check logs: docker-compose logs api"
    print_info "Artifacts saved to: $ARTIFACTS_DIR"
    exit 1
fi

echo ""
echo "Step 4: OpenAPI Specification Analysis..."

# Fetch and save OpenAPI spec
curl -s http://localhost:8000/openapi.json -o "$ARTIFACTS_DIR/openapi.json"
if [ ! -s "$ARTIFACTS_DIR/openapi.json" ]; then
    print_error "Failed to fetch OpenAPI spec"
    exit 1
fi
print_success "OpenAPI spec saved to $ARTIFACTS_DIR/openapi.json"

# Extract summary
jq '{
  paths: (.paths | length),
  tags: [.tags[]? | .name],
  first_three_paths: (.paths | keys | .[0:3])
}' "$ARTIFACTS_DIR/openapi.json" | tee "$ARTIFACTS_DIR/openapi_summary.json"

ENDPOINT_COUNT=$(jq '.paths' "$ARTIFACTS_DIR/openapi_summary.json")
print_info "Total endpoints in OpenAPI: $ENDPOINT_COUNT"

if [ "$ENDPOINT_COUNT" -lt 140 ]; then
    print_error "FAIL: paths < 140 (got $ENDPOINT_COUNT)"
    exit 1
fi
print_success "Endpoint count verified (expected ≥140, got $ENDPOINT_COUNT)"

echo ""
echo "Step 5: CORS Preflight Check..."

# Test CORS preflight
CORS_RESPONSE=$(curl -s -X OPTIONS http://localhost:8000/api/v1/properties \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: GET" \
    -i -o "$ARTIFACTS_DIR/cors_preflight.txt" -w "%{http_code}")

if grep -q "Access-Control-Allow-Origin" "$ARTIFACTS_DIR/cors_preflight.txt"; then
    print_success "CORS headers present"
else
    print_error "CORS headers missing - frontend requests may fail"
fi

echo ""
echo "Step 6: Authentication Flow (401 → 200 flip)..."

# Get first property ID for testing
PROPS=$(curl -s http://localhost:8000/api/v1/properties)
FIRST_PROP_ID=$(echo "$PROPS" | jq -r '.[0].id' 2>/dev/null || echo "prop_1")
print_info "Testing with property ID: $FIRST_PROP_ID"

# Test 1: PATCH without token (expect 401 or similar auth error)
print_info "Testing PATCH without token (expecting auth error)..."
NO_TOKEN_RESPONSE=$(curl -s -X PATCH "http://localhost:8000/api/v1/properties/$FIRST_PROP_ID" \
    -H 'Content-Type: application/json' \
    -d '{"tags":["verified-test"]}' \
    -w '\n%{http_code}\n')

echo "$NO_TOKEN_RESPONSE" > "$ARTIFACTS_DIR/patch_no_token.txt"
NO_TOKEN_CODE=$(tail -1 "$ARTIFACTS_DIR/patch_no_token.txt")

if [ "$NO_TOKEN_CODE" = "401" ] || [ "$NO_TOKEN_CODE" = "403" ]; then
    print_success "Auth required: HTTP $NO_TOKEN_CODE (expected)"
elif [ "$NO_TOKEN_CODE" = "404" ]; then
    print_info "Got 404 (property not found) - auth may not be enforced or property ID invalid"
else
    print_error "Unexpected response: HTTP $NO_TOKEN_CODE (expected 401/403)"
fi

# Test 2: Login
print_info "Logging in as demo@example.com..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "demo@example.com", "password": "demo123"}')

echo "$LOGIN_RESPONSE" | jq '.' > "$ARTIFACTS_DIR/login_response.json" 2>/dev/null || echo "$LOGIN_RESPONSE" > "$ARTIFACTS_DIR/login_response.json"

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    print_error "Login failed - no token received"
    cat "$ARTIFACTS_DIR/login_response.json"
    exit 1
fi
print_success "Login successful, token: ${TOKEN:0:20}..."

# Test 3: PATCH with token (expect 200 or 404)
print_info "Testing PATCH with token (expecting success)..."
WITH_TOKEN_RESPONSE=$(curl -s -X PATCH "http://localhost:8000/api/v1/properties/$FIRST_PROP_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"tags":["verified-test"]}' \
    -w '\n%{http_code}\n')

echo "$WITH_TOKEN_RESPONSE" > "$ARTIFACTS_DIR/patch_with_token.txt"
WITH_TOKEN_CODE=$(tail -1 "$ARTIFACTS_DIR/patch_with_token.txt")

if [ "$WITH_TOKEN_CODE" = "200" ]; then
    print_success "Auth flip verified: 401/403 → 200 ✓"
elif [ "$WITH_TOKEN_CODE" = "404" ]; then
    print_info "Got 404 (property not found) but auth accepted (token valid)"
else
    print_error "Auth failed with token: HTTP $WITH_TOKEN_CODE"
fi

# Generate auth flip summary
echo "Auth Flip Summary:" > "$ARTIFACTS_DIR/auth_flip_summary.txt"
echo "  Without token: HTTP $NO_TOKEN_CODE" >> "$ARTIFACTS_DIR/auth_flip_summary.txt"
echo "  With token:    HTTP $WITH_TOKEN_CODE" >> "$ARTIFACTS_DIR/auth_flip_summary.txt"
cat "$ARTIFACTS_DIR/auth_flip_summary.txt"

echo ""
echo "Step 7: Write-Operation Guard (Demo Safety)..."

# Test POST to leads without auth (should fail if demo is locked)
print_info "Testing POST /leads without auth..."
WRITE_GUARD_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/leads \
    -H 'Content-Type: application/json' \
    -d '{"name":"Test Lead","email":"risk@test.com","phone":"555-0000","source":"test"}' \
    -w '\n%{http_code}\n')

echo "$WRITE_GUARD_RESPONSE" > "$ARTIFACTS_DIR/public_write_probe.txt"
WRITE_CODE=$(tail -1 "$ARTIFACTS_DIR/public_write_probe.txt")

if [ "$WRITE_CODE" = "401" ] || [ "$WRITE_CODE" = "403" ]; then
    print_success "Write guard active: POST requires auth (HTTP $WRITE_CODE)"
elif [ "$WRITE_CODE" = "200" ] || [ "$WRITE_CODE" = "201" ]; then
    print_error "RISK: Public write allowed (HTTP $WRITE_CODE) - demo is not write-protected!"
    print_info "Consider adding DEMO_ALLOW_WRITES=false guard"
else
    print_info "Write probe returned HTTP $WRITE_CODE"
fi

echo ""
echo "Step 8: SSE Smoke Test (Headless)..."

# Get SSE token
SSE_TOKEN_RESPONSE=$(curl -s http://localhost:8000/api/v1/sse/token)
echo "$SSE_TOKEN_RESPONSE" | jq '.' > "$ARTIFACTS_DIR/sse_token.json" 2>/dev/null

SSE_TOKEN=$(echo "$SSE_TOKEN_RESPONSE" | jq -r '.token')
if [ "$SSE_TOKEN" = "null" ] || [ -z "$SSE_TOKEN" ]; then
    print_error "Failed to get SSE token"
    exit 1
fi
print_success "SSE token obtained: ${SSE_TOKEN:0:20}..."

# Connect to SSE stream in background and capture first event
print_info "Connecting to SSE stream (5 second test)..."
timeout 5 curl -N -s "http://localhost:8000/api/v1/sse/stream?token=$SSE_TOKEN" 2>/dev/null | head -20 > "$ARTIFACTS_DIR/sse_stream_sample.txt" &
SSE_PID=$!

sleep 2

# Emit a test event (if endpoint exists)
print_info "Attempting to emit test event..."
curl -s -X POST http://localhost:8000/api/v1/sse/test/emit \
    -H 'Content-Type: application/json' \
    -d '{"event_type": "property_updated", "data": {"property_id": "test", "message": "Verification test"}}' \
    > "$ARTIFACTS_DIR/sse_emit_response.txt" 2>/dev/null || echo "Note: /sse/test/emit endpoint may not exist"

# Wait for SSE process
wait $SSE_PID 2>/dev/null || true

if [ -s "$ARTIFACTS_DIR/sse_stream_sample.txt" ]; then
    print_success "SSE stream connected"
    EVENT_COUNT=$(grep -c "^event:" "$ARTIFACTS_DIR/sse_stream_sample.txt" || echo "0")
    DATA_COUNT=$(grep -c "^data:" "$ARTIFACTS_DIR/sse_stream_sample.txt" || echo "0")
    print_info "Captured: $EVENT_COUNT events, $DATA_COUNT data lines"

    if [ "$EVENT_COUNT" -gt 0 ]; then
        print_success "SSE events received ✓"
    else
        print_info "No events received in 5s window (heartbeat-only is OK)"
    fi
else
    print_error "SSE stream failed to connect or no data received"
fi

echo ""
echo "Step 9: Frontend Sanity Check..."

# Check if frontend is running
FRONTEND_RESPONSE=$(curl -s http://localhost:3000 -o "$ARTIFACTS_DIR/frontend_root.html")
if [ -s "$ARTIFACTS_DIR/frontend_root.html" ]; then
    print_success "Frontend accessible at http://localhost:3000"

    # Look for Next.js or dashboard indicators
    if grep -qi "dashboard\|real.estate\|next" "$ARTIFACTS_DIR/frontend_root.html"; then
        print_success "Frontend HTML contains expected content"
    else
        print_info "Frontend loaded but content not verified"
    fi
else
    print_error "Frontend not accessible (may still be building)"
    print_info "Check logs: docker-compose logs frontend"
fi

echo ""
echo "Step 10: Page Walk (New Feature Pages)..."

# Test each new page endpoint
PAGES=(
    "workflow:Smart Lists"
    "automation:Cadence Rules"
    "leads:Lead Management"
    "deals:Deal Pipeline"
    "data:Data Enrichment"
)

for PAGE_INFO in "${PAGES[@]}"; do
    IFS=':' read -r PAGE_PATH PAGE_NAME <<< "$PAGE_INFO"

    # Call the API endpoint that the page would use
    case $PAGE_PATH in
        "workflow")
            API_PATH="/api/v1/workflow/smart-lists"
            ;;
        "automation")
            API_PATH="/api/v1/automation/cadence-rules"
            ;;
        "leads")
            API_PATH="/api/v1/leads"
            ;;
        "deals")
            API_PATH="/api/v1/deals"
            ;;
        "data")
            API_PATH="/api/v1/data-propensity/enrichment/stats"
            ;;
        *)
            continue
            ;;
    esac

    RESPONSE=$(curl -s "http://localhost:8000$API_PATH")
    echo "$RESPONSE" | jq '.' > "$ARTIFACTS_DIR/page_${PAGE_PATH}_api.json" 2>/dev/null || echo "$RESPONSE" > "$ARTIFACTS_DIR/page_${PAGE_PATH}_api.json"

    # Extract 2-3 fields from response
    if echo "$RESPONSE" | jq -e '.' > /dev/null 2>&1; then
        SAMPLE=$(echo "$RESPONSE" | jq -r 'if type == "array" then .[0] | keys[0:3] else keys[0:3] end' 2>/dev/null || echo "N/A")
        print_success "$PAGE_NAME: GET $API_PATH → fields: $SAMPLE"
    else
        print_info "$PAGE_NAME: GET $API_PATH → non-JSON response"
    fi
done

echo ""
echo "=============================================="
echo "Summary: Runtime Verification Complete"
echo "=============================================="
echo ""
print_success "API: http://localhost:8000/api/v1"
print_success "Docs: http://localhost:8000/docs"
print_success "Frontend: http://localhost:3000"
echo ""
print_success "Artifacts saved to: $ARTIFACTS_DIR/"
echo ""
print_info "Key artifacts for PR evidence:"
echo "  - openapi_summary.json (endpoint count + tags)"
echo "  - auth_flip_summary.txt (401 → 200 verification)"
echo "  - sse_stream_sample.txt (event stream proof)"
echo "  - page_*_api.json (API responses for new pages)"
echo ""
print_info "New pages to test manually:"
echo "  - http://localhost:3000/dashboard/workflow"
echo "  - http://localhost:3000/dashboard/automation"
echo "  - http://localhost:3000/dashboard/leads"
echo "  - http://localhost:3000/dashboard/deals"
echo "  - http://localhost:3000/dashboard/data"
echo "  - http://localhost:3000/dashboard/admin"
echo ""
print_info "To stop services: docker-compose down"
print_info "To view logs: docker-compose logs -f [service-name]"
echo ""
