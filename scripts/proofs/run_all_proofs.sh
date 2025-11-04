#!/bin/bash
# =============================================================================
# Run All Runtime Proofs
# Generates evidence artifacts for demo purposes
# =============================================================================
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="audit_artifacts/${TIMESTAMP}/proofs"
mkdir -p "$OUTPUT_DIR"

# API URL
API_URL="${API_URL:-http://localhost:8000}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Real Estate OS - Runtime Proofs${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  API URL: ${API_URL}"
echo -e "  Output:  ${OUTPUT_DIR}"
echo ""

# Check if API is accessible
echo -e "${YELLOW}🔍 Checking API accessibility...${NC}"
if ! curl -sf "${API_URL}/healthz" > /dev/null 2>&1; then
    echo -e "${RED}❌ API not accessible at ${API_URL}${NC}"
    echo -e "${YELLOW}   Please start the Docker stack first:${NC}"
    echo -e "${YELLOW}   ./scripts/docker/start.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓ API is accessible${NC}"
echo ""

# Track proof results
PROOFS_PASSED=0
PROOFS_FAILED=0
PROOFS_TOTAL=0

# Function to run a proof
run_proof() {
    local proof_name=$1
    local proof_script=$2

    PROOFS_TOTAL=$((PROOFS_TOTAL + 1))

    echo -e "${YELLOW}Running proof: ${proof_name}...${NC}"

    if bash "$proof_script" "$OUTPUT_DIR" "$API_URL"; then
        echo -e "${GREEN}✓ ${proof_name} passed${NC}"
        PROOFS_PASSED=$((PROOFS_PASSED + 1))
    else
        echo -e "${RED}✗ ${proof_name} failed${NC}"
        PROOFS_FAILED=$((PROOFS_FAILED + 1))
    fi

    echo ""
}

# =============================================================================
# PROOF 1: Mock Provider Integration
# =============================================================================

run_proof "Mock Provider Integration" "scripts/proofs/01_mock_providers.sh"

# =============================================================================
# PROOF 2: API Health & OpenAPI
# =============================================================================

run_proof "API Health & OpenAPI Export" "scripts/proofs/02_api_health.sh"

# =============================================================================
# PROOF 3: Authentication & JWT
# =============================================================================

run_proof "Authentication & JWT Tokens" "scripts/proofs/03_authentication.sh"

# =============================================================================
# PROOF 4: Rate Limiting
# =============================================================================

run_proof "Rate Limiting Enforcement" "scripts/proofs/04_rate_limiting.sh"

# =============================================================================
# PROOF 5: Idempotency
# =============================================================================

run_proof "Idempotency Key System" "scripts/proofs/05_idempotency.sh"

# =============================================================================
# PROOF 6: Background Jobs
# =============================================================================

run_proof "Background Job Processing" "scripts/proofs/06_background_jobs.sh"

# =============================================================================
# PROOF 7: Real-Time Updates (SSE)
# =============================================================================

run_proof "Server-Sent Events (SSE)" "scripts/proofs/07_sse_events.sh"

# =============================================================================
# SUMMARY
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Proof Generation Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  Total Proofs:   ${PROOFS_TOTAL}"
echo -e "  Passed:         ${GREEN}${PROOFS_PASSED}${NC}"
echo -e "  Failed:         ${RED}${PROOFS_FAILED}${NC}"
echo ""

# Generate summary JSON
cat > "${OUTPUT_DIR}/summary.json" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "api_url": "${API_URL}",
  "total_proofs": ${PROOFS_TOTAL},
  "passed": ${PROOFS_PASSED},
  "failed": ${PROOFS_FAILED},
  "proofs": {
    "mock_providers": "$([ -f "${OUTPUT_DIR}/01_mock_providers.json" ] && echo 'passed' || echo 'failed')",
    "api_health": "$([ -f "${OUTPUT_DIR}/02_api_health.json" ] && echo 'passed' || echo 'failed')",
    "authentication": "$([ -f "${OUTPUT_DIR}/03_authentication.json" ] && echo 'passed' || echo 'failed')",
    "rate_limiting": "$([ -f "${OUTPUT_DIR}/04_rate_limiting.json" ] && echo 'passed' || echo 'failed')",
    "idempotency": "$([ -f "${OUTPUT_DIR}/05_idempotency.json" ] && echo 'passed' || echo 'failed')",
    "background_jobs": "$([ -f "${OUTPUT_DIR}/06_background_jobs.json" ] && echo 'passed' || echo 'failed')",
    "sse_events": "$([ -f "${OUTPUT_DIR}/07_sse_events.json" ] && echo 'passed' || echo 'failed')"
  },
  "artifacts_directory": "${OUTPUT_DIR}"
}
EOF

echo -e "  ${YELLOW}Summary:${NC} ${OUTPUT_DIR}/summary.json"
echo ""

if [ $PROOFS_FAILED -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ All proofs passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Some proofs failed${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
