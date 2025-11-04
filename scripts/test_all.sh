#!/bin/bash
# Run all tests from repository root

set -e

echo "🧪 Running all tests for Real Estate OS..."
echo "================================================"

TOTAL_TESTS=0
TOTAL_PASSED=0
START_TIME=$(date +%s)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to run tests for a package
run_tests() {
    local package_name=$1
    local package_path=$2

    echo ""
    echo "📦 Testing: $package_name"
    echo "   Path: $package_path"

    cd "$package_path"

    if poetry run pytest -v --tb=short 2>&1 | tee /tmp/test_output.txt; then
        tests_run=$(grep -c "PASSED" /tmp/test_output.txt || echo "0")
        TOTAL_PASSED=$((TOTAL_PASSED + tests_run))
        TOTAL_TESTS=$((TOTAL_TESTS + tests_run))
        echo -e "${GREEN}✅ $package_name: $tests_run tests passed${NC}"
    else
        echo -e "${RED}❌ $package_name: Tests failed${NC}"
        exit 1
    fi

    cd - > /dev/null
}

# Navigate to repo root
REPO_ROOT="/home/user/real-estate-os"
cd "$REPO_ROOT"

# Run tests for each package
run_tests "Contracts" "$REPO_ROOT/packages/contracts"
run_tests "Policy Kernel" "$REPO_ROOT/services/policy-kernel"
run_tests "Discovery Resolver" "$REPO_ROOT/agents/discovery/resolver"
run_tests "Enrichment Hub" "$REPO_ROOT/agents/enrichment/hub"
run_tests "Score Engine" "$REPO_ROOT/agents/scoring/engine"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "================================================"
echo -e "${GREEN}✅ All tests passed!${NC}"
echo "   Total tests: $TOTAL_TESTS"
echo "   Duration: ${DURATION}s"
echo "================================================"

# Generate coverage summary
echo ""
echo "📊 Generating combined coverage report..."
# This would combine coverage from all packages (requires coverage configuration)
echo "   (Coverage reports available in each package's htmlcov/ directory)"
