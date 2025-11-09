#!/usr/bin/env bash
#
# Runtime Verification - Dual Branch Proof
# Verifies MOUNTED endpoints vs DECLARED endpoints for both candidate branches
#
# Targets:
#   - full-consolidation (152 declared endpoints)
#   - mock-providers-twilio (132 declared endpoints)
#
# Requirements: Docker, docker-compose, curl, jq, pytest
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
TS=$(date +"%Y%m%d_%H%M%S")
OUT_BASE="audit_artifacts/runtime_verification_${TS}"
API_URL="${API_URL:-http://localhost:8000}"
TIMEOUT=120

# Branches to verify
BRANCHES=(
  "origin/claude/full-consolidation-011CUo8XMMdfTgWrwjpAVcE1:full-consolidation"
  "origin/claude/mock-providers-twilio-011CUoNy9C1cvzAMeQmPjREU:mock-providers-twilio"
)

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_section() { echo ""; echo -e "${BLUE}========================================${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}========================================${NC}"; }

# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

verify_branch() {
  local BRANCH_REF=$1
  local BRANCH_NAME=$2
  local OUT="${OUT_BASE}/${BRANCH_NAME}"

  mkdir -p "${OUT}"/{openapi,migrations,tests,models,demo,logs}

  log_section "Verifying Branch: ${BRANCH_NAME}"

  # 1. Checkout branch
  log_info "Checking out ${BRANCH_REF}..."
  git checkout "${BRANCH_REF}" --detach 2>&1 | tee "${OUT}/checkout.log" || {
    log_error "Failed to checkout ${BRANCH_REF}"
    return 1
  }

  git rev-parse HEAD > "${OUT}/commit_sha.txt"
  git log -1 --format="%s" > "${OUT}/commit_msg.txt"

  # 2. Environment setup
  log_info "Setting up MOCK_MODE environment..."
  if [ ! -f .env.mock ]; then
    log_error ".env.mock not found"
    echo "ERROR: .env.mock missing" > "${OUT}/errors.txt"
    return 1
  fi

  cp .env.mock .env
  echo "MOCK_MODE=true" >> .env

  # 3. Static analysis (pre-boot)
  log_info "Running static analysis..."

  # Count declared endpoints
  find api -type f -name "*.py" 2>/dev/null | xargs grep -cE "@router\.(get|post|put|patch|delete)\(" 2>/dev/null | \
    awk '{sum+=$1} END {print sum}' > "${OUT}/declared_endpoints_count.txt" || echo "0" > "${OUT}/declared_endpoints_count.txt"

  DECLARED=$(cat "${OUT}/declared_endpoints_count.txt")
  log_info "Declared endpoints (grep): ${DECLARED}"

  # Count SQLAlchemy Base subclasses
  find . -type f -name "*.py" -not -path "*/.git/*" -not -path "*/node_modules/*" 2>/dev/null | \
    xargs grep -hE "^class\s+[A-Z][A-Za-z0-9_]*\(.*Base" 2>/dev/null | \
    sed 's/class\s\+\([A-Za-z0-9_]\+\).*/\1/' | sort -u > "${OUT}/models/base_subclasses.txt" || true

  MODEL_COUNT=$(wc -l < "${OUT}/models/base_subclasses.txt" 2>/dev/null || echo 0)
  log_info "SQLAlchemy models (Base subclasses): ${MODEL_COUNT}"

  # List migration files
  find . -path "*/versions/*.py" -not -name "__*" 2>/dev/null | sort > "${OUT}/migrations/migration_files.txt" || true
  MIGRATION_COUNT=$(wc -l < "${OUT}/migrations/migration_files.txt" 2>/dev/null || echo 0)
  log_info "Alembic migrations: ${MIGRATION_COUNT}"

  # 4. Docker compose up
  log_info "Starting Docker Compose stack..."
  docker compose down -v 2>&1 | tee "${OUT}/logs/compose_down.log" || true
  docker compose up -d --wait 2>&1 | tee "${OUT}/logs/compose_up.log" || {
    log_error "Docker Compose failed to start"
    docker compose logs > "${OUT}/logs/compose_all.log" || true
    echo "ERROR: Compose failed" >> "${OUT}/errors.txt"
    return 1
  }

  docker compose ps > "${OUT}/logs/compose_ps.txt"

  # 5. Wait for API health
  log_info "Waiting for API health (${TIMEOUT}s timeout)..."
  ATTEMPTS=$((TIMEOUT / 2))
  until curl -fsS "${API_URL}/healthz" > "${OUT}/healthz.json" 2>/dev/null || [ $ATTEMPTS -eq 0 ]; do
    sleep 2
    ATTEMPTS=$((ATTEMPTS - 1))
  done

  if [ $ATTEMPTS -eq 0 ]; then
    log_error "API never became healthy"
    docker compose logs api > "${OUT}/logs/api_boot_failure.log" || true
    echo "ERROR: API health check failed" >> "${OUT}/errors.txt"
    return 1
  fi

  log_success "API is healthy"

  # 6. Fetch OpenAPI spec
  log_info "Fetching OpenAPI spec..."
  curl -fsS "${API_URL}/docs/openapi.json" -o "${OUT}/openapi/openapi.json" || {
    log_error "Failed to fetch OpenAPI spec"
    echo "ERROR: OpenAPI fetch failed" >> "${OUT}/errors.txt"
    return 1
  }

  # 7. Count MOUNTED endpoints
  MOUNTED=$(jq '.paths | keys | length' "${OUT}/openapi/openapi.json" 2>/dev/null || echo 0)
  echo "${MOUNTED}" > "${OUT}/openapi/mounted_endpoints_count.txt"

  log_success "OpenAPI fetched: ${MOUNTED} mounted endpoints"

  # Extract all paths
  jq -r '.paths | keys[]' "${OUT}/openapi/openapi.json" | sort > "${OUT}/openapi/endpoint_paths.txt" || true

  # 8. Endpoint reconciliation
  DIFF=$((DECLARED - MOUNTED))
  cat > "${OUT}/openapi/reconciliation.txt" <<EOF
DECLARED endpoints (static grep): ${DECLARED}
MOUNTED endpoints (OpenAPI):      ${MOUNTED}
DIFFERENCE:                        ${DIFF}

Status: $( [ "${DIFF}" -eq 0 ] && echo "✅ MATCH" || echo "⚠️ MISMATCH - ${DIFF} endpoints not mounted" )
EOF

  if [ "${DIFF}" -ne 0 ]; then
    log_warning "Endpoint count mismatch: declared=${DECLARED}, mounted=${MOUNTED}"
  else
    log_success "Endpoint count matches: ${MOUNTED}"
  fi

  # 9. Test ping endpoint
  log_info "Testing /ping endpoint..."
  curl -fsS "${API_URL}/ping" > "${OUT}/ping.json" 2>&1 || {
    log_warning "Ping endpoint failed (may need DB)"
  }

  # 10. Run Alembic migrations
  log_info "Running Alembic migrations..."
  docker compose exec -T api alembic upgrade head > "${OUT}/migrations/upgrade_output.txt" 2>&1 || {
    log_warning "Migrations failed or not configured"
    cat "${OUT}/migrations/upgrade_output.txt" | tail -20
  }

  # Check migration status
  docker compose exec -T api alembic current > "${OUT}/migrations/current.txt" 2>&1 || true

  # 11. Run tests
  log_info "Running pytest..."
  docker compose exec -T api pytest -q --maxfail=1 --disable-warnings \
    --tb=short -v > "${OUT}/tests/pytest_output.txt" 2>&1 || {
    log_warning "Some tests failed (check ${OUT}/tests/pytest_output.txt)"
  }

  # Count test results
  grep -E "passed|failed|error" "${OUT}/tests/pytest_output.txt" | tail -1 > "${OUT}/tests/summary.txt" || echo "N/A" > "${OUT}/tests/summary.txt"

  # 12. Run pytest with coverage (if possible)
  log_info "Running pytest with coverage..."
  docker compose exec -T api pytest --cov=. --cov-report=term --cov-report=xml \
    --disable-warnings -q > "${OUT}/tests/coverage_output.txt" 2>&1 || {
    log_warning "Coverage report failed"
  }

  # Extract coverage percentage
  grep -oP "TOTAL.*\K\d+%" "${OUT}/tests/coverage_output.txt" | tail -1 > "${OUT}/tests/coverage_pct.txt" || echo "N/A" > "${OUT}/tests/coverage_pct.txt"

  # 13. Demo flow test
  log_info "Testing demo flow..."

  # Check if /properties endpoint exists
  if jq -e '.paths | has("/api/v1/properties")' "${OUT}/openapi/openapi.json" >/dev/null 2>&1; then
    # Test properties CRUD
    cat > "${OUT}/demo/property_payload.json" <<'JSON'
{
  "address": "123 Main St",
  "city": "Austin",
  "state": "TX",
  "zip": "78701",
  "property_type": "single_family",
  "status": "active"
}
JSON

    curl -fsS -X POST "${API_URL}/api/v1/properties" \
      -H "Content-Type: application/json" \
      -d @"${OUT}/demo/property_payload.json" > "${OUT}/demo/post_property.json" 2>&1 || {
      log_warning "POST /properties failed (may need auth)"
    }

    curl -fsS "${API_URL}/api/v1/properties" > "${OUT}/demo/get_properties.json" 2>&1 || {
      log_warning "GET /properties failed (may need auth)"
    }

    log_success "Demo flow attempted (check ${OUT}/demo/ for results)"
  else
    log_warning "No /api/v1/properties endpoint found, skipping demo flow"
  fi

  # 14. Collect logs
  log_info "Collecting container logs..."
  docker compose logs api > "${OUT}/logs/api_full.log" || true
  docker compose logs api | tail -500 > "${OUT}/logs/api_tail.log" || true

  # 15. Shutdown
  log_info "Shutting down stack..."
  docker compose down -v 2>&1 | tee "${OUT}/logs/compose_down_final.log" || true

  # 16. Generate summary
  cat > "${OUT}/SUMMARY.txt" <<EOF
================================================================================
RUNTIME VERIFICATION SUMMARY
================================================================================

Branch: ${BRANCH_NAME}
Ref: ${BRANCH_REF}
Commit: $(cat ${OUT}/commit_sha.txt)
Message: $(cat ${OUT}/commit_msg.txt)
Timestamp: ${TS}

--------------------------------------------------------------------------------
ENDPOINT COUNTS
--------------------------------------------------------------------------------
Declared (static grep):  ${DECLARED}
Mounted (OpenAPI):       ${MOUNTED}
Difference:              ${DIFF}
Status:                  $( [ "${DIFF}" -eq 0 ] && echo "✅ MATCH" || echo "⚠️ MISMATCH" )

--------------------------------------------------------------------------------
DATABASE & MIGRATIONS
--------------------------------------------------------------------------------
SQLAlchemy Models:       ${MODEL_COUNT}
Alembic Migrations:      ${MIGRATION_COUNT}
Migration Status:        $(cat ${OUT}/migrations/current.txt 2>/dev/null | head -1 || echo "N/A")

--------------------------------------------------------------------------------
TESTS
--------------------------------------------------------------------------------
Test Results:            $(cat ${OUT}/tests/summary.txt)
Coverage:                $(cat ${OUT}/tests/coverage_pct.txt)

--------------------------------------------------------------------------------
DEMO FLOW
--------------------------------------------------------------------------------
POST /properties:        $([ -f ${OUT}/demo/post_property.json ] && echo "✅ Attempted" || echo "⚠️ Skipped")
GET /properties:         $([ -f ${OUT}/demo/get_properties.json ] && echo "✅ Attempted" || echo "⚠️ Skipped")

--------------------------------------------------------------------------------
ARTIFACTS
--------------------------------------------------------------------------------
OpenAPI spec:            ${OUT}/openapi/openapi.json
Endpoint paths:          ${OUT}/openapi/endpoint_paths.txt
Models list:             ${OUT}/models/base_subclasses.txt
Migration files:         ${OUT}/migrations/migration_files.txt
Test output:             ${OUT}/tests/pytest_output.txt
Coverage report:         ${OUT}/tests/coverage_output.txt
API logs:                ${OUT}/logs/api_full.log
Demo results:            ${OUT}/demo/

================================================================================
EOF

  cat "${OUT}/SUMMARY.txt"
  log_success "Verification complete for ${BRANCH_NAME}"

  return 0
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

log_section "Runtime Verification - Dual Branch Proof"
log_info "Timestamp: $(date -u)"
log_info "Output: ${OUT_BASE}"

mkdir -p "${OUT_BASE}"

# Save comparison table header
cat > "${OUT_BASE}/COMPARISON.txt" <<'EOF'
================================================================================
BRANCH COMPARISON - RUNTIME VERIFICATION
================================================================================

Branch               | Declared | Mounted | Models | Migrations | Tests | Coverage
---------------------|----------|---------|--------|------------|-------|----------
EOF

# Verify each branch
for BRANCH_SPEC in "${BRANCHES[@]}"; do
  IFS=':' read -r BRANCH_REF BRANCH_NAME <<< "${BRANCH_SPEC}"

  if verify_branch "${BRANCH_REF}" "${BRANCH_NAME}"; then
    # Extract metrics
    DECLARED=$(cat "${OUT_BASE}/${BRANCH_NAME}/declared_endpoints_count.txt" 2>/dev/null || echo "ERR")
    MOUNTED=$(cat "${OUT_BASE}/${BRANCH_NAME}/openapi/mounted_endpoints_count.txt" 2>/dev/null || echo "ERR")
    MODELS=$(wc -l < "${OUT_BASE}/${BRANCH_NAME}/models/base_subclasses.txt" 2>/dev/null || echo "ERR")
    MIGRATIONS=$(wc -l < "${OUT_BASE}/${BRANCH_NAME}/migrations/migration_files.txt" 2>/dev/null || echo "ERR")
    TESTS=$(cat "${OUT_BASE}/${BRANCH_NAME}/tests/summary.txt" 2>/dev/null | head -c 20 || echo "ERR")
    COVERAGE=$(cat "${OUT_BASE}/${BRANCH_NAME}/tests/coverage_pct.txt" 2>/dev/null || echo "N/A")

    printf "%-20s | %8s | %7s | %6s | %10s | %5s | %s\n" \
      "${BRANCH_NAME}" "${DECLARED}" "${MOUNTED}" "${MODELS}" "${MIGRATIONS}" "${TESTS:0:5}" "${COVERAGE}" \
      >> "${OUT_BASE}/COMPARISON.txt"
  else
    printf "%-20s | %8s | %7s | %6s | %10s | %5s | %s\n" \
      "${BRANCH_NAME}" "ERROR" "ERROR" "ERROR" "ERROR" "ERROR" "ERROR" \
      >> "${OUT_BASE}/COMPARISON.txt"
  fi

  echo "" # Spacing between branches
done

# Return to original branch
log_info "Returning to original branch: ${CURRENT_BRANCH}"
git checkout "${CURRENT_BRANCH}"

log_section "VERIFICATION COMPLETE"
echo ""
cat "${OUT_BASE}/COMPARISON.txt"
echo ""
echo "Detailed results: ${OUT_BASE}/"
echo "  - full-consolidation/SUMMARY.txt"
echo "  - mock-providers-twilio/SUMMARY.txt"
