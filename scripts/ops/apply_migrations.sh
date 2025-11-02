#!/bin/bash
set -e

# Apply Database Migrations
# This script applies all migrations in order and generates artifacts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts/db"

echo "===================================="
echo "Applying Database Migrations"
echo "===================================="
echo ""

# Ensure artifacts directory exists
mkdir -p "$ARTIFACTS_DIR"

# Load environment
if [ -f "$PROJECT_ROOT/.env.staging" ]; then
  source "$PROJECT_ROOT/.env.staging"
else
  echo "ERROR: .env.staging not found"
  echo "Copy .env.staging.example to .env.staging and configure"
  exit 1
fi

# Database connection
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-realestate}"
DB_USER="${POSTGRES_USER:-postgres}"

export PGPASSWORD="$POSTGRES_PASSWORD"

echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo ""

# Check connection
echo "Testing database connection..."
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
  echo "ERROR: Cannot connect to database"
  echo "Make sure PostgreSQL is running:"
  echo "  docker compose --env-file .env.staging -f docker-compose.staging.yml up -d postgres"
  exit 1
fi
echo "✓ Connection successful"
echo ""

# Apply migrations in order
MIGRATIONS_DIR="$PROJECT_ROOT/db/migrations"
LOG_FILE="$ARTIFACTS_DIR/apply-log.txt"

echo "Applying migrations..." | tee "$LOG_FILE"
echo "Time: $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

for migration in "$MIGRATIONS_DIR"/*.sql; do
  if [ -f "$migration" ]; then
    migration_name=$(basename "$migration")
    echo "Applying $migration_name..." | tee -a "$LOG_FILE"

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration" >> "$LOG_FILE" 2>&1; then
      echo "  ✓ Success" | tee -a "$LOG_FILE"
    else
      echo "  ✗ Failed" | tee -a "$LOG_FILE"
      echo "Check $LOG_FILE for details"
      exit 1
    fi
  fi
done

echo "" | tee -a "$LOG_FILE"
echo "All migrations applied successfully" | tee -a "$LOG_FILE"

# Generate RLS policies artifact
echo ""
echo "Generating RLS policies artifact..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
" > "$ARTIFACTS_DIR/rls-policies.txt"

echo "✓ Saved to $ARTIFACTS_DIR/rls-policies.txt"

# List tables
echo ""
echo "Database tables:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt" | tee -a "$LOG_FILE"

# Count tables with RLS
echo ""
echo "Tables with RLS enabled:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT
  schemaname,
  tablename,
  rowsecurity
FROM pg_tables
WHERE schemaname = 'public' AND rowsecurity = true
ORDER BY tablename;
" | tee -a "$LOG_FILE"

echo ""
echo "===================================="
echo "Migration complete"
echo "===================================="
echo ""
echo "Artifacts generated:"
echo "  - $ARTIFACTS_DIR/apply-log.txt"
echo "  - $ARTIFACTS_DIR/rls-policies.txt"
echo ""
echo "Next steps:"
echo "  1. Verify RLS: bash scripts/ops/verify_rls.sh"
echo "  2. Start API: docker compose --env-file .env.staging -f docker-compose.staging.yml up -d api"
echo "  3. Health check: bash scripts/ops/health_check.sh"
