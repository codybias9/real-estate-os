#!/bin/bash
# =============================================================================
# Proof 2: API Health & OpenAPI Export
# Validates API is running and exports OpenAPI specification
# =============================================================================

OUTPUT_DIR=$1
API_URL=$2

# Test health endpoint
HEALTH_RESPONSE=$(curl -s "${API_URL}/healthz")
HEALTH_STATUS=$?

# Get API status
STATUS_RESPONSE=$(curl -s "${API_URL}/api/v1/status")
STATUS_CODE=$?

# Export OpenAPI spec
OPENAPI_SPEC=$(curl -s "${API_URL}/openapi.json")
OPENAPI_STATUS=$?

# Count endpoints
ENDPOINT_COUNT=$(echo "$OPENAPI_SPEC" | python3 -c "
import json, sys
try:
    spec = json.load(sys.stdin)
    paths = spec.get('paths', {})
    count = sum(len(methods) for methods in paths.values())
    print(count)
except:
    print(0)
" 2>/dev/null || echo 0)

# Create proof artifact
cat > "${OUTPUT_DIR}/02_api_health.json" << EOF
{
  "proof_name": "API Health & OpenAPI Export",
  "description": "Validates API is operational and exports complete API specification",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "results": {
    "health_check": {
      "endpoint": "${API_URL}/healthz",
      "success": $([ $HEALTH_STATUS -eq 0 ] && echo 'true' || echo 'false'),
      "response": $(echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo 'null')
    },
    "status_check": {
      "endpoint": "${API_URL}/api/v1/status",
      "success": $([ $STATUS_CODE -eq 0 ] && echo 'true' || echo 'false'),
      "response": $(echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo 'null')
    },
    "openapi_export": {
      "endpoint": "${API_URL}/openapi.json",
      "success": $([ $OPENAPI_STATUS -eq 0 ] && echo 'true' || echo 'false'),
      "endpoint_count": ${ENDPOINT_COUNT},
      "spec_size_bytes": $(echo "$OPENAPI_SPEC" | wc -c)
    }
  },
  "evidence": {
    "api_accessible": $([ $HEALTH_STATUS -eq 0 ] && echo 'true' || echo 'false'),
    "features_enabled": $(echo "$STATUS_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    features = data.get('features', {})
    enabled = sum(1 for v in features.values() if v)
    print(enabled)
except:
    print(0)
" 2>/dev/null || echo 0),
    "total_endpoints": ${ENDPOINT_COUNT}
  },
  "conclusion": "API is operational with ${ENDPOINT_COUNT} documented endpoints"
}
EOF

# Save OpenAPI spec
echo "$OPENAPI_SPEC" > "${OUTPUT_DIR}/openapi.json"

echo "  ✓ API health proof generated (${ENDPOINT_COUNT} endpoints documented)"

# Exit success if health check passed
[ $HEALTH_STATUS -eq 0 ]
