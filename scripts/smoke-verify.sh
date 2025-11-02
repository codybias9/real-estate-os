#!/bin/bash
set -e

# Smoke Verification Script
# Tests the six critical paths and generates verification artifacts

ARTIFACTS_DIR="artifacts/verification"
mkdir -p "$ARTIFACTS_DIR"

echo "=== Real Estate OS Smoke Verification ==="
echo "Starting at $(date)"

FAILURES=0
SUCCESSES=0

# Helper function to log test results
log_result() {
    local test_name="$1"
    local status="$2"
    local output_file="$3"

    if [ "$status" == "PASS" ]; then
        echo "✅ $test_name: PASS"
        ((SUCCESSES++))
    else
        echo "❌ $test_name: FAIL"
        ((FAILURES++))
    fi

    echo "$test_name: $status" >> "$ARTIFACTS_DIR/smoke-summary.txt"
}

# Test 1: Feast online features in scoring hot path with trace
echo ""
echo "Test 1: Feast online features for scoring..."
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from ml.feast_integration import test_feast_online_fetch
    result = test_feast_online_fetch('DEMO123')
    import json
    with open('$ARTIFACTS_DIR/feast-online-trace-DEMO123.json', 'w') as f:
        json.dump(result, f, indent=2)
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}')
    sys.exit(1)
" 2>&1 | tee "$ARTIFACTS_DIR/test1-feast.log"; then
    log_result "Feast Online Features" "PASS" "$ARTIFACTS_DIR/test1-feast.log"
else
    log_result "Feast Online Features" "FAIL" "$ARTIFACTS_DIR/test1-feast.log"
fi

# Test 2: Comp-Critic ranked comps + adjustments waterfall
echo ""
echo "Test 2: Comp-Critic valuation..."
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from ml.models.comp_critic import test_comp_critic
    result = test_comp_critic('DEMO123')
    import json
    with open('$ARTIFACTS_DIR/comps-waterfall-DEMO123.json', 'w') as f:
        json.dump(result, f, indent=2)
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}')
    sys.exit(1)
" 2>&1 | tee "$ARTIFACTS_DIR/test2-comps.log"; then
    log_result "Comp-Critic Valuation" "PASS" "$ARTIFACTS_DIR/test2-comps.log"
else
    log_result "Comp-Critic Valuation" "FAIL" "$ARTIFACTS_DIR/test2-comps.log"
fi

# Test 3: Offer solver feasible/infeasible/timeout with logs + frontier CSV
echo ""
echo "Test 3: Offer optimization solver..."
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from ml.models.offer_optimizer import test_offer_solver
    result = test_offer_solver()
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}')
    sys.exit(1)
" 2>&1 | tee "$ARTIFACTS_DIR/test3-offers.log"; then
    log_result "Offer Optimization" "PASS" "$ARTIFACTS_DIR/test3-offers.log"
else
    log_result "Offer Optimization" "FAIL" "$ARTIFACTS_DIR/test3-offers.log"
fi

# Test 4: Regime detect + policy output with confidence
echo ""
echo "Test 4: Regime monitoring..."
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from ml.models.regime_monitor import test_regime_detection
    result = test_regime_detection('CLARK-NV')
    import json
    with open('$ARTIFACTS_DIR/regime-policy-CLARK-NV.json', 'w') as f:
        json.dump(result, f, indent=2)
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}')
    sys.exit(1)
" 2>&1 | tee "$ARTIFACTS_DIR/test4-regime.log"; then
    log_result "Regime Monitoring" "PASS" "$ARTIFACTS_DIR/test4-regime.log"
else
    log_result "Regime Monitoring" "FAIL" "$ARTIFACTS_DIR/test4-regime.log"
fi

# Test 5: Negotiation quiet-hours block & DNC suppression
echo ""
echo "Test 5: Negotiation compliance..."
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from ml.models.negotiation_brain import test_compliance
    result = test_compliance()
    import json
    with open('$ARTIFACTS_DIR/negotiation-compliance.json', 'w') as f:
        json.dump(result, f, indent=2)
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}')
    sys.exit(1)
" 2>&1 | tee "$ARTIFACTS_DIR/test5-negotiation.log"; then
    log_result "Negotiation Compliance" "PASS" "$ARTIFACTS_DIR/test5-negotiation.log"
else
    log_result "Negotiation Compliance" "FAIL" "$ARTIFACTS_DIR/test5-negotiation.log"
fi

# Test 6: DCF golden case outputs
echo ""
echo "Test 6: DCF Engine..."
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from ml.models.dcf_engine import test_dcf_golden_cases
    result = test_dcf_golden_cases()
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}')
    sys.exit(1)
" 2>&1 | tee "$ARTIFACTS_DIR/test6-dcf.log"; then
    log_result "DCF Engine" "PASS" "$ARTIFACTS_DIR/test6-dcf.log"
else
    log_result "DCF Engine" "FAIL" "$ARTIFACTS_DIR/test6-dcf.log"
fi

# Generate summary JSON
cat > "$ARTIFACTS_DIR/smoke-results.json" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "total_tests": $((SUCCESSES + FAILURES)),
  "successes": $SUCCESSES,
  "failures": $FAILURES,
  "status": "$( [ $FAILURES -eq 0 ] && echo 'PASS' || echo 'FAIL' )"
}
EOF

echo ""
echo "=== Smoke Verification Complete ==="
echo "Successes: $SUCCESSES"
echo "Failures: $FAILURES"
echo "Artifacts saved to: $ARTIFACTS_DIR"

if [ $FAILURES -gt 0 ]; then
    exit 1
fi

exit 0
