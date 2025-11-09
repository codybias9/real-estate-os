#!/usr/bin/env bash
#
# Enhanced Runtime Verification - Hardened Edition
# Addresses all false-positive failure modes
#
# Key improvements over dual.sh:
# - Route introspection (app.routes vs OpenAPI)
# - Alembic heads validation (fails on multiple heads)
# - Coverage config debugging
# - SSE event capture
# - Network isolation verification (mock provider guard)
# - Docker compose config capture
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
OUT_BASE="audit_artifacts/runtime_enhanced_${TS}"
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
# ENHANCED VERIFICATION
# ============================================================================

verify_branch_enhanced() {
  local BRANCH_REF=$1
  local BRANCH_NAME=$2
  local OUT="${OUT_BASE}/${BRANCH_NAME}"

  mkdir -p "${OUT}"/{openapi,migrations,tests,models,demo,logs,introspection,network,compose}

  log_section "Enhanced Verification: ${BRANCH_NAME}"

  # 1. Checkout
  log_info "Checking out ${BRANCH_REF}..."
  git checkout "${BRANCH_REF}" --detach 2>&1 | tee "${OUT}/checkout.log" || {
    log_error "Failed to checkout"
    return 1
  }

  git rev-parse HEAD > "${OUT}/commit_sha.txt"
  git log -1 --format="%s" > "${OUT}/commit_msg.txt"

  # 2. Environment setup
  log_info "Setting up MOCK_MODE + VERIFY_MODE..."
  if [ ! -f .env.mock ]; then
    log_error ".env.mock not found"
    return 1
  fi

  cp .env.mock .env
  cat >> .env <<EOF
MOCK_MODE=true
VERIFY_MODE=true
# Bogus credentials to catch accidental real provider usage
SENDGRID_API_KEY=BOGUS_KEY_SHOULD_NOT_BE_USED
TWILIO_ACCOUNT_SID=BOGUS_SID
TWILIO_AUTH_TOKEN=BOGUS_TOKEN
AWS_ACCESS_KEY_ID=BOGUS_AWS_KEY
EOF

  # 3. Capture compose config BEFORE boot
  log_info "Capturing docker compose configuration..."
  docker compose config > "${OUT}/compose/compose_resolved.yml" 2>&1 || {
    log_warning "docker compose config failed"
  }

  # List services
  docker compose config --services > "${OUT}/compose/services.txt" 2>&1 || true

  # Capture compose file hash
  if [ -f docker-compose.yml ]; then
    md5sum docker-compose.yml > "${OUT}/compose/compose_hash.txt" 2>&1 || true
  fi

  # 4. Static analysis
  log_info "Running static analysis..."
  find api -type f -name "*.py" 2>/dev/null | xargs grep -cE "@router\.(get|post|put|patch|delete)\(" 2>/dev/null | \
    awk '{sum+=$1} END {print sum}' > "${OUT}/declared_endpoints_count.txt" || echo "0" > "${OUT}/declared_endpoints_count.txt"

  DECLARED=$(cat "${OUT}/declared_endpoints_count.txt")

  # 5. Docker compose up
  log_info "Starting Docker stack..."
  docker compose down -v 2>&1 | tee "${OUT}/logs/compose_down.log" || true
  docker compose up -d --wait 2>&1 | tee "${OUT}/logs/compose_up.log" || {
    log_error "Docker Compose failed"
    docker compose logs > "${OUT}/logs/compose_all.log" || true
    return 1
  }

  docker compose ps > "${OUT}/logs/compose_ps.txt"

  # 6. Wait for health
  log_info "Waiting for API health..."
  ATTEMPTS=$((TIMEOUT / 2))
  until curl -fsS "${API_URL}/healthz" > "${OUT}/healthz.json" 2>/dev/null || [ $ATTEMPTS -eq 0 ]; do
    sleep 2
    ATTEMPTS=$((ATTEMPTS - 1))
  done

  if [ $ATTEMPTS -eq 0 ]; then
    log_error "API never became healthy"
    docker compose logs api > "${OUT}/logs/api_boot_failure.log" || true
    return 1
  fi

  log_success "API is healthy"

  # 7. ENHANCED: Introspection route dump
  log_info "Fetching route introspection (app.routes)..."
  curl -fsS "${API_URL}/__introspection/routes" > "${OUT}/introspection/routes_raw.json" 2>&1 || {
    log_warning "Introspection endpoint not available (add api.introspection router to main.py)"
    echo '{"error":"introspection not enabled"}' > "${OUT}/introspection/routes_raw.json"
  }

  # Extract route count from introspection
  ROUTES_RAW=$(jq -r '.total_routes // 0' "${OUT}/introspection/routes_raw.json" 2>/dev/null || echo "N/A")

  # 8. Fetch OpenAPI spec
  log_info "Fetching OpenAPI spec..."
  curl -fsS "${API_URL}/docs/openapi.json" -o "${OUT}/openapi/openapi.json" || {
    log_error "Failed to fetch OpenAPI"
    return 1
  }

  MOUNTED=$(jq '.paths | keys | length' "${OUT}/openapi/openapi.json" 2>/dev/null || echo 0)
  echo "${MOUNTED}" > "${OUT}/openapi/mounted_endpoints_count.txt"

  log_success "OpenAPI: ${MOUNTED} endpoints, app.routes: ${ROUTES_RAW}"

  # Cross-check: OpenAPI vs app.routes
  if [ "${ROUTES_RAW}" != "N/A" ]; then
    DIFF_ROUTES=$((ROUTES_RAW - MOUNTED))
    if [ "${DIFF_ROUTES}" -gt 5 ]; then
      log_warning "app.routes (${ROUTES_RAW}) > OpenAPI (${MOUNTED}) by ${DIFF_ROUTES} routes"
      echo "WARN: ${DIFF_ROUTES} routes not in OpenAPI spec" >> "${OUT}/introspection/warnings.txt"
    fi
  fi

  # Extract endpoint paths
  jq -r '.paths | keys[]' "${OUT}/openapi/openapi.json" | sort > "${OUT}/openapi/endpoint_paths.txt" || true

  # 9. ENHANCED: Alembic heads validation
  log_info "Validating Alembic migrations..."

  # Upgrade to head
  docker compose exec -T api alembic upgrade head > "${OUT}/migrations/upgrade_output.txt" 2>&1 || {
    log_warning "Migration upgrade failed"
  }

  # Check for multiple heads (FAIL if found)
  docker compose exec -T api alembic heads -v > "${OUT}/migrations/heads.txt" 2>&1 || true
  HEAD_COUNT=$(grep -cE "^[a-f0-9]+ \(" "${OUT}/migrations/heads.txt" 2>/dev/null || echo "0")

  if [ "${HEAD_COUNT}" -gt 1 ]; then
    log_error "Multiple Alembic heads detected (${HEAD_COUNT})!"
    echo "CRITICAL: ${HEAD_COUNT} migration heads found" >> "${OUT}/migrations/CRITICAL.txt"
    cat "${OUT}/migrations/heads.txt"
  else
    log_success "Single Alembic head"
  fi

  # Check current migration
  docker compose exec -T api alembic current > "${OUT}/migrations/current.txt" 2>&1 || true

  # Full migration history
  docker compose exec -T api alembic history --verbose > "${OUT}/migrations/history_full.txt" 2>&1 || true
  docker compose exec -T api alembic history --verbose | tail -50 > "${OUT}/migrations/history_tail.txt" 2>&1 || true

  # 10. ENHANCED: Provider introspection
  log_info "Checking provider configuration..."
  curl -fsS "${API_URL}/__introspection/providers" > "${OUT}/introspection/providers.json" 2>&1 || {
    log_warning "Provider introspection not available"
  }

  # Check logs for "USING MOCK" messages
  docker compose logs api | grep -i "mock\|provider" | head -50 > "${OUT}/introspection/mock_logs.txt" || true

  # 11. ENHANCED: Network isolation check
  log_info "Checking for accidental outbound connections..."

  # Look for DNS errors (gaierror) or connection timeouts that would indicate real API attempts
  docker compose logs api | grep -iE "gaierror|connection.*refused|timeout|ssl.*error" > "${OUT}/network/connection_errors.txt" 2>&1 || true

  ERROR_COUNT=$(wc -l < "${OUT}/network/connection_errors.txt" 2>/dev/null || echo 0)

  if [ "${ERROR_COUNT}" -gt 0 ]; then
    log_warning "Found ${ERROR_COUNT} network error lines (may indicate real provider attempts)"
    cat "${OUT}/network/connection_errors.txt" | head -20
  else
    log_success "No suspicious network errors detected"
  fi

  # Check for bogus credentials in logs (should NOT appear if mocks are working)
  docker compose logs api | grep -i "BOGUS" > "${OUT}/network/bogus_credential_leaks.txt" 2>&1 || true

  BOGUS_COUNT=$(wc -l < "${OUT}/network/bogus_credential_leaks.txt" 2>/dev/null || echo 0)

  if [ "${BOGUS_COUNT}" -gt 0 ]; then
    log_error "BOGUS credentials detected in logs! Real providers may be instantiating!"
    cat "${OUT}/network/bogus_credential_leaks.txt" | head -10
  fi

  # 12. ENHANCED: Test execution (two passes)
  log_info "Running tests (fast fail + full run)..."

  # Pass 1: Fast fail
  docker compose exec -T api pytest -q --maxfail=1 --disable-warnings --tb=short \
    > "${OUT}/tests/pytest_fast.txt" 2>&1 || {
    log_warning "Fast test run hit failures"
  }

  # Pass 2: Full run with JUnit XML
  docker compose exec -T api pytest -q --disable-warnings --tb=short \
    --junitxml=/tmp/junit.xml > "${OUT}/tests/pytest_full.txt" 2>&1 || {
    log_warning "Full test run had failures"
  }

  # Copy JUnit XML out
  docker compose exec -T api cat /tmp/junit.xml > "${OUT}/tests/junit.xml" 2>&1 || true

  # Count results
  grep -E "passed|failed|error" "${OUT}/tests/pytest_full.txt" | tail -1 > "${OUT}/tests/summary.txt" || echo "N/A" > "${OUT}/tests/summary.txt"

  # 13. ENHANCED: Coverage with config debugging
  log_info "Running pytest with coverage (debug mode)..."

  # Run with coverage
  docker compose exec -T api pytest --cov=. --cov-report=term --cov-report=xml --cov-report=html \
    --disable-warnings -q > "${OUT}/tests/coverage_output.txt" 2>&1 || {
    log_warning "Coverage failed"
  }

  # Extract coverage percentage
  grep -oP "TOTAL.*\K\d+%" "${OUT}/tests/coverage_output.txt" | tail -1 > "${OUT}/tests/coverage_pct.txt" || echo "N/A" > "${OUT}/tests/coverage_pct.txt"

  # Copy coverage.xml out
  docker compose exec -T api cat coverage.xml > "${OUT}/tests/coverage.xml" 2>&1 || true

  # DEBUG: Coverage config
  docker compose exec -T api coverage debug sys > "${OUT}/tests/coverage_debug_sys.txt" 2>&1 || true
  docker compose exec -T api coverage debug config > "${OUT}/tests/coverage_debug_config.txt" 2>&1 || true

  # 14. ENHANCED: Demo flow with enrichment check
  log_info "Testing demo flow (POST→enrichment→GET)..."

  if jq -e '.paths | has("/api/v1/properties")' "${OUT}/openapi/openapi.json" >/dev/null 2>&1; then
    # POST property
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

    # Extract property ID if available
    PROPERTY_ID=$(jq -r '.id // empty' "${OUT}/demo/post_property.json" 2>/dev/null || echo "")

    # GET properties list
    curl -fsS "${API_URL}/api/v1/properties" > "${OUT}/demo/get_properties.json" 2>&1 || {
      log_warning "GET /properties failed"
    }

    # If we got a property ID, fetch it specifically
    if [ -n "${PROPERTY_ID}" ]; then
      curl -fsS "${API_URL}/api/v1/properties/${PROPERTY_ID}" > "${OUT}/demo/get_property_detail.json" 2>&1 || true
    fi

    log_success "Demo flow attempted"
  else
    log_warning "No /api/v1/properties endpoint, skipping demo"
  fi

  # 15. ENHANCED: SSE probe
  log_info "Probing for SSE events..."

  if jq -e '.paths | has("/api/v1/sse")' "${OUT}/openapi/openapi.json" >/dev/null 2>&1; then
    # Open SSE connection for 5 seconds
    timeout 5 curl -N -H "Accept: text/event-stream" "${API_URL}/api/v1/sse" \
      > "${OUT}/demo/sse_events.txt" 2>&1 || true

    EVENT_COUNT=$(grep -c "^data:" "${OUT}/demo/sse_events.txt" 2>/dev/null || echo 0)
    log_info "Captured ${EVENT_COUNT} SSE events"
  else
    log_info "No SSE endpoint found"
  fi

  # 16. ENHANCED: DLQ smoke test (optional)
  log_info "Checking for DLQ endpoint..."

  if jq -e '.paths | has("/api/v1/ops/dlq")' "${OUT}/openapi/openapi.json" >/dev/null 2>&1; then
    # Get DLQ count before
    curl -fsS "${API_URL}/api/v1/ops/dlq" > "${OUT}/demo/dlq_before.json" 2>&1 || true

    # Try to trigger DLQ (POST bad message)
    curl -fsS -X POST "${API_URL}/api/v1/ops/dlq/test-failure" \
      -H "Content-Type: application/json" \
      -d '{"invalid":"data"}' > "${OUT}/demo/dlq_trigger.json" 2>&1 || true

    # Get DLQ count after
    curl -fsS "${API_URL}/api/v1/ops/dlq" > "${OUT}/demo/dlq_after.json" 2>&1 || true

    log_info "DLQ smoke test completed"
  fi

  # 17. Collect logs
  log_info "Collecting container logs..."
  docker compose logs api > "${OUT}/logs/api_full.log" || true
  docker compose logs api | tail -1000 > "${OUT}/logs/api_tail.log" || true

  # Capture specific log patterns
  docker compose logs api | grep -i "error\|exception\|traceback" > "${OUT}/logs/errors.log" 2>&1 || true
  docker compose logs api | grep -i "warning" > "${OUT}/logs/warnings.log" 2>&1 || true

  # 18. Shutdown
  log_info "Shutting down stack..."
  docker compose down -v 2>&1 | tee "${OUT}/logs/compose_down_final.log" || true

  # 19. Generate enhanced summary
  cat > "${OUT}/SUMMARY.txt" <<EOF
================================================================================
ENHANCED RUNTIME VERIFICATION SUMMARY
================================================================================

Branch: ${BRANCH_NAME}
Ref: ${BRANCH_REF}
Commit: $(cat ${OUT}/commit_sha.txt)
Timestamp: ${TS}

--------------------------------------------------------------------------------
ENDPOINT COUNTS (CRITICAL)
--------------------------------------------------------------------------------
Declared (static grep):  ${DECLARED}
Mounted (OpenAPI):       ${MOUNTED}
app.routes total:        ${ROUTES_RAW}
Difference (decl-mount): $((DECLARED - MOUNTED))
Status:                  $( [ $((DECLARED - MOUNTED)) -le 5 ] && echo "✅ MATCH" || echo "⚠️ MISMATCH" )

Route Introspection:     $( [ "${ROUTES_RAW}" != "N/A" ] && echo "✅ Available" || echo "⚠️ Not enabled" )
OpenAPI vs app.routes:   $( [ "${ROUTES_RAW}" != "N/A" ] && echo "$((ROUTES_RAW - MOUNTED)) difference" || echo "N/A" )

--------------------------------------------------------------------------------
MIGRATIONS (CRITICAL)
--------------------------------------------------------------------------------
Alembic Heads:           ${HEAD_COUNT} $( [ "${HEAD_COUNT}" -eq 1 ] && echo "✅" || echo "❌ MULTIPLE HEADS!" )
Migration Status:        $(cat ${OUT}/migrations/current.txt 2>/dev/null | head -1 || echo "N/A")
Upgrade Success:         $( grep -q "Running upgrade" ${OUT}/migrations/upgrade_output.txt && echo "✅" || echo "⚠️ Check logs" )

--------------------------------------------------------------------------------
TESTS (CRITICAL)
--------------------------------------------------------------------------------
Fast Run (maxfail=1):    $(head -1 ${OUT}/tests/pytest_fast.txt 2>/dev/null || echo "N/A")
Full Run Results:        $(cat ${OUT}/tests/summary.txt)
Coverage:                $(cat ${OUT}/tests/coverage_pct.txt)
JUnit XML:               $( [ -f ${OUT}/tests/junit.xml ] && echo "✅ Generated" || echo "⚠️ Missing" )

--------------------------------------------------------------------------------
MOCK PROVIDERS (CRITICAL)
--------------------------------------------------------------------------------
Provider Config:         $( [ -f ${OUT}/introspection/providers.json ] && jq -r '.providers' ${OUT}/introspection/providers.json 2>/dev/null || echo "N/A" )
Network Errors:          ${ERROR_COUNT} lines $( [ "${ERROR_COUNT}" -eq 0 ] && echo "✅" || echo "⚠️ Check network/" )
Bogus Creds in Logs:     ${BOGUS_COUNT} occurrences $( [ "${BOGUS_COUNT}" -eq 0 ] && echo "✅" || echo "❌ LEAK!" )

--------------------------------------------------------------------------------
DEMO FLOW
--------------------------------------------------------------------------------
POST /properties:        $( [ -f ${OUT}/demo/post_property.json ] && echo "✅ Attempted" || echo "⚠️ Skipped" )
GET /properties:         $( [ -f ${OUT}/demo/get_properties.json ] && echo "✅ Attempted" || echo "⚠️ Skipped" )
SSE Events Captured:     $( [ -f ${OUT}/demo/sse_events.txt ] && echo "$(grep -c '^data:' ${OUT}/demo/sse_events.txt || echo 0) events" || echo "N/A" )
DLQ Smoke Test:          $( [ -f ${OUT}/demo/dlq_after.json ] && echo "✅ Attempted" || echo "N/A" )

--------------------------------------------------------------------------------
DOCKER COMPOSE
--------------------------------------------------------------------------------
Services:                $(cat ${OUT}/compose/services.txt 2>/dev/null | wc -l || echo "N/A")
Config Hash:             $(cat ${OUT}/compose/compose_hash.txt 2>/dev/null || echo "N/A")
Resolved Config:         $( [ -f ${OUT}/compose/compose_resolved.yml ] && echo "✅ Captured" || echo "⚠️ Failed" )

--------------------------------------------------------------------------------
ARTIFACTS
--------------------------------------------------------------------------------
OpenAPI spec:            ${OUT}/openapi/openapi.json
Route introspection:     ${OUT}/introspection/routes_raw.json
Provider config:         ${OUT}/introspection/providers.json
Alembic heads:           ${OUT}/migrations/heads.txt
Alembic history:         ${OUT}/migrations/history_full.txt
Test JUnit XML:          ${OUT}/tests/junit.xml
Coverage XML:            ${OUT}/tests/coverage.xml
Coverage debug:          ${OUT}/tests/coverage_debug_sys.txt
Network errors:          ${OUT}/network/connection_errors.txt
Bogus cred leaks:        ${OUT}/network/bogus_credential_leaks.txt
SSE events:              ${OUT}/demo/sse_events.txt
DLQ test:                ${OUT}/demo/dlq_*.json
Error logs:              ${OUT}/logs/errors.log
Full API logs:           ${OUT}/logs/api_full.log

================================================================================
PASS/FAIL CRITERIA
================================================================================

✅ PASS if:
- Mounted endpoints ≥ 140 (or ≥ 95% of declared)
- Single Alembic head, upgrade succeeds
- Tests: ≥60% pass rate
- Demo flow: POST + GET work
- Mock providers: Zero bogus cred leaks, zero network errors
- No unhandled exceptions in logs

⚠️ WARN if:
- 5-20 endpoints missing (check feature flags)
- <60% test pass but >40%
- Minor network errors (<5 lines)

❌ FAIL if:
- <100 mounted endpoints
- Multiple Alembic heads
- Bogus credentials in logs (real providers instantiated)
- Tests crash completely
- API won't boot

================================================================================
EOF

  cat "${OUT}/SUMMARY.txt"
  log_success "Enhanced verification complete for ${BRANCH_NAME}"

  return 0
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

log_section "Enhanced Runtime Verification"
log_info "Timestamp: $(date -u)"
log_info "Output: ${OUT_BASE}"

mkdir -p "${OUT_BASE}"

# Verify each branch
for BRANCH_SPEC in "${BRANCHES[@]}"; do
  IFS=':' read -r BRANCH_REF BRANCH_NAME <<< "${BRANCH_SPEC}"

  if verify_branch_enhanced "${BRANCH_REF}" "${BRANCH_NAME}"; then
    log_success "${BRANCH_NAME} verification completed"
  else
    log_error "${BRANCH_NAME} verification failed"
  fi

  echo ""
done

# Return to original branch
log_info "Returning to original branch: ${CURRENT_BRANCH}"
git checkout "${CURRENT_BRANCH}"

log_section "ENHANCED VERIFICATION COMPLETE"
echo ""
echo "Results: ${OUT_BASE}/"
echo "  - full-consolidation/SUMMARY.txt"
echo "  - mock-providers-twilio/SUMMARY.txt"
echo ""
echo "Review SUMMARY.txt files and compare against PASS/FAIL criteria"
