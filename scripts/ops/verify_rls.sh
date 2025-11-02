#!/bin/bash
set -e

# RLS (Row-Level Security) Verification Script
# Tests cross-tenant isolation at database level

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/isolation"

echo "===================================="
echo "RLS Cross-Tenant Isolation Test"
echo "===================================="
echo ""

# Ensure artifacts directory exists
mkdir -p "$ARTIFACTS_DIR"

# Load environment
if [ -f "$PROJECT_ROOT/.env.staging" ]; then
  source "$PROJECT_ROOT/.env.staging"
fi

# Database connection
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-realestate}"
DB_USER="${POSTGRES_USER:-postgres}"

export PGPASSWORD="$POSTGRES_PASSWORD"

OUTPUT_FILE="$ARTIFACTS_DIR/negative-tests-db.txt"

echo "Running RLS isolation tests..." | tee "$OUTPUT_FILE"
echo "Time: $(date)" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Test UUIDs for two tenants
TENANT_A="11111111-1111-1111-1111-111111111111"
TENANT_B="22222222-2222-2222-2222-222222222222"

echo "Test Tenants:" | tee -a "$OUTPUT_FILE"
echo "  Tenant A: $TENANT_A" | tee -a "$OUTPUT_FILE"
echo "  Tenant B: $TENANT_B" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Create test tenants if they don't exist
echo "Creating test tenants..." | tee -a "$OUTPUT_FILE"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF >> "$OUTPUT_FILE" 2>&1
INSERT INTO tenants (id, name, created_at, updated_at)
VALUES
  ('$TENANT_A', 'Test Tenant A', NOW(), NOW()),
  ('$TENANT_B', 'Test Tenant B', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;
EOF

# Insert test properties for each tenant
echo "Inserting test properties..." | tee -a "$OUTPUT_FILE"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF >> "$OUTPUT_FILE" 2>&1
-- Tenant A properties
INSERT INTO properties (id, tenant_id, address, city, state, zip_code, property_type, list_price, created_at, updated_at)
VALUES
  (gen_random_uuid(), '$TENANT_A', '100 Tenant A St', 'City A', 'CA', '90001', 'Residential', 500000, NOW(), NOW()),
  (gen_random_uuid(), '$TENANT_A', '200 Tenant A St', 'City A', 'CA', '90001', 'Residential', 600000, NOW(), NOW()),
  (gen_random_uuid(), '$TENANT_A', '300 Tenant A St', 'City A', 'CA', '90001', 'Residential', 700000, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Tenant B properties
INSERT INTO properties (id, tenant_id, address, city, state, zip_code, property_type, list_price, created_at, updated_at)
VALUES
  (gen_random_uuid(), '$TENANT_B', '100 Tenant B St', 'City B', 'CA', '90002', 'Commercial', 1000000, NOW(), NOW()),
  (gen_random_uuid(), '$TENANT_B', '200 Tenant B St', 'City B', 'CA', '90002', 'Commercial', 1100000, NOW(), NOW()),
  (gen_random_uuid(), '$TENANT_B', '300 Tenant B St', 'City B', 'CA', '90002', 'Commercial', 1200000, NOW(), NOW())
ON CONFLICT DO NOTHING;
EOF

echo "✓ Test data inserted" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Test 1: Tenant A should see only their properties
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 1: Tenant A can see their properties" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Query: SET app.tenant_id='$TENANT_A'; SELECT COUNT(*) FROM properties;" | tee -a "$OUTPUT_FILE"
RESULT_A=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SET LOCAL app.tenant_id='$TENANT_A';
SELECT COUNT(*) FROM properties;
")

echo "Result: $RESULT_A properties" | tee -a "$OUTPUT_FILE"

if [ "$RESULT_A" -ge 3 ]; then
  echo "✓ PASS: Tenant A can see their properties" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: Expected ≥3 properties, got $RESULT_A" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# Test 2: Tenant B should see only their properties
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 2: Tenant B can see their properties" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Query: SET app.tenant_id='$TENANT_B'; SELECT COUNT(*) FROM properties;" | tee -a "$OUTPUT_FILE"
RESULT_B=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SET LOCAL app.tenant_id='$TENANT_B';
SELECT COUNT(*) FROM properties;
")

echo "Result: $RESULT_B properties" | tee -a "$OUTPUT_FILE"

if [ "$RESULT_B" -ge 3 ]; then
  echo "✓ PASS: Tenant B can see their properties" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: Expected ≥3 properties, got $RESULT_B" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# Test 3: Tenant A should NOT see Tenant B's properties
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 3: Tenant A CANNOT see Tenant B properties" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Query: SET app.tenant_id='$TENANT_A'; SELECT COUNT(*) FROM properties WHERE tenant_id='$TENANT_B';" | tee -a "$OUTPUT_FILE"
CROSS_TENANT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SET LOCAL app.tenant_id='$TENANT_A';
SELECT COUNT(*) FROM properties WHERE tenant_id='$TENANT_B';
")

echo "Result: $CROSS_TENANT properties" | tee -a "$OUTPUT_FILE"

if [ "$CROSS_TENANT" -eq 0 ]; then
  echo "✓ PASS: RLS blocks cross-tenant read" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: RLS FAILED - Tenant A can see $CROSS_TENANT of Tenant B's properties" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# Test 4: Tenant A should NOT be able to UPDATE Tenant B's properties
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 4: Tenant A CANNOT update Tenant B properties" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Query: SET app.tenant_id='$TENANT_A'; UPDATE properties SET list_price=999999 WHERE tenant_id='$TENANT_B';" | tee -a "$OUTPUT_FILE"
UPDATE_RESULT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SET LOCAL app.tenant_id='$TENANT_A';
UPDATE properties SET list_price=999999 WHERE tenant_id='$TENANT_B';
" 2>&1 | grep "UPDATE" | awk '{print $2}')

echo "Rows affected: ${UPDATE_RESULT:-0}" | tee -a "$OUTPUT_FILE"

if [ "${UPDATE_RESULT:-0}" -eq 0 ]; then
  echo "✓ PASS: RLS blocks cross-tenant update" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: RLS FAILED - Tenant A updated $UPDATE_RESULT of Tenant B's properties" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# Test 5: Tenant A should NOT be able to DELETE Tenant B's properties
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 5: Tenant A CANNOT delete Tenant B properties" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Query: SET app.tenant_id='$TENANT_A'; DELETE FROM properties WHERE tenant_id='$TENANT_B';" | tee -a "$OUTPUT_FILE"
DELETE_RESULT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SET LOCAL app.tenant_id='$TENANT_A';
DELETE FROM properties WHERE tenant_id='$TENANT_B';
" 2>&1 | grep "DELETE" | awk '{print $2}')

echo "Rows affected: ${DELETE_RESULT:-0}" | tee -a "$OUTPUT_FILE"

if [ "${DELETE_RESULT:-0}" -eq 0 ]; then
  echo "✓ PASS: RLS blocks cross-tenant delete" | tee -a "$OUTPUT_FILE"
else
  echo "✗ FAIL: RLS FAILED - Tenant A deleted $DELETE_RESULT of Tenant B's properties" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# Summary
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "RLS Verification Complete" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Artifact generated: $OUTPUT_FILE"
echo ""
echo "Next: Verify isolation at API level with scripts/ops/verify_api_isolation.sh"
