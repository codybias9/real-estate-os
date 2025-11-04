#!/bin/bash
# =============================================================================
# Run Real Estate OS Test Suite
# Executes tests in 3 passes: Unit → Integration → E2E
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
OUTPUT_DIR="audit_artifacts/${TIMESTAMP}/tests"
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Real Estate OS - Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Set test environment
export MOCK_MODE=true
export TESTING=true
export DB_DSN="postgresql://postgres:postgres@localhost:5432/real_estate_os_test"
export REDIS_URL="redis://localhost:6379/15"
export JWT_SECRET_KEY="test-secret-key"

echo -e "${YELLOW}📋 Test Configuration:${NC}"
echo "  Mock Mode: ${MOCK_MODE}"
echo "  Database: ${DB_DSN}"
echo "  Redis: ${REDIS_URL}"
echo "  Output: ${OUTPUT_DIR}"
echo ""

# Track overall status
UNIT_STATUS=0
INTEGRATION_STATUS=0
E2E_STATUS=0

# =============================================================================
# PASS 1: UNIT TESTS
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PASS 1: Unit Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Running unit tests (fast, no external dependencies)...${NC}"
echo ""

if pytest tests/unit \
    -v \
    -m unit \
    --cov=api \
    --cov=db \
    --cov-report=html:${OUTPUT_DIR}/coverage_unit/html \
    --cov-report=xml:${OUTPUT_DIR}/coverage_unit/coverage.xml \
    --cov-report=term \
    --junit-xml=${OUTPUT_DIR}/junit_unit.xml \
    --tb=short; then
    echo ""
    echo -e "${GREEN}✓ Unit tests passed${NC}"
    UNIT_STATUS=0
else
    echo ""
    echo -e "${RED}✗ Unit tests failed${NC}"
    UNIT_STATUS=1
fi

echo ""

# =============================================================================
# PASS 2: INTEGRATION TESTS
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PASS 2: Integration Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Running integration tests (database, redis, mock providers)...${NC}"
echo ""

# Ensure test database exists
echo -e "${YELLOW}📊 Setting up test database...${NC}"
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'real_estate_os_test'" | grep -q 1 || \
    psql -U postgres -c "CREATE DATABASE real_estate_os_test;" 2>/dev/null || true

if pytest tests/integration \
    -v \
    -m integration \
    --cov=api \
    --cov=db \
    --cov-append \
    --cov-report=html:${OUTPUT_DIR}/coverage_integration/html \
    --cov-report=xml:${OUTPUT_DIR}/coverage_integration/coverage.xml \
    --cov-report=term \
    --junit-xml=${OUTPUT_DIR}/junit_integration.xml \
    --tb=short; then
    echo ""
    echo -e "${GREEN}✓ Integration tests passed${NC}"
    INTEGRATION_STATUS=0
else
    echo ""
    echo -e "${RED}✗ Integration tests failed${NC}"
    INTEGRATION_STATUS=1
fi

echo ""

# =============================================================================
# PASS 3: END-TO-END TESTS
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PASS 3: End-to-End Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Running e2e tests (full stack workflows)...${NC}"
echo ""

if pytest tests/e2e \
    -v \
    -m e2e \
    --cov=api \
    --cov=db \
    --cov-append \
    --cov-report=html:${OUTPUT_DIR}/coverage_e2e/html \
    --cov-report=xml:${OUTPUT_DIR}/coverage_e2e/coverage.xml \
    --cov-report=term \
    --junit-xml=${OUTPUT_DIR}/junit_e2e.xml \
    --tb=short; then
    echo ""
    echo -e "${GREEN}✓ E2E tests passed${NC}"
    E2E_STATUS=0
else
    echo ""
    echo -e "${RED}✗ E2E tests failed${NC}"
    E2E_STATUS=1
fi

echo ""

# =============================================================================
# COMBINED COVERAGE REPORT
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Combined Coverage Report${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Generate combined coverage report
pytest --cov=api --cov=db \
    --cov-report=html:${OUTPUT_DIR}/coverage_combined/html \
    --cov-report=xml:${OUTPUT_DIR}/coverage_combined/coverage.xml \
    --cov-report=term-missing \
    --collect-only \
    tests/ > /dev/null 2>&1 || true

# Parse coverage percentage
COVERAGE=$(grep -oP 'TOTAL.*\K\d+(?=%)' ${OUTPUT_DIR}/coverage_combined/coverage.xml 2>/dev/null || echo "0")

echo -e "  Total Coverage: ${GREEN}${COVERAGE}%${NC}"
echo ""
echo -e "  ${YELLOW}Reports:${NC}"
echo "    HTML:  ${OUTPUT_DIR}/coverage_combined/html/index.html"
echo "    XML:   ${OUTPUT_DIR}/coverage_combined/coverage.xml"
echo ""

# =============================================================================
# SUMMARY
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Count test results
UNIT_TOTAL=$(grep -oP 'tests="\K\d+' ${OUTPUT_DIR}/junit_unit.xml 2>/dev/null || echo "0")
UNIT_FAILURES=$(grep -oP 'failures="\K\d+' ${OUTPUT_DIR}/junit_unit.xml 2>/dev/null || echo "0")
UNIT_PASSED=$((UNIT_TOTAL - UNIT_FAILURES))

INTEGRATION_TOTAL=$(grep -oP 'tests="\K\d+' ${OUTPUT_DIR}/junit_integration.xml 2>/dev/null || echo "0")
INTEGRATION_FAILURES=$(grep -oP 'failures="\K\d+' ${OUTPUT_DIR}/junit_integration.xml 2>/dev/null || echo "0")
INTEGRATION_PASSED=$((INTEGRATION_TOTAL - INTEGRATION_FAILURES))

E2E_TOTAL=$(grep -oP 'tests="\K\d+' ${OUTPUT_DIR}/junit_e2e.xml 2>/dev/null || echo "0")
E2E_FAILURES=$(grep -oP 'failures="\K\d+' ${OUTPUT_DIR}/junit_e2e.xml 2>/dev/null || echo "0")
E2E_PASSED=$((E2E_TOTAL - E2E_FAILURES))

TOTAL_TESTS=$((UNIT_TOTAL + INTEGRATION_TOTAL + E2E_TOTAL))
TOTAL_PASSED=$((UNIT_PASSED + INTEGRATION_PASSED + E2E_PASSED))
TOTAL_FAILED=$((UNIT_FAILURES + INTEGRATION_FAILURES + E2E_FAILURES))

echo -e "  ${BLUE}Unit Tests:${NC}         ${UNIT_PASSED}/${UNIT_TOTAL} passed"
echo -e "  ${BLUE}Integration Tests:${NC}  ${INTEGRATION_PASSED}/${INTEGRATION_TOTAL} passed"
echo -e "  ${BLUE}E2E Tests:${NC}          ${E2E_PASSED}/${E2E_TOTAL} passed"
echo ""
echo -e "  ${BLUE}Total:${NC}              ${GREEN}${TOTAL_PASSED}/${TOTAL_TESTS} passed${NC}"
echo -e "  ${BLUE}Coverage:${NC}           ${GREEN}${COVERAGE}%${NC}"
echo ""

# Generate test report summary JSON
cat > "${OUTPUT_DIR}/summary.json" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "test_suite": "real-estate-os",
  "mode": "mock",
  "results": {
    "unit": {
      "total": ${UNIT_TOTAL},
      "passed": ${UNIT_PASSED},
      "failed": ${UNIT_FAILURES},
      "status": "$( [ $UNIT_STATUS -eq 0 ] && echo 'passed' || echo 'failed' )"
    },
    "integration": {
      "total": ${INTEGRATION_TOTAL},
      "passed": ${INTEGRATION_PASSED},
      "failed": ${INTEGRATION_FAILURES},
      "status": "$( [ $INTEGRATION_STATUS -eq 0 ] && echo 'passed' || echo 'failed' )"
    },
    "e2e": {
      "total": ${E2E_TOTAL},
      "passed": ${E2E_PASSED},
      "failed": ${E2E_FAILURES},
      "status": "$( [ $E2E_STATUS -eq 0 ] && echo 'passed' || echo 'failed' )"
    }
  },
  "coverage": {
    "percentage": ${COVERAGE},
    "threshold": 70,
    "passed": $( [ ${COVERAGE} -ge 70 ] && echo 'true' || echo 'false' )
  }
}
EOF

echo -e "  ${YELLOW}Test Summary:${NC} ${OUTPUT_DIR}/summary.json"
echo ""

# Overall exit status
if [ $TOTAL_FAILED -eq 0 ] && [ ${COVERAGE} -ge 70 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ All tests passed! Coverage ${COVERAGE}% ≥ 70%${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Tests failed or coverage below threshold${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
