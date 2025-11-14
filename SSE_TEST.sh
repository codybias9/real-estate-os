#!/bin/bash
# SSE Event Stream Test
# This script tests real-time SSE events by connecting to the stream
# and triggering test events
# Artifacts saved to: artifacts/runtime/

set -e

echo "=============================================="
echo "SSE Event Stream Test"
echo "=============================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Create artifacts directory
mkdir -p artifacts/runtime
ARTIFACTS_DIR="artifacts/runtime"
EVENTS_LOG="$ARTIFACTS_DIR/sse_events.jsonl"

# Clear previous events log
> "$EVENTS_LOG"

# Get SSE token
echo "Step 1: Obtaining SSE token..."
SSE_TOKEN_RESPONSE=$(curl -s http://localhost:8000/api/v1/sse/token)

if command -v jq &> /dev/null; then
    SSE_TOKEN=$(echo "$SSE_TOKEN_RESPONSE" | jq -r '.token')
    STREAM_URL=$(echo "$SSE_TOKEN_RESPONSE" | jq -r '.stream_url' 2>/dev/null || echo "http://localhost:8000/api/v1/sse/stream")
    print_success "Token obtained: ${SSE_TOKEN:0:20}..."
else
    print_error "jq required for this script"
    exit 1
fi

if [ "$SSE_TOKEN" = "null" ] || [ -z "$SSE_TOKEN" ]; then
    print_error "Failed to obtain SSE token"
    exit 1
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
echo ""

# Track event count and timeout
EVENT_COUNT=0
MAX_EVENTS=10
TIMEOUT=30
START_TIME=$(date +%s)

# Cleanup function
cleanup() {
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    echo "--- SSE STREAM SUMMARY ---"
    print_info "Duration: ${DURATION}s"
    print_info "Events captured: $EVENT_COUNT"
    print_info "Events saved to: $EVENTS_LOG"

    if [ $EVENT_COUNT -eq 0 ]; then
        print_error "FAIL: No events received within ${TIMEOUT}s"
        print_info "Check if SSE stream is working: docker-compose logs api | grep -i sse"
        exit 1
    else
        print_success "PASS: $EVENT_COUNT events received"
    fi

    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM EXIT

# Connect to SSE stream with timeout monitoring
{
    timeout $TIMEOUT curl -N -H "Accept: text/event-stream" \
        "http://localhost:8000/api/v1/sse/stream?token=$SSE_TOKEN" \
        2>/dev/null || true
} | while IFS= read -r line; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    # Check timeout
    if [ $ELAPSED -gt $TIMEOUT ]; then
        print_error "Timeout reached (${TIMEOUT}s)"
        break
    fi

    # Parse and display SSE events with timestamps
    if [[ $line == event:* ]]; then
        EVENT_TYPE=$(echo "$line" | cut -d':' -f2- | xargs)
        TIMESTAMP=$(date '+%H:%M:%S')
        printf "${GREEN}[${TIMESTAMP}]${NC} Event: ${YELLOW}${EVENT_TYPE}${NC}\n"

        # Track for JSONL
        CURRENT_EVENT_TYPE="$EVENT_TYPE"
        EVENT_COUNT=$((EVENT_COUNT + 1))

    elif [[ $line == data:* ]]; then
        DATA=$(echo "$line" | cut -d':' -f2- | xargs)
        TIMESTAMP=$(date '+%H:%M:%S')

        # Pretty print with jq if valid JSON
        if echo "$DATA" | jq '.' >/dev/null 2>&1; then
            echo "${GREEN}[${TIMESTAMP}]${NC} Data:"
            echo "$DATA" | jq '.'

            # Save to JSONL with metadata
            echo "{\"timestamp\":\"$(date -Iseconds)\",\"event_type\":\"$CURRENT_EVENT_TYPE\",\"data\":$DATA}" >> "$EVENTS_LOG"
        else
            echo "${GREEN}[${TIMESTAMP}]${NC} Data: $DATA"
        fi

    elif [[ $line == id:* ]]; then
        EVENT_ID=$(echo "$line" | cut -d':' -f2- | xargs)
        TIMESTAMP=$(date '+%H:%M:%S')
        printf "${GREEN}[${TIMESTAMP}]${NC} ID: $EVENT_ID\n"

    elif [[ $line == :* ]]; then
        # Heartbeat/comment
        TIMESTAMP=$(date '+%H:%M:%S')
        printf "${GREEN}[${TIMESTAMP}]${NC} ❤ Heartbeat\n"

    elif [[ $line == retry:* ]]; then
        RETRY=$(echo "$line" | cut -d':' -f2- | xargs)
        TIMESTAMP=$(date '+%H:%M:%S')
        printf "${GREEN}[${TIMESTAMP}]${NC} Retry: ${RETRY}ms\n"
    fi

    # Stop after max events
    if [ $EVENT_COUNT -ge $MAX_EVENTS ]; then
        print_success "Reached max events ($MAX_EVENTS), stopping..."
        break
    fi
done

# Normal exit (cleanup trap will handle summary)
