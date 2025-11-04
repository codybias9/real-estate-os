#!/bin/bash
#
# Generate Runtime Proof Artifacts (Phase 4)
#
# Generates machine-readable evidence of claimed runtime behavior:
#  1. SSE latency proof (p95 ≤ 2s)
#  2. Memo determinism proof (identical SHA256 for same input)
#  3. DLQ drill proof (poison message → DLQ → replay once → single side-effect)
#  4. Security headers proof (CSP, HSTS, XFO, XCTO in production mode)
#  5. Rate limit proof (429 with Retry-After header)
#  6. DR restore proof (pg_dump → restore → compare row counts)
#  7. OpenAPI export (openapi.json with SHA256)
#
# Prerequisites:
#  - Docker stack running in mock mode
#  - API accessible at http://localhost:8000
#  - Database accessible (postgres service)
#  - Redis accessible (redis service)
#
# Usage:
#   ./scripts/generate_proofs.sh [--output <dir>] [--proof <name>]
#
# Options:
#   --output <dir>  : Output directory (default: audit_artifacts/<timestamp>/proofs)
#   --proof <name>  : Run specific proof (all, sse, memo, dlq, security, ratelimit, dr, openapi)
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "============================================================================"
echo "  Real Estate OS - Runtime Proof Generation (Phase 4)"
echo "============================================================================"
echo ""

# Parse arguments
PROOF="all"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
OUTPUT_DIR="audit_artifacts/${TIMESTAMP}/proofs"

while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --proof)
            PROOF="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--output <dir>] [--proof <name>]"
            exit 1
            ;;
    esac
done

# Create output directory
mkdir -p "${OUTPUT_DIR}"

echo "Configuration:"
echo "  Proof: $PROOF"
echo "  Output: ${OUTPUT_DIR}"
echo ""

# Track proof results
declare -A PROOF_RESULTS

# ============================================================================
# Proof 1: SSE Latency (p95 ≤ 2s)
# ============================================================================
if [ "$PROOF" = "all" ] || [ "$PROOF" = "sse" ]; then
    echo "============================================================================"
    echo "  Proof 1: SSE Latency (p95 ≤ 2s)"
    echo "============================================================================"
    echo ""

    if python3 scripts/proofs/sse_latency_proof.py \
        --output "${OUTPUT_DIR}/sse_latency.json" \
        --api-url "http://localhost:8000"; then
        echo -e "${GREEN}✓ SSE latency proof generated${NC}"
        PROOF_RESULTS["sse"]="PASSED"
    else
        echo -e "${RED}✗ SSE latency proof failed${NC}"
        PROOF_RESULTS["sse"]="FAILED"
    fi

    echo ""
fi

# ============================================================================
# Proof 2: Memo Determinism (identical SHA256)
# ============================================================================
if [ "$PROOF" = "all" ] || [ "$PROOF" = "memo" ]; then
    echo "============================================================================"
    echo "  Proof 2: Memo Determinism (identical SHA256 for same input)"
    echo "============================================================================"
    echo ""

    if python3 scripts/proofs/memo_determinism_proof.py \
        --output "${OUTPUT_DIR}/memo_hashes.json" \
        --api-url "http://localhost:8000"; then
        echo -e "${GREEN}✓ Memo determinism proof generated${NC}"
        PROOF_RESULTS["memo"]="PASSED"
    else
        echo -e "${RED}✗ Memo determinism proof failed${NC}"
        PROOF_RESULTS["memo"]="FAILED"
    fi

    echo ""
fi

# ============================================================================
# Proof 3: DLQ Drill (poison → DLQ → replay once → single side-effect)
# ============================================================================
if [ "$PROOF" = "all" ] || [ "$PROOF" = "dlq" ]; then
    echo "============================================================================"
    echo "  Proof 3: DLQ Drill (poison message → DLQ → replay once)"
    echo "============================================================================"
    echo ""

    if python3 scripts/proofs/dlq_drill_proof.py \
        --output "${OUTPUT_DIR}/dlq_drill.json" \
        --api-url "http://localhost:8000"; then
        echo -e "${GREEN}✓ DLQ drill proof generated${NC}"
        PROOF_RESULTS["dlq"]="PASSED"
    else
        echo -e "${RED}✗ DLQ drill proof failed${NC}"
        PROOF_RESULTS["dlq"]="FAILED"
    fi

    echo ""
fi

# ============================================================================
# Proof 4: Security Headers (CSP, HSTS, XFO, XCTO)
# ============================================================================
if [ "$PROOF" = "all" ] || [ "$PROOF" = "security" ]; then
    echo "============================================================================"
    echo "  Proof 4: Security Headers (production mode)"
    echo "============================================================================"
    echo ""

    if python3 scripts/proofs/security_headers_proof.py \
        --output "${OUTPUT_DIR}/security_headers.json" \
        --api-url "http://localhost:8000"; then
        echo -e "${GREEN}✓ Security headers proof generated${NC}"
        PROOF_RESULTS["security"]="PASSED"
    else
        echo -e "${RED}✗ Security headers proof failed${NC}"
        PROOF_RESULTS["security"]="FAILED"
    fi

    echo ""
fi

# ============================================================================
# Proof 5: Rate Limiting (429 with Retry-After)
# ============================================================================
if [ "$PROOF" = "all" ] || [ "$PROOF" = "ratelimit" ]; then
    echo "============================================================================"
    echo "  Proof 5: Rate Limiting (429 with Retry-After header)"
    echo "============================================================================"
    echo ""

    if python3 scripts/proofs/ratelimit_proof.py \
        --output "${OUTPUT_DIR}/ratelimit_proof.json" \
        --api-url "http://localhost:8000"; then
        echo -e "${GREEN}✓ Rate limiting proof generated${NC}"
        PROOF_RESULTS["ratelimit"]="PASSED"
    else
        echo -e "${RED}✗ Rate limiting proof failed${NC}"
        PROOF_RESULTS["ratelimit"]="FAILED"
    fi

    echo ""
fi

# ============================================================================
# Proof 6: DR Mini-Restore (pg_dump → restore → compare)
# ============================================================================
if [ "$PROOF" = "all" ] || [ "$PROOF" = "dr" ]; then
    echo "============================================================================"
    echo "  Proof 6: DR Mini-Restore (backup → restore → validate)"
    echo "============================================================================"
    echo ""

    if bash scripts/proofs/dr_restore_proof.sh \
        --output "${OUTPUT_DIR}/dr_restore.json"; then
        echo -e "${GREEN}✓ DR restore proof generated${NC}"
        PROOF_RESULTS["dr"]="PASSED"
    else
        echo -e "${RED}✗ DR restore proof failed${NC}"
        PROOF_RESULTS["dr"]="FAILED"
    fi

    echo ""
fi

# ============================================================================
# Proof 7: OpenAPI Export (openapi.json with SHA256)
# ============================================================================
if [ "$PROOF" = "all" ] || [ "$PROOF" = "openapi" ]; then
    echo "============================================================================"
    echo "  Proof 7: OpenAPI Export (with SHA256)"
    echo "============================================================================"
    echo ""

    # Fetch OpenAPI schema
    if curl -s -o "${OUTPUT_DIR}/openapi.json" http://localhost:8000/openapi.json; then
        # Generate SHA256 hash
        SHA256=$(sha256sum "${OUTPUT_DIR}/openapi.json" | awk '{print $1}')
        echo "{\"sha256\": \"$SHA256\", \"source\": \"http://localhost:8000/openapi.json\"}" > "${OUTPUT_DIR}/openapi_hash.json"

        echo -e "${GREEN}✓ OpenAPI schema exported${NC}"
        echo "  SHA256: $SHA256"
        PROOF_RESULTS["openapi"]="PASSED"
    else
        echo -e "${RED}✗ OpenAPI export failed${NC}"
        PROOF_RESULTS["openapi"]="FAILED"
    fi

    echo ""
fi

# ============================================================================
# Generate Summary Report
# ============================================================================
echo "============================================================================"
echo "  Proof Generation Summary"
echo "============================================================================"
echo ""

TOTAL_PROOFS=0
PASSED_PROOFS=0
FAILED_PROOFS=0

for proof in "${!PROOF_RESULTS[@]}"; do
    TOTAL_PROOFS=$((TOTAL_PROOFS + 1))
    status="${PROOF_RESULTS[$proof]}"

    if [ "$status" = "PASSED" ]; then
        echo -e "  ${proof}: ${GREEN}✓ PASSED${NC}"
        PASSED_PROOFS=$((PASSED_PROOFS + 1))
    else
        echo -e "  ${proof}: ${RED}✗ FAILED${NC}"
        FAILED_PROOFS=$((FAILED_PROOFS + 1))
    fi
done

echo ""
echo "Results: $PASSED_PROOFS/$TOTAL_PROOFS proofs passed"
echo ""

# Generate summary JSON
cat > "${OUTPUT_DIR}/summary.json" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "total_proofs": $TOTAL_PROOFS,
  "passed": $PASSED_PROOFS,
  "failed": $FAILED_PROOFS,
  "proofs": $(
    echo "{"
    first=true
    for proof in "${!PROOF_RESULTS[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            echo ","
        fi
        echo "    \"$proof\": \"${PROOF_RESULTS[$proof]}\""
    done
    echo "  }"
  )
}
EOF

echo "Artifacts:"
echo "  - ${OUTPUT_DIR}/summary.json"

if [ "$PROOF" = "all" ] || [ "$PROOF" = "sse" ]; then
    echo "  - ${OUTPUT_DIR}/sse_latency.json"
fi

if [ "$PROOF" = "all" ] || [ "$PROOF" = "memo" ]; then
    echo "  - ${OUTPUT_DIR}/memo_hashes.json"
fi

if [ "$PROOF" = "all" ] || [ "$PROOF" = "dlq" ]; then
    echo "  - ${OUTPUT_DIR}/dlq_drill.json"
fi

if [ "$PROOF" = "all" ] || [ "$PROOF" = "security" ]; then
    echo "  - ${OUTPUT_DIR}/security_headers.json"
fi

if [ "$PROOF" = "all" ] || [ "$PROOF" = "ratelimit" ]; then
    echo "  - ${OUTPUT_DIR}/ratelimit_proof.json"
fi

if [ "$PROOF" = "all" ] || [ "$PROOF" = "dr" ]; then
    echo "  - ${OUTPUT_DIR}/dr_restore.json"
fi

if [ "$PROOF" = "all" ] || [ "$PROOF" = "openapi" ]; then
    echo "  - ${OUTPUT_DIR}/openapi.json"
    echo "  - ${OUTPUT_DIR}/openapi_hash.json"
fi

echo ""
echo "============================================================================"

# Exit with failure if any proofs failed
if [ $FAILED_PROOFS -gt 0 ]; then
    echo -e "${RED}❌ Some proofs failed${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All proofs passed!${NC}"
    echo ""
    echo "Next Steps:"
    echo "  1. Review proof artifacts in ${OUTPUT_DIR}/"
    echo "  2. Package evidence: zip -r evidence_pack.zip audit_artifacts/"
    echo "  3. Proceed to Phase 5: Demo polish"
    echo ""
    exit 0
fi
