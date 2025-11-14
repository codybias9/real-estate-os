#!/bin/bash
# SSE Event Stream Test
# This script tests real-time SSE events by connecting to the stream
# and triggering test events

set -e

echo "=============================================="
echo "SSE Event Stream Test"
echo "=============================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Get SSE token
echo "Step 1: Obtaining SSE token..."
SSE_TOKEN_RESPONSE=$(curl -s http://localhost:8000/api/v1/sse/token)

if command -v jq &> /dev/null; then
    SSE_TOKEN=$(echo "$SSE_TOKEN_RESPONSE" | jq -r '.token')
    STREAM_URL=$(echo "$SSE_TOKEN_RESPONSE" | jq -r '.stream_url')
    print_success "Token obtained: ${SSE_TOKEN:0:20}..."
else
    print_info "Install jq for better output parsing"
    SSE_TOKEN=$(echo "$SSE_TOKEN_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
fi

echo ""
echo "Step 2: Starting SSE stream listener..."
print_info "Connecting to: http://localhost:8000/api/v1/sse/stream?token=$SSE_TOKEN"
print_info "Stream will show events in real-time. Press Ctrl+C to stop."
echo ""
print_info "In another terminal, trigger test events with:"
echo "  curl -X POST http://localhost:8000/api/v1/sse/test/emit \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"event_type\": \"property_updated\", \"data\": {\"property_id\": \"test\", \"message\": \"Test event\"}}'"
echo ""
echo "--- SSE STREAM (live events below) ---"

# Connect to SSE stream
curl -N -H "Accept: text/event-stream" \
    "http://localhost:8000/api/v1/sse/stream?token=$SSE_TOKEN" \
    2>/dev/null | while IFS= read -r line; do
    # Parse and display SSE events with timestamps
    if [[ $line == event:* ]]; then
        EVENT_TYPE=$(echo "$line" | cut -d':' -f2- | xargs)
        printf "${GREEN}[$(date '+%H:%M:%S')]${NC} Event: ${YELLOW}$EVENT_TYPE${NC}\n"
    elif [[ $line == data:* ]]; then
        DATA=$(echo "$line" | cut -d':' -f2- | xargs)
        if command -v jq &> /dev/null; then
            echo "$DATA" | jq '.' 2>/dev/null || echo "  Data: $DATA"
        else
            echo "  Data: $DATA"
        fi
    elif [[ $line == :* ]]; then
        # Heartbeat
        printf "${GREEN}[$(date '+%H:%M:%S')]${NC} Heartbeat\n"
    fi
done
