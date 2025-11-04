#!/bin/bash
#
# Run Real Estate OS Test Suite (Phase 3)
#
# Executes tests in three passes:
#  - Pass A: Backend tests (no services required - uses SQLite in-memory)
#  - Pass B: Integration tests (requires Docker services)
#  - Pass C: E2E tests (requires full stack + frontend)
#
# Prerequisites:
#  - Python 3.9+ with venv
#  - pytest, pytest-cov installed
#  - For Pass B/C: Docker stack running (see scripts/start_docker_stack.sh)
#
# Usage:
#   ./scripts/run_tests.sh [--pass <A|B|C|all>] [--no-coverage] [--output <dir>]
#
# Options:
#   --pass <A|B|C|all>  : Run specific pass or all (default: all)
#   --no-coverage       : Skip coverage reporting
#   --output <dir>      : Output directory for artifacts (default: audit_artifacts/<timestamp>/tests)
#   --fail-fast         : Stop on first test failure
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================================"
echo "  Real Estate OS - Test Suite Execution (Phase 3)"
echo "============================================================================"
echo ""

# Parse arguments
PASS="all"
COVERAGE=true
FAIL_FAST=false
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
OUTPUT_DIR="audit_artifacts/${TIMESTAMP}/tests"

while [[ $# -gt 0 ]]; do
    case $1 in
        --pass)
            PASS="$2"
            shift 2
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --fail-fast)
            FAIL_FAST=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--pass <A|B|C|all>] [--no-coverage] [--output <dir>] [--fail-fast]"
            exit 1
            ;;
    esac
done

# Create output directories
mkdir -p "${OUTPUT_DIR}/backend"
mkdir -p "${OUTPUT_DIR}/integration"
mkdir -p "${OUTPUT_DIR}/e2e"
mkdir -p "${OUTPUT_DIR}/coverage"

echo "Configuration:"
echo "  Pass: $PASS"
echo "  Coverage: $COVERAGE"
echo "  Fail Fast: $FAIL_FAST"
echo "  Output: ${OUTPUT_DIR}"
echo ""

# Build pytest base command
PYTEST_BASE="pytest -v --tb=short --color=yes"

if [ "$FAIL_FAST" = true ]; then
    PYTEST_BASE="$PYTEST_BASE -x"
fi

# Track test results
PASS_A_STATUS=0
PASS_B_STATUS=0
PASS_C_STATUS=0

# ============================================================================
# Pass A: Backend Tests (No Services Required)
# ============================================================================
if [ "$PASS" = "all" ] || [ "$PASS" = "A" ]; then
    echo "============================================================================"
    echo "  Pass A: Backend Tests (No Services Required)"
    echo "============================================================================"
    echo ""
    echo "→ Running backend tests with SQLite in-memory database..."
    echo ""

    # Backend tests use conftest.py fixtures with SQLite in-memory
    # No Docker services required
    if $PYTEST_BASE \
        tests/backend/ \
        --junitxml="${OUTPUT_DIR}/backend/junit.xml" \
        --html="${OUTPUT_DIR}/backend/report.html" \
        --self-contained-html 2>&1 | tee "${OUTPUT_DIR}/backend/output.log"; then

        echo -e "${GREEN}✓ Pass A: Backend tests completed successfully${NC}"
        PASS_A_STATUS=0
    else
        echo -e "${RED}✗ Pass A: Backend tests failed${NC}"
        PASS_A_STATUS=1

        if [ "$FAIL_FAST" = true ]; then
            echo ""
            echo "Stopping due to --fail-fast flag"
            exit 1
        fi
    fi

    echo ""
fi

# ============================================================================
# Pass B: Integration Tests (Requires Docker Services)
# ============================================================================
if [ "$PASS" = "all" ] || [ "$PASS" = "B" ]; then
    echo "============================================================================"
    echo "  Pass B: Integration Tests (Requires Docker Services)"
    echo "============================================================================"
    echo ""

    # Check if Docker services are running
    echo "→ Checking Docker services..."

    if ! docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps | grep -q "Up"; then
        echo -e "${YELLOW}⚠ Warning: Docker services may not be running${NC}"
        echo "  To start services: ./scripts/start_docker_stack.sh"
        echo ""
        echo "  Attempting to run tests anyway (some may fail)..."
        echo ""
    else
        echo -e "${GREEN}✓ Docker services detected${NC}"
        echo ""
    fi

    echo "→ Running integration tests..."
    echo ""

    # Integration tests require: postgres, redis, rabbitmq, api (mock mode)
    # Tests marked with @pytest.mark.integration
    if [ "$COVERAGE" = true ]; then
        COVERAGE_ARGS="--cov=api --cov=db --cov-report=html:${OUTPUT_DIR}/coverage/html --cov-report=xml:${OUTPUT_DIR}/coverage/coverage.xml --cov-report=term-missing"
    else
        COVERAGE_ARGS=""
    fi

    if $PYTEST_BASE \
        tests/integration/ \
        $COVERAGE_ARGS \
        --junitxml="${OUTPUT_DIR}/integration/junit.xml" \
        --html="${OUTPUT_DIR}/integration/report.html" \
        --self-contained-html 2>&1 | tee "${OUTPUT_DIR}/integration/output.log"; then

        echo -e "${GREEN}✓ Pass B: Integration tests completed successfully${NC}"
        PASS_B_STATUS=0
    else
        echo -e "${RED}✗ Pass B: Integration tests failed${NC}"
        PASS_B_STATUS=1

        if [ "$FAIL_FAST" = true ]; then
            echo ""
            echo "Stopping due to --fail-fast flag"
            exit 1
        fi
    fi

    echo ""
fi

# ============================================================================
# Pass C: E2E Tests (Requires Full Stack + Frontend)
# ============================================================================
if [ "$PASS" = "all" ] || [ "$PASS" = "C" ]; then
    echo "============================================================================"
    echo "  Pass C: E2E Tests (Requires Full Stack + Frontend)"
    echo "============================================================================"
    echo ""

    # Check if frontend is running
    echo "→ Checking frontend availability..."

    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
        echo -e "${GREEN}✓ Frontend is accessible${NC}"
        echo ""
    else
        echo -e "${YELLOW}⚠ Warning: Frontend may not be running${NC}"
        echo "  E2E tests require full Docker stack with frontend"
        echo "  To start: ./scripts/start_docker_stack.sh"
        echo ""
        echo "  Attempting to run tests anyway (some may fail)..."
        echo ""
    fi

    echo "→ Running E2E tests..."
    echo ""

    # E2E tests require: full stack (api, frontend, all services)
    # Tests marked with @pytest.mark.e2e
    if $PYTEST_BASE \
        tests/e2e/ \
        --junitxml="${OUTPUT_DIR}/e2e/junit.xml" \
        --html="${OUTPUT_DIR}/e2e/report.html" \
        --self-contained-html 2>&1 | tee "${OUTPUT_DIR}/e2e/output.log"; then

        echo -e "${GREEN}✓ Pass C: E2E tests completed successfully${NC}"
        PASS_C_STATUS=0
    else
        echo -e "${RED}✗ Pass C: E2E tests failed${NC}"
        PASS_C_STATUS=1
    fi

    echo ""
fi

# ============================================================================
# Summary Report
# ============================================================================
echo "============================================================================"
echo "  Test Execution Summary"
echo "============================================================================"
echo ""

# Calculate overall status
OVERALL_STATUS=0

if [ "$PASS" = "all" ] || [ "$PASS" = "A" ]; then
    if [ $PASS_A_STATUS -eq 0 ]; then
        echo -e "  Pass A (Backend):      ${GREEN}✓ PASSED${NC}"
    else
        echo -e "  Pass A (Backend):      ${RED}✗ FAILED${NC}"
        OVERALL_STATUS=1
    fi
fi

if [ "$PASS" = "all" ] || [ "$PASS" = "B" ]; then
    if [ $PASS_B_STATUS -eq 0 ]; then
        echo -e "  Pass B (Integration):  ${GREEN}✓ PASSED${NC}"
    else
        echo -e "  Pass B (Integration):  ${RED}✗ FAILED${NC}"
        OVERALL_STATUS=1
    fi
fi

if [ "$PASS" = "all" ] || [ "$PASS" = "C" ]; then
    if [ $PASS_C_STATUS -eq 0 ]; then
        echo -e "  Pass C (E2E):          ${GREEN}✓ PASSED${NC}"
    else
        echo -e "  Pass C (E2E):          ${RED}✗ FAILED${NC}"
        OVERALL_STATUS=1
    fi
fi

echo ""

# Coverage report
if [ "$COVERAGE" = true ] && [ -f "${OUTPUT_DIR}/coverage/coverage.xml" ]; then
    echo "Coverage Report:"

    # Extract coverage percentage from XML
    if command -v python3 &> /dev/null; then
        COVERAGE_PCT=$(python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('${OUTPUT_DIR}/coverage/coverage.xml')
root = tree.getroot()
line_rate = float(root.attrib.get('line-rate', 0))
print(f'{line_rate * 100:.1f}')
" 2>/dev/null || echo "unknown")

        echo "  Total Coverage: ${COVERAGE_PCT}%"

        # Check if coverage meets target
        if command -v bc &> /dev/null; then
            if (( $(echo "$COVERAGE_PCT >= 70.0" | bc -l) )); then
                echo -e "  Target (70%):   ${GREEN}✓ MET${NC}"
            else
                echo -e "  Target (70%):   ${RED}✗ NOT MET${NC}"
                OVERALL_STATUS=1
            fi
        fi
    fi

    echo ""
    echo "  HTML Report: ${OUTPUT_DIR}/coverage/html/index.html"
    echo "  XML Report:  ${OUTPUT_DIR}/coverage/coverage.xml"
    echo ""
fi

# Artifacts
echo "Test Artifacts:"
echo "  Output Directory: ${OUTPUT_DIR}/"

if [ "$PASS" = "all" ] || [ "$PASS" = "A" ]; then
    echo "  - backend/junit.xml"
    echo "  - backend/report.html"
    echo "  - backend/output.log"
fi

if [ "$PASS" = "all" ] || [ "$PASS" = "B" ]; then
    echo "  - integration/junit.xml"
    echo "  - integration/report.html"
    echo "  - integration/output.log"
fi

if [ "$PASS" = "all" ] || [ "$PASS" = "C" ]; then
    echo "  - e2e/junit.xml"
    echo "  - e2e/report.html"
    echo "  - e2e/output.log"
fi

if [ "$COVERAGE" = true ]; then
    echo "  - coverage/coverage.xml"
    echo "  - coverage/html/"
fi

echo ""
echo "============================================================================"

# Exit with overall status
if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Next Steps:"
    echo "  1. Review coverage report: open ${OUTPUT_DIR}/coverage/html/index.html"
    echo "  2. Proceed to Phase 4: ./scripts/generate_proofs.sh"
    echo ""
else
    echo -e "${RED}❌ Some tests failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Review test logs in ${OUTPUT_DIR}/"
    echo "  2. Check Docker services: docker compose ps"
    echo "  3. View service logs: docker compose logs [service]"
    echo ""
fi

exit $OVERALL_STATUS
