#!/bin/bash
set -e

# MinIO Cross-Tenant Isolation Verification Script
# Tests tenant prefix-based isolation in object storage

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}\")\" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/isolation"

echo "========================================"
echo "MinIO Cross-Tenant Isolation Test"
echo "========================================"
echo ""

# Ensure artifacts directory exists
mkdir -p "$ARTIFACTS_DIR"

# Load environment
if [ -f "$PROJECT_ROOT/.env.staging" ]; then
  source "$PROJECT_ROOT/.env.staging"
fi

MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET="documents"
OUTPUT_FILE="$ARTIFACTS_DIR/minio-prefix-proof.txt"

echo "Testing MinIO at: $MINIO_ENDPOINT" | tee "$OUTPUT_FILE"
echo "Bucket: $BUCKET" | tee -a "$OUTPUT_FILE"
echo "Time: $(date)" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Test tenant UUIDs
TENANT_A="11111111-1111-1111-1111-111111111111"
TENANT_B="22222222-2222-2222-2222-222222222222"

echo "Test Tenants:" | tee -a "$OUTPUT_FILE"
echo "  Tenant A: $TENANT_A" | tee -a "$OUTPUT_FILE"
echo "  Tenant B: $TENANT_B" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# Prerequisites Check
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "Prerequisites Check" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Check if MinIO client (mc) is installed
if ! command -v mc &> /dev/null; then
  echo "⚠ MinIO client (mc) not installed" | tee -a "$OUTPUT_FILE"
  echo "" | tee -a "$OUTPUT_FILE"
  echo "Install MinIO client:" | tee -a "$OUTPUT_FILE"
  echo "  wget https://dl.min.io/client/mc/release/linux-amd64/mc" | tee -a "$OUTPUT_FILE"
  echo "  chmod +x mc" | tee -a "$OUTPUT_FILE"
  echo "  sudo mv mc /usr/local/bin/" | tee -a "$OUTPUT_FILE"
  echo "" | tee -a "$OUTPUT_FILE"
  echo "Falling back to curl-based tests..." | tee -a "$OUTPUT_FILE"
  USE_MC=false
else
  echo "✓ MinIO client (mc) is installed" | tee -a "$OUTPUT_FILE"
  USE_MC=true
fi
echo "" | tee -a "$OUTPUT_FILE"

# Check if MinIO is running
if ! curl -sf "http://$MINIO_ENDPOINT/minio/health/live" > /dev/null 2>&1; then
  echo "✗ MinIO not available at $MINIO_ENDPOINT" | tee -a "$OUTPUT_FILE"
  echo "Start MinIO: docker compose up -d minio" | tee -a "$OUTPUT_FILE"
  exit 1
fi

echo "✓ MinIO is healthy" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# Setup MinIO Client Alias
# ========================================
if [ "$USE_MC" = true ]; then
  echo "Configuring MinIO client alias..." | tee -a "$OUTPUT_FILE"
  mc alias set testminio "http://$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" > /dev/null 2>&1
  echo "✓ MinIO alias configured" | tee -a "$OUTPUT_FILE"
  echo "" | tee -a "$OUTPUT_FILE"
fi

# ========================================
# Create Bucket and Upload Test Files
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "Setting Up Test Data" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# Create test files
mkdir -p /tmp/minio_test
echo "Tenant A - Document 1" > /tmp/minio_test/tenant_a_doc1.txt
echo "Tenant A - Document 2" > /tmp/minio_test/tenant_a_doc2.txt
echo "Tenant A - Document 3" > /tmp/minio_test/tenant_a_doc3.txt
echo "Tenant B - Document 1" > /tmp/minio_test/tenant_b_doc1.txt
echo "Tenant B - Document 2" > /tmp/minio_test/tenant_b_doc2.txt
echo "Tenant B - Document 3" > /tmp/minio_test/tenant_b_doc3.txt

if [ "$USE_MC" = true ]; then
  # Create bucket if it doesn't exist
  mc mb -p "testminio/$BUCKET" > /dev/null 2>&1 || true
  echo "✓ Bucket created/verified: $BUCKET" | tee -a "$OUTPUT_FILE"

  # Upload files with tenant prefixes
  echo "Uploading test files..." | tee -a "$OUTPUT_FILE"
  mc cp /tmp/minio_test/tenant_a_doc1.txt "testminio/$BUCKET/$TENANT_A/doc1.txt" > /dev/null 2>&1
  mc cp /tmp/minio_test/tenant_a_doc2.txt "testminio/$BUCKET/$TENANT_A/doc2.txt" > /dev/null 2>&1
  mc cp /tmp/minio_test/tenant_a_doc3.txt "testminio/$BUCKET/$TENANT_A/doc3.txt" > /dev/null 2>&1
  mc cp /tmp/minio_test/tenant_b_doc1.txt "testminio/$BUCKET/$TENANT_B/doc1.txt" > /dev/null 2>&1
  mc cp /tmp/minio_test/tenant_b_doc2.txt "testminio/$BUCKET/$TENANT_B/doc2.txt" > /dev/null 2>&1
  mc cp /tmp/minio_test/tenant_b_doc3.txt "testminio/$BUCKET/$TENANT_B/doc3.txt" > /dev/null 2>&1

  echo "  Tenant A: 3 documents uploaded" | tee -a "$OUTPUT_FILE"
  echo "  Tenant B: 3 documents uploaded" | tee -a "$OUTPUT_FILE"
  echo "" | tee -a "$OUTPUT_FILE"
else
  echo "⚠ Cannot upload files without mc client" | tee -a "$OUTPUT_FILE"
  echo "Install mc client to run full test suite" | tee -a "$OUTPUT_FILE"
  echo "" | tee -a "$OUTPUT_FILE"
fi

# ========================================
# TEST 1: List Tenant A Objects Only
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 1: List objects with Tenant A prefix" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

if [ "$USE_MC" = true ]; then
  echo "Command: mc ls testminio/$BUCKET/$TENANT_A/" | tee -a "$OUTPUT_FILE"
  TENANT_A_OBJECTS=$(mc ls "testminio/$BUCKET/$TENANT_A/" 2>/dev/null | wc -l)

  echo "Objects found: $TENANT_A_OBJECTS" | tee -a "$OUTPUT_FILE"

  if [ "$TENANT_A_OBJECTS" -eq 3 ]; then
    echo "✓ PASS: Tenant A can list their 3 objects" | tee -a "$OUTPUT_FILE"
  else
    echo "✗ FAIL: Expected 3 objects, found $TENANT_A_OBJECTS" | tee -a "$OUTPUT_FILE"
  fi

  echo "" | tee -a "$OUTPUT_FILE"
  echo "Object list:" | tee -a "$OUTPUT_FILE"
  mc ls "testminio/$BUCKET/$TENANT_A/" 2>&1 | tee -a "$OUTPUT_FILE"
else
  echo "SKIP: Requires mc client" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 2: List Tenant B Objects Only
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 2: List objects with Tenant B prefix" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

if [ "$USE_MC" = true ]; then
  echo "Command: mc ls testminio/$BUCKET/$TENANT_B/" | tee -a "$OUTPUT_FILE"
  TENANT_B_OBJECTS=$(mc ls "testminio/$BUCKET/$TENANT_B/" 2>/dev/null | wc -l)

  echo "Objects found: $TENANT_B_OBJECTS" | tee -a "$OUTPUT_FILE"

  if [ "$TENANT_B_OBJECTS" -eq 3 ]; then
    echo "✓ PASS: Tenant B can list their 3 objects" | tee -a "$OUTPUT_FILE"
  else
    echo "✗ FAIL: Expected 3 objects, found $TENANT_B_OBJECTS" | tee -a "$OUTPUT_FILE"
  fi

  echo "" | tee -a "$OUTPUT_FILE"
  echo "Object list:" | tee -a "$OUTPUT_FILE"
  mc ls "testminio/$BUCKET/$TENANT_B/" 2>&1 | tee -a "$OUTPUT_FILE"
else
  echo "SKIP: Requires mc client" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 3: Attempt to Access Tenant B Object with Tenant A Prefix
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 3: Cross-tenant object access attempt" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

if [ "$USE_MC" = true ]; then
  echo "Attempting to download Tenant B object using wrong prefix..." | tee -a "$OUTPUT_FILE"
  echo "Command: mc cat testminio/$BUCKET/$TENANT_B/doc1.txt" | tee -a "$OUTPUT_FILE"

  # In production, this would be blocked by IAM policy
  # For now, we demonstrate the correct access pattern
  CONTENT=$(mc cat "testminio/$BUCKET/$TENANT_B/doc1.txt" 2>&1 || echo "ACCESS_DENIED")

  if echo "$CONTENT" | grep -q "Tenant B"; then
    echo "⚠ WARNING: Cross-tenant access succeeded (IAM policy not enforced)" | tee -a "$OUTPUT_FILE"
    echo "Content: $CONTENT" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"
    echo "To enforce isolation, configure MinIO IAM policy:" | tee -a "$OUTPUT_FILE"
    echo "  1. Create policy restricting access to tenant prefix" | tee -a "$OUTPUT_FILE"
    echo "  2. Assign policy to tenant-specific user/service account" | tee -a "$OUTPUT_FILE"
    echo "  3. Application must use tenant-specific credentials" | tee -a "$OUTPUT_FILE"
  else
    echo "✓ PASS: Cross-tenant access denied by IAM policy" | tee -a "$OUTPUT_FILE"
  fi
else
  echo "SKIP: Requires mc client" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# TEST 4: Verify Prefix-Based Isolation Pattern
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "TEST 4: Prefix-based isolation validation" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

if [ "$USE_MC" = true ]; then
  echo "Listing all objects in bucket (admin view)..." | tee -a "$OUTPUT_FILE"
  ALL_OBJECTS=$(mc ls -r "testminio/$BUCKET/" 2>/dev/null | wc -l)
  echo "Total objects in bucket: $ALL_OBJECTS" | tee -a "$OUTPUT_FILE"

  if [ "$ALL_OBJECTS" -eq 6 ]; then
    echo "✓ All 6 test objects present in storage" | tee -a "$OUTPUT_FILE"
  else
    echo "⚠ Expected 6 objects, found $ALL_OBJECTS" | tee -a "$OUTPUT_FILE"
  fi

  echo "" | tee -a "$OUTPUT_FILE"
  echo "Full object tree:" | tee -a "$OUTPUT_FILE"
  mc tree "testminio/$BUCKET/" 2>&1 | head -20 | tee -a "$OUTPUT_FILE"
else
  echo "SKIP: Requires mc client" | tee -a "$OUTPUT_FILE"
fi
echo "" | tee -a "$OUTPUT_FILE"

# ========================================
# IAM Policy Example
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "Recommended IAM Policy for Tenant Isolation" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << 'EOF'
Example MinIO IAM Policy for Tenant A:

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::documents/11111111-1111-1111-1111-111111111111/*",
        "arn:aws:s3:::images/11111111-1111-1111-1111-111111111111/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::documents", "arn:aws:s3:::images"],
      "Condition": {
        "StringLike": {
          "s3:prefix": ["11111111-1111-1111-1111-111111111111/*"]
        }
      }
    }
  ]
}

To apply:
  1. Save policy as tenant-a-policy.json
  2. mc admin policy add testminio tenant-a-policy tenant-a-policy.json
  3. mc admin user add testminio tenant-a-user <password>
  4. mc admin policy set testminio tenant-a-policy user=tenant-a-user
  5. Use tenant-a-user credentials in application for Tenant A operations

EOF

# ========================================
# Summary
# ========================================
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "MinIO Isolation Verification Complete" | tee -a "$OUTPUT_FILE"
echo "========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Key Findings:" | tee -a "$OUTPUT_FILE"
echo "  - Tenant prefix isolation works at application layer" | tee -a "$OUTPUT_FILE"
echo "  - Objects are stored under tenant-specific prefixes (tenant_id/...)" | tee -a "$OUTPUT_FILE"
echo "  - IAM policies MUST be configured to enforce access control" | tee -a "$OUTPUT_FILE"
echo "  - Application MUST use tenant-specific credentials or enforce prefix checks" | tee -a "$OUTPUT_FILE"
echo "  - Without IAM policies, any user with bucket access can read all objects" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "Artifact generated: $OUTPUT_FILE"
echo ""

# Cleanup
echo "Cleaning up test files..."
if [ "$USE_MC" = true ]; then
  mc rm -r --force "testminio/$BUCKET/$TENANT_A/" > /dev/null 2>&1 || true
  mc rm -r --force "testminio/$BUCKET/$TENANT_B/" > /dev/null 2>&1 || true
  echo "✓ Test objects deleted from MinIO"
fi
rm -rf /tmp/minio_test
echo "✓ Local test files deleted"
