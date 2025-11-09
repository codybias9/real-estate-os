# Real Estate OS - Audit & Verification Scripts

**Purpose:** Comprehensive static and runtime verification tools to prove platform capabilities and reconcile documentation claims vs. reality.

---

## Quick Start

```bash
# 1. Static analysis (no Docker required)
./scripts/audit_static.sh

# 2. Runtime verification (requires Docker)
./scripts/runtime_verification_dual.sh

# 3. Model reconciliation
./scripts/reconcile_models.sh

# 4. All branches comparison
./scripts/audit_all_branches.sh
```

---

## Scripts Overview

### 🔍 Static Analysis

#### `audit_static.sh`
**Purpose:** Scan codebase without running it
**Duration:** ~30 seconds
**Requirements:** None (just bash + standard Unix tools)
**Output:** `audit_artifacts/<timestamp>/static/`

**What it checks:**
- Endpoint decorators (`@router.get/post/put/delete`)
- Router files (`APIRouter` imports)
- SQLAlchemy models (`class ...Base`)
- Alembic migrations (`db/versions/*.py`)
- Tests (`test_*.py` files)
- Docker Compose services
- Airflow DAGs
- Frontend presence (`package.json`)
- Mock provider references (`MOCK_MODE` grep)

**When to use:**
- First audit of any branch
- Before runtime verification (sets expectations)
- CI/CD checks (fast, no dependencies)

---

#### `audit_all_branches.sh`
**Purpose:** Compare multiple branches side-by-side
**Duration:** ~2-3 minutes (static only)
**Requirements:** Git access to remote branches
**Output:** `audit_artifacts/branch_comparison_<timestamp>/`

**What it does:**
- Checks out each candidate branch
- Runs static counts (endpoints, routers, models)
- Generates comparison CSV
- Returns to original branch

**When to use:**
- Finding which branch has the full implementation
- Comparing feature parity across branches
- Locating "lost" code

**Branches audited by default:**
- `full-consolidation` (152 endpoints)
- `mock-providers-twilio` (132 endpoints)
- `review-real-estate-api` (74 endpoints)
- `continue-api-implementation` (32 endpoints)
- `crm-platform-full-implementation` (30 endpoints)

---

#### `reconcile_models.sh`
**Purpose:** Diagnose "20 vs 35 models" confusion
**Duration:** ~10 seconds
**Requirements:** None
**Output:** `audit_artifacts/model_reconciliation_<timestamp>/`

**What it reconciles:**
1. **SQLAlchemy Base subclasses** (authoritative DB models)
2. **Alembic migration tables** (what's in the DB)
3. **Pydantic schemas** (API validation, not DB models)
4. **`__tablename__` declarations** (explicit table names)

**Outputs:**
- `1_sqlalchemy_models.txt` - Authoritative model list
- `2_migration_tables.txt` - What's been migrated
- `3_pydantic_schemas.txt` - API schemas (NOT models)
- `models_without_migrations.txt` - Models missing from DB
- `migrations_without_models.txt` - Orphan migrations

**When to use:**
- Confusion about model counts
- Before `alembic revision --autogenerate`
- After major refactoring

---

### ⚙️ Runtime Verification

#### `runtime_verification_dual.sh`
**Purpose:** Prove MOUNTED endpoints vs DECLARED endpoints
**Duration:** ~30-45 minutes per branch
**Requirements:** Docker, docker-compose, curl, jq
**Output:** `audit_artifacts/runtime_verification_<timestamp>/`

**What it verifies:**
1. **Static pre-check** (declared endpoints, models, migrations)
2. **Docker boot** (`docker compose up -d --wait`)
3. **API health** (`/healthz` endpoint)
4. **OpenAPI spec** (MOUNTED endpoint count)
5. **Endpoint reconciliation** (declared vs mounted diff)
6. **Alembic migrations** (`alembic upgrade head`)
7. **Tests** (`pytest` with coverage)
8. **Demo flow** (POST + GET `/properties`)
9. **Mock providers** (check logs for mock implementations)
10. **Logs collection** (API logs for diagnosis)

**Branches verified:**
- `full-consolidation` (primary candidate)
- `mock-providers-twilio` (fallback candidate)

**Outputs per branch:**
- `SUMMARY.txt` - One-page overview
- `openapi/openapi.json` - Full OpenAPI spec
- `openapi/mounted_endpoints_count.txt` - The truth (e.g., "152")
- `openapi/reconciliation.txt` - Declared vs mounted analysis
- `models/base_subclasses.txt` - SQLAlchemy models
- `migrations/upgrade_output.txt` - Migration results
- `tests/pytest_output.txt` - Test results
- `tests/coverage_pct.txt` - Coverage percentage
- `demo/post_property.json` - Demo flow response
- `logs/api_full.log` - Complete API logs

**When to use:**
- After static analysis (to confirm findings)
- Before declaring a release candidate
- After fixing wiring issues (to re-verify)
- CI/CD integration (quality gate)

---

## Verification Workflow

### Phase 1: Discovery (5 minutes)
```bash
# Find which branches exist
git fetch --all
git branch -r | grep claude

# Compare all branches
./scripts/audit_all_branches.sh

# Review comparison
cat audit_artifacts/branch_comparison_*/BRANCH_COMPARISON_SUMMARY.md
```

**Output:** List of candidate branches ranked by endpoint count

---

### Phase 2: Static Deep Dive (2 minutes per branch)
```bash
# Checkout candidate
git checkout origin/claude/full-consolidation-... -b full-consolidation

# Static audit
./scripts/audit_static.sh

# Model reconciliation
./scripts/reconcile_models.sh

# Review
cat audit_artifacts/*/static/endpoints_decorators.txt
cat audit_artifacts/*/recon/RECONCILIATION_REPORT.txt
```

**Output:**
- Declared endpoint count
- Model count (authoritative)
- Migration parity

---

### Phase 3: Runtime Proof (30-45 minutes)
```bash
# Run dual verification (both candidates)
./scripts/runtime_verification_dual.sh

# Review results
cat audit_artifacts/runtime_verification_*/COMPARISON.txt
cat audit_artifacts/runtime_verification_*/full-consolidation/SUMMARY.txt
```

**Output:**
- MOUNTED endpoint count (the truth)
- Test results
- Demo flow success/failure
- Logs for diagnosis

---

### Phase 4: Decision (10 minutes)
```bash
# Review decision matrix
cat scripts/DECISION_MATRIX.md

# Compare results to scenarios
# Select winner based on criteria

# Document decision
echo "Winner: full-consolidation (152 mounted endpoints)" > DECISION.txt
```

**Output:** Clear release candidate selection

---

## Understanding the Outputs

### Static Analysis Success
```
=== Endpoint decorators ===
DECLARED_ENDPOINTS=152
ROUTER_FILES= 21

=== SQLAlchemy models ===
MODEL_COUNT= 20

=== Alembic migrations ===
versions dir: db/versions
b81dde19348f_add_ping_model.py
...
```

**Interpretation:**
- 152 endpoints declared in code
- 21 router files (auth, properties, leads, etc.)
- 20 database models
- Multiple migration files

---

### Runtime Verification Success
```
ENDPOINT COUNTS
--------------------------------------------------------------------------------
Declared (static grep):  152
Mounted (OpenAPI):       152
Difference:              0
Status:                  ✅ MATCH

TESTS
--------------------------------------------------------------------------------
Test Results:            42 passed, 3 failed
Coverage:                67%
```

**Interpretation:**
- All 152 endpoints are mounted ✅
- 93% test pass rate ✅
- Good coverage ✅
- **This branch is ready for release**

---

### Runtime Verification Failure
```
ENDPOINT COUNTS
--------------------------------------------------------------------------------
Declared (static grep):  152
Mounted (OpenAPI):       2
Difference:              150
Status:                  ⚠️ MISMATCH
```

**Interpretation:**
- Only 2 endpoints mounted (likely just `/healthz` and `/ping`)
- 150 endpoints declared but not included in `api/main.py`
- **Routing issue - check `app.include_router()` calls**

---

### Model Reconciliation Success
```
COUNTS SUMMARY
--------------------------------------------------------------------------------
SQLAlchemy Base subclasses:        20  ← AUTHORITATIVE (DB models)
Tables in Alembic migrations:      20
Pydantic schemas (API contracts):  67

Status: ✅ MODELS AND MIGRATIONS MATCH
```

**Interpretation:**
- 20 database models (authoritative count)
- 20 tables in migrations (perfect match) ✅
- 67 Pydantic schemas (API validation, NOT models)
- No missing migrations, no orphans ✅

---

### Model Reconciliation Failure
```
COUNTS SUMMARY
--------------------------------------------------------------------------------
SQLAlchemy Base subclasses:        20
Tables in Alembic migrations:      14
Pydantic schemas (API contracts):  67

⚠️ You have 20 models but only 14 migrated tables.
   This means some models are NOT persisted to the database.
   Run: alembic revision --autogenerate -m 'Add missing models'
```

**Interpretation:**
- 6 models have no migrations
- Database is missing 6 tables
- **Action:** Generate missing migrations

---

## Troubleshooting

### Issue: "Docker not available"
**Fix:** Run scripts on a machine with Docker, or use GitHub Actions

### Issue: "Only 2 endpoints mounted (expected 152)"
**Fix:**
```bash
# Check main.py for include_router calls
grep -n "include_router" api/main.py

# Check for import errors
docker compose logs api | grep -i error

# Verify routers are imported
head -50 api/main.py | grep "from api.routers import"
```

### Issue: "Tests fail completely"
**Fix:**
```bash
# Check pytest is installed
docker compose exec api pip list | grep pytest

# Run verbose
docker compose exec api pytest -v -s

# Check test database
docker compose exec api env | grep TEST_DB
```

### Issue: "Migrations fail"
**Fix:**
```bash
# Check Alembic config
docker compose exec api cat alembic.ini

# Check database connection
docker compose exec api python -c "from api.database import engine; print(engine.url)"

# Check migration history
docker compose exec api alembic history
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Runtime Verification

on: [pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Static Audit
        run: ./scripts/audit_static.sh

      - name: Runtime Verification
        run: ./scripts/runtime_verification_dual.sh

      - name: Upload Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: verification-results
          path: audit_artifacts/
```

---

## Next Steps After Verification

### If full-consolidation wins:
1. Create `release/full-consolidation-rc1` branch
2. Set up CI gates (see `DECISION_MATRIX.md`)
3. Add demo seed script
4. Open PR to main with evidence pack

### If mock-providers-twilio wins:
1. Use as interim release candidate
2. Fix full-consolidation wiring issues
3. Plan merge strategy

### If both fail verification:
1. Follow troubleshooting guide above
2. Fix routing/imports
3. Re-run verification
4. Delay release until issues resolved

---

## Supporting Documentation

- `RUNTIME_VERIFICATION_PLAN.md` - Detailed verification checklist
- `DECISION_MATRIX.md` - Objective decision criteria
- `audit_artifacts/` - All verification evidence
- `../docs/GITHUB_ACTIONS_MONITORING.md` - CI/CD setup guide

---

## Questions?

Review the full documentation:
- Static analysis results: `audit_artifacts/*/static/`
- Runtime verification: `audit_artifacts/runtime_verification_*/SUMMARY.txt`
- Model reconciliation: `audit_artifacts/model_reconciliation_*/RECONCILIATION_REPORT.txt`
- Decision criteria: `DECISION_MATRIX.md`
