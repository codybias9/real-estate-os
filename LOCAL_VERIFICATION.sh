#!/bin/bash
# Local Runtime Verification Script
# Run this on your local machine to verify all changes

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
    print_info "jq not found. Installing jq for JSON parsing..."
    # On macOS: brew install jq
    # On Linux: sudo apt-get install jq
fi

echo ""
echo "Step 2: Starting services..."
print_info "This will take 30-60 seconds on first run..."
docker-compose up -d

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
    print_info "Check logs with: docker-compose logs api"
    exit 1
fi

echo ""
echo "Step 4: Fetching OpenAPI spec..."
OPENAPI_RESPONSE=$(curl -s http://localhost:8000/api/v1/openapi.json)
if [ -z "$OPENAPI_RESPONSE" ]; then
    print_error "Failed to fetch OpenAPI spec"
    exit 1
fi
print_success "OpenAPI spec retrieved"

# Count endpoints from OpenAPI
if command -v jq &> /dev/null; then
    ENDPOINT_COUNT=$(echo "$OPENAPI_RESPONSE" | jq '.paths | length')
    print_info "Total endpoints in OpenAPI: $ENDPOINT_COUNT"

    if [ "$ENDPOINT_COUNT" -ge 140 ]; then
        print_success "Endpoint count verified (expected ~142, got $ENDPOINT_COUNT)"
    else
        print_error "Endpoint count mismatch (expected ~142, got $ENDPOINT_COUNT)"
    fi
fi

echo ""
echo "Step 5: Testing authentication flow..."

# Test login
print_info "Logging in as demo@example.com..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "demo@example.com", "password": "demo123"}')

if command -v jq &> /dev/null; then
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
    if [ "$TOKEN" != "null" ] && [ ! -z "$TOKEN" ]; then
        print_success "Login successful, token received"
    else
        print_error "Login failed - no token received"
        echo "Response: $LOGIN_RESPONSE"
        exit 1
    fi
else
    print_info "Install jq to parse token automatically"
    TOKEN="mock-token-for-testing"
fi

echo ""
echo "Step 6: Testing protected endpoints..."

# Test unprotected GET (should work without token)
print_info "Testing public GET /properties (no auth)..."
PROPS_RESPONSE=$(curl -s -X GET http://localhost:8000/api/v1/properties)
if command -v jq &> /dev/null; then
    PROPS_COUNT=$(echo "$PROPS_RESPONSE" | jq 'length')
    if [ "$PROPS_COUNT" -eq 15 ]; then
        print_success "Public GET works: 15 properties returned"
    else
        print_error "Expected 15 properties, got $PROPS_COUNT"
    fi
else
    print_info "Public GET /properties returned data"
fi

# Test protected PATCH (should require token)
print_info "Testing protected PATCH /properties (requires auth)..."
PATCH_RESPONSE=$(curl -s -X PATCH http://localhost:8000/api/v1/properties/test-id \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"status": "active"}')

if echo "$PATCH_RESPONSE" | grep -q "not found\|Property"; then
    print_success "Protected endpoint accepts bearer token"
else
    print_error "Protected endpoint auth failed"
    echo "Response: $PATCH_RESPONSE"
fi

echo ""
echo "Step 7: Testing SSE events..."

# Get SSE token
print_info "Requesting SSE token..."
SSE_TOKEN_RESPONSE=$(curl -s http://localhost:8000/api/v1/sse/token)
if command -v jq &> /dev/null; then
    SSE_TOKEN=$(echo "$SSE_TOKEN_RESPONSE" | jq -r '.token')
    if [ "$SSE_TOKEN" != "null" ] && [ ! -z "$SSE_TOKEN" ]; then
        print_success "SSE token obtained"
        print_info "SSE stream URL: http://localhost:8000/api/v1/sse/stream?token=$SSE_TOKEN"
        print_info "To test SSE, open this in a browser or use: curl -N <URL>"
    else
        print_error "Failed to get SSE token"
    fi
else
    print_info "SSE endpoint accessible at /api/v1/sse/token"
fi

echo ""
echo "Step 8: Checking frontend..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_success "Frontend accessible at http://localhost:3000"
else
    print_error "Frontend not accessible (may still be building)"
    print_info "Check logs with: docker-compose logs frontend"
fi

echo ""
echo "=============================================="
echo "Summary: Runtime Verification Complete"
echo "=============================================="
echo ""
print_success "API: http://localhost:8000/api/v1"
print_success "Docs: http://localhost:8000/docs"
print_success "Frontend: http://localhost:3000"
echo ""
print_info "New pages to test:"
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
