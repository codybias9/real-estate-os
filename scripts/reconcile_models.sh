#!/usr/bin/env bash
#
# Model Reconciliation Script
# Cross-checks SQLAlchemy models vs Alembic migrations vs Pydantic schemas
#
# Resolves: "20 models vs 35 models vs 26 models" confusion
#
set -euo pipefail

OUT="audit_artifacts/model_reconciliation_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${OUT}"

echo "=========================================="
echo "Model Reconciliation Analysis"
echo "=========================================="
echo ""

# ============================================================================
# 1. SQLAlchemy Base Subclasses (AUTHORITATIVE - these are DB tables)
# ============================================================================

echo "[1/5] Finding SQLAlchemy Base subclasses..."

# Find all classes that inherit from Base (declarative_base)
find . -type f -name "*.py" \
  -not -path "*/.git/*" \
  -not -path "*/node_modules/*" \
  -not -path "*/__pycache__/*" \
  -not -path "*/venv/*" \
  -not -path "*/.venv/*" \
  2>/dev/null | \
  xargs grep -hE "^class\s+[A-Z][A-Za-z0-9_]*\(.*Base" 2>/dev/null | \
  sed -E 's/^class\s+([A-Za-z0-9_]+)\(.*/\1/' | \
  grep -v "^Base$" | \
  sort -u > "${OUT}/1_sqlalchemy_models.txt" || touch "${OUT}/1_sqlalchemy_models.txt"

SQLALCHEMY_COUNT=$(wc -l < "${OUT}/1_sqlalchemy_models.txt")
echo "   Found: ${SQLALCHEMY_COUNT} SQLAlchemy models"

# ============================================================================
# 2. Alembic Migration Tables (What's been migrated)
# ============================================================================

echo "[2/5] Extracting tables from Alembic migrations..."

# Find all create_table and drop_table calls in migration files
find . -path "*/versions/*.py" -not -name "__*" 2>/dev/null | \
  xargs grep -hE "(create_table|drop_table|Table)\(" 2>/dev/null | \
  grep -oE '["'\'']([\w_]+)["'\'']' | \
  tr -d '"' | tr -d "'" | \
  grep -v "^op$\|^sa$\|^Column$\|^Integer$\|^String$" | \
  sort -u > "${OUT}/2_migration_tables.txt" || touch "${OUT}/2_migration_tables.txt"

MIGRATION_COUNT=$(wc -l < "${OUT}/2_migration_tables.txt")
echo "   Found: ${MIGRATION_COUNT} tables in migrations"

# Count migration files
find . -path "*/versions/*.py" -not -name "__*" 2>/dev/null | \
  wc -l > "${OUT}/2_migration_file_count.txt"
MIGRATION_FILES=$(cat "${OUT}/2_migration_file_count.txt")
echo "   (From ${MIGRATION_FILES} migration files)"

# ============================================================================
# 3. Pydantic Schemas (API contracts, not DB models)
# ============================================================================

echo "[3/5] Finding Pydantic schemas..."

# Find all Pydantic models (inherit from BaseModel)
find api -type f -name "*.py" 2>/dev/null | \
  xargs grep -hE "^class\s+[A-Z][A-Za-z0-9_]*\(.*BaseModel" 2>/dev/null | \
  sed -E 's/^class\s+([A-Za-z0-9_]+)\(.*/\1/' | \
  sort -u > "${OUT}/3_pydantic_schemas.txt" || touch "${OUT}/3_pydantic_schemas.txt"

PYDANTIC_COUNT=$(wc -l < "${OUT}/3_pydantic_schemas.txt")
echo "   Found: ${PYDANTIC_COUNT} Pydantic schemas"

# ============================================================================
# 4. Table Names from __tablename__ Declarations
# ============================================================================

echo "[4/5] Extracting __tablename__ declarations..."

find . -type f -name "*.py" \
  -not -path "*/.git/*" \
  -not -path "*/node_modules/*" \
  2>/dev/null | \
  xargs grep -hE '^\s*__tablename__\s*=\s*["\047]' 2>/dev/null | \
  sed -E 's/.*__tablename__\s*=\s*["'\'']([\w_]+)["'\''].*/\1/' | \
  sort -u > "${OUT}/4_tablename_declarations.txt" || touch "${OUT}/4_tablename_declarations.txt"

TABLENAME_COUNT=$(wc -l < "${OUT}/4_tablename_declarations.txt")
echo "   Found: ${TABLENAME_COUNT} __tablename__ declarations"

# ============================================================================
# 5. Model File Locations
# ============================================================================

echo "[5/5] Locating model files..."

# Find all files that define models
find . -type f -name "*.py" \
  -not -path "*/.git/*" \
  -not -path "*/node_modules/*" \
  2>/dev/null | \
  xargs grep -l "class.*Base\|__tablename__" 2>/dev/null | \
  sort > "${OUT}/5_model_files.txt" || touch "${OUT}/5_model_files.txt"

MODEL_FILES=$(wc -l < "${OUT}/5_model_files.txt")
echo "   Found: ${MODEL_FILES} files containing models"

# ============================================================================
# RECONCILIATION ANALYSIS
# ============================================================================

echo ""
echo "=========================================="
echo "RECONCILIATION ANALYSIS"
echo "=========================================="
echo ""

cat > "${OUT}/RECONCILIATION_REPORT.txt" <<EOF
Model Reconciliation Report
Generated: $(date -u)
================================================================================

COUNTS SUMMARY
--------------------------------------------------------------------------------
SQLAlchemy Base subclasses:        ${SQLALCHEMY_COUNT}  ← AUTHORITATIVE (DB models)
Tables in Alembic migrations:      ${MIGRATION_COUNT}
Pydantic schemas (API contracts):  ${PYDANTIC_COUNT}
__tablename__ declarations:        ${TABLENAME_COUNT}
Files containing models:           ${MODEL_FILES}
Alembic migration files:           ${MIGRATION_FILES}

================================================================================
INTERPRETATION
================================================================================

The confusion "20 vs 35 vs 26 models" likely comes from counting different things:

1. SQLAlchemy Base subclasses (${SQLALCHEMY_COUNT}) = Database tables/models
   → This is the AUTHORITATIVE count for "how many models exist"
   → These are persisted to the database via Alembic migrations

2. Pydantic schemas (${PYDANTIC_COUNT}) = API request/response contracts
   → Often 2-5x more than DB models (Create/Update/Response per model)
   → Example: User model → UserCreate, UserUpdate, UserResponse schemas
   → NOT database models, just validation schemas

3. Tables in migrations (${MIGRATION_COUNT}) = What's actually in the DB
   → Should match SQLAlchemy count (±orphans from refactoring)
   → If <SQLAlchemy: missing migrations (models not persisted)
   → If >SQLAlchemy: orphan migrations (old models removed from code)

================================================================================
DIAGNOSIS
================================================================================

Status: $( \
  if [ "${SQLALCHEMY_COUNT}" -eq "${MIGRATION_COUNT}" ]; then \
    echo "✅ MODELS AND MIGRATIONS MATCH"; \
  elif [ $((SQLALCHEMY_COUNT - MIGRATION_COUNT)) -le 2 ] && [ $((MIGRATION_COUNT - SQLALCHEMY_COUNT)) -le 2 ]; then \
    echo "⚠️ MINOR MISMATCH (within ±2, acceptable)"; \
  else \
    echo "❌ MISMATCH - Needs reconciliation"; \
  fi \
)

Difference: $((SQLALCHEMY_COUNT - MIGRATION_COUNT)) models

$( \
  if [ "${SQLALCHEMY_COUNT}" -gt "${MIGRATION_COUNT}" ]; then \
    echo "⚠️ You have ${SQLALCHEMY_COUNT} models but only ${MIGRATION_COUNT} migrated tables."; \
    echo "   This means some models are NOT persisted to the database."; \
    echo "   Run: alembic revision --autogenerate -m 'Add missing models'"; \
  elif [ "${MIGRATION_COUNT}" -gt "${SQLALCHEMY_COUNT}" ]; then \
    echo "⚠️ You have ${MIGRATION_COUNT} migrated tables but only ${SQLALCHEMY_COUNT} models."; \
    echo "   This means some old migrations reference deleted models."; \
    echo "   Review: audit_artifacts/.../2_migration_tables.txt vs 1_sqlalchemy_models.txt"; \
  else \
    echo "✅ Model count matches migration count. Database is in sync."; \
  fi \
)

================================================================================
DETAILED COMPARISONS
================================================================================

Files created for manual review:

1. SQLAlchemy models:        ${OUT}/1_sqlalchemy_models.txt
2. Migration tables:          ${OUT}/2_migration_tables.txt
3. Pydantic schemas:          ${OUT}/3_pydantic_schemas.txt
4. __tablename__ decls:       ${OUT}/4_tablename_declarations.txt
5. Model file locations:      ${OUT}/5_model_files.txt

To find missing models:
  comm -23 ${OUT}/1_sqlalchemy_models.txt ${OUT}/2_migration_tables.txt

To find orphan migrations:
  comm -13 ${OUT}/1_sqlalchemy_models.txt ${OUT}/2_migration_tables.txt

================================================================================
RECOMMENDED ACTIONS
================================================================================

1. Use SQLAlchemy count (${SQLALCHEMY_COUNT}) as the authoritative "model count"
   → Update all documentation to reflect this number

2. Review model-to-migration parity:
   → Run: comm -23 ${OUT}/1_sqlalchemy_models.txt ${OUT}/2_migration_tables.txt
   → If output is not empty, generate missing migrations

3. Don't count Pydantic schemas as "models"
   → They are API validation schemas, not database models
   → Clarify in docs: "${SQLALCHEMY_COUNT} database models, ${PYDANTIC_COUNT} API schemas"

4. If you see models but no migrations:
   → Create migration: alembic revision --autogenerate -m "Sync models"
   → Apply: alembic upgrade head

5. If you see migrations but no models:
   → Review: cat ${OUT}/2_migration_tables.txt
   → Remove orphan migrations or restore deleted models

================================================================================
EOF

cat "${OUT}/RECONCILIATION_REPORT.txt"

# ============================================================================
# FIND DISCREPANCIES
# ============================================================================

echo ""
echo "=========================================="
echo "DISCREPANCY ANALYSIS"
echo "=========================================="
echo ""

# Models not in migrations
echo "[Checking for models without migrations...]"
comm -23 "${OUT}/1_sqlalchemy_models.txt" "${OUT}/2_migration_tables.txt" > "${OUT}/models_without_migrations.txt"
MISSING_MIGRATIONS=$(wc -l < "${OUT}/models_without_migrations.txt")

if [ "${MISSING_MIGRATIONS}" -gt 0 ]; then
  echo "⚠️ Found ${MISSING_MIGRATIONS} models WITHOUT migrations:"
  cat "${OUT}/models_without_migrations.txt" | head -10
  [ "${MISSING_MIGRATIONS}" -gt 10 ] && echo "   (... and $((MISSING_MIGRATIONS - 10)) more)"
else
  echo "✅ All models have migrations"
fi

echo ""

# Migrations without models (orphans)
echo "[Checking for orphan migrations...]"
comm -13 "${OUT}/1_sqlalchemy_models.txt" "${OUT}/2_migration_tables.txt" > "${OUT}/migrations_without_models.txt"
ORPHAN_MIGRATIONS=$(wc -l < "${OUT}/migrations_without_models.txt")

if [ "${ORPHAN_MIGRATIONS}" -gt 0 ]; then
  echo "⚠️ Found ${ORPHAN_MIGRATIONS} orphan migrations (no corresponding model):"
  cat "${OUT}/migrations_without_models.txt" | head -10
  [ "${ORPHAN_MIGRATIONS}" -gt 10 ] && echo "   (... and $((ORPHAN_MIGRATIONS - 10)) more)"
else
  echo "✅ No orphan migrations"
fi

# ============================================================================
# SUMMARY OUTPUT
# ============================================================================

echo ""
echo "=========================================="
echo "RECONCILIATION COMPLETE"
echo "=========================================="
echo ""
echo "Results saved to: ${OUT}/"
echo ""
echo "Key files:"
echo "  - RECONCILIATION_REPORT.txt    (full analysis)"
echo "  - 1_sqlalchemy_models.txt      (authoritative model list)"
echo "  - 2_migration_tables.txt       (what's in the DB)"
echo "  - models_without_migrations.txt (needs alembic revision)"
echo "  - migrations_without_models.txt (orphan migrations)"
echo ""
echo "Authoritative Model Count: ${SQLALCHEMY_COUNT}"
echo ""
