#!/bin/bash
#
# Run Introspection Suite
#
# Generates endpoints.json and models.json by introspecting the running application.
# Requires: API and DB to be running (Docker stack up)
#
# Usage:
#   ./scripts/run_introspection.sh [output_dir]
#
# Default output_dir: audit_artifacts/<timestamp>/
#

set -e

# Determine output directory
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
OUTPUT_DIR="${1:-audit_artifacts/${TIMESTAMP}}"

echo "================================================"
echo "  Real Estate OS - Introspection Suite"
echo "================================================"
echo ""
echo "Output Directory: ${OUTPUT_DIR}"
echo ""

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Run endpoint introspection
echo "→ Introspecting API endpoints..."
python scripts/introspect_endpoints.py > "${OUTPUT_DIR}/endpoints.json" 2>&1

if [ $? -eq 0 ]; then
    echo "  ✅ endpoints.json generated"
    # Extract stats from stderr
    ENDPOINT_COUNT=$(jq '.statistics.total_endpoints' "${OUTPUT_DIR}/endpoints.json")
    echo "     Total Endpoints: ${ENDPOINT_COUNT}"
else
    echo "  ❌ Endpoint introspection failed"
    exit 1
fi

echo ""

# Run model introspection
echo "→ Introspecting database models..."
python scripts/introspect_models.py > "${OUTPUT_DIR}/models.json" 2>&1

if [ $? -eq 0 ]; then
    echo "  ✅ models.json generated"
    # Extract stats
    MODEL_COUNT=$(jq '.statistics.total_models' "${OUTPUT_DIR}/models.json")
    TABLE_COUNT=$(jq '.statistics.total_tables' "${OUTPUT_DIR}/models.json")
    echo "     Total Models: ${MODEL_COUNT}"
    echo "     Total Tables: ${TABLE_COUNT}"
else
    echo "  ❌ Model introspection failed"
    exit 1
fi

echo ""
echo "================================================"
echo "  ✅ Introspection Complete"
echo "================================================"
echo ""
echo "Artifacts:"
echo "  - ${OUTPUT_DIR}/endpoints.json"
echo "  - ${OUTPUT_DIR}/models.json"
echo ""
echo "Validation:"
echo "  jq '.statistics' ${OUTPUT_DIR}/endpoints.json"
echo "  jq '.statistics' ${OUTPUT_DIR}/models.json"
echo ""
