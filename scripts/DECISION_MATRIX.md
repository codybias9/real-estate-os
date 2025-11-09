# Runtime Verification - Decision Matrix

**Purpose:** Objective criteria for selecting the release candidate branch based on runtime verification results.

**Date:** 2025-11-09

---

## Quick Reference Table

| Metric | full-consolidation | mock-providers-twilio | Threshold | Winner? |
|--------|--------------------|-----------------------|-----------|---------|
| **Declared Endpoints** | 152 | 132 | N/A | - |
| **Mounted Endpoints** | *[TBD]* | *[TBD]* | ≥120 | 🏆 |
| **Endpoint Fidelity** | *[TBD]* | *[TBD]* | ≥95% | 🏆 |
| **SQLAlchemy Models** | 20 | 20 | ≥15 | ✅ |
| **Alembic Migrations** | *[TBD]* | *[TBD]* | Match models ±2 | ✅ |
| **Test Pass Rate** | *[TBD]* | *[TBD]* | ≥60% | 🏆 |
| **Test Coverage** | *[TBD]* | *[TBD]* | ≥30% | 🏆 |
| **Demo Flow** | *[TBD]* | *[TBD]* | ≥1 CRUD works | 🏆 |
| **Mock Providers** | *[TBD]* | *[TBD]* | All wired | 🏆 |

**Legend:**
- 🏆 = Deciding factor (high weight)
- ✅ = Must pass (gate)
- *[TBD]* = Fill in after running `runtime_verification_dual.sh`

---

## Scenario 1: full-consolidation WINS (Expected)

### Criteria Met:
```
Mounted endpoints:    140-152  ✅ (≥95% fidelity)
Models vs migrations: Balanced ✅ (±2 acceptable)
Tests:                >60% pass, >30% coverage ✅
Demo flow:            POST + GET /properties works ✅
Mock providers:       All wired (email, SMS, PDF, storage) ✅
Logs:                 No critical errors ✅
```

### Decision: ✅ **Make full-consolidation the Release Candidate**

### Actions:
1. **Immediate (Day 1):**
   - Create `release/full-consolidation-rc1` branch
   - Cherry-pick any critical fixes from other branches
   - Update `README.md` with verified endpoint count
   - Tag as `v1.0.0-rc1`

2. **CI/CD Setup (Day 2):**
   - Add GitHub Actions workflow:
     - Lint (ruff, mypy)
     - Tests (pytest with coverage)
     - Docker build
     - Runtime verification (same script)
   - Set up branch protection for `main`
   - Require CI gates to pass before merge

3. **Documentation (Day 3):**
   - Update `docs/` with actual endpoint count
   - Add `DEMO_GUIDE.md` with sample API calls
   - Create `scripts/demo/seed.sh` for demo data
   - Document all mock provider configurations

4. **Demo Polish (Day 4):**
   - Ensure 3-5 key flows work:
     - User registration + login
     - Property CRUD
     - Lead creation + enrichment
     - Workflow automation trigger
     - Email/SMS mock verification
   - Record screen demo or curl script

5. **Release (Day 5):**
   - Open PR: `release/full-consolidation-rc1` → `main`
   - Attach evidence pack:
     - `audit_artifacts/runtime_verification_*/SUMMARY.txt`
     - `openapi.json`
     - `coverage.xml`
     - Demo flow recordings
   - Merge after review
   - Tag `v1.0.0`

---

## Scenario 2: mock-providers-twilio WINS (Fallback)

### Criteria Met:
```
full-consolidation:
  Mounted endpoints:  <100  ❌ (major wiring issue)
  Demo flow:          Fails ❌

mock-providers-twilio:
  Mounted endpoints:  120-132 ✅
  Tests:              >50% pass ✅
  Demo flow:          Works ✅
  Mock providers:     All wired ✅
```

### Decision: ⚠️ **Use mock-providers-twilio as interim RC**

### Actions:
1. **Immediate:**
   - Create `release/mock-providers-rc1` branch
   - Document known limitations (fewer tests, fewer features)
   - Tag as `v1.0.0-rc1-demo`

2. **Parallel Track: Fix full-consolidation:**
   - Investigate wiring issue (likely `api/main.py`)
   - Common causes:
     - Missing `app.include_router()` calls
     - Import errors (check logs for `ModuleNotFoundError`)
     - Feature flags disabling routes
     - Circular dependencies
   - Fix and re-verify
   - Plan merge: `mock-providers-twilio` + `full-consolidation` fixes

3. **Short-term Release:**
   - Use mock-providers-twilio for demos/MVP
   - Set expectation: "Demo release, not production"
   - Plan upgrade path to full-consolidation once fixed

4. **Medium-term:**
   - Once full-consolidation is fixed, deprecate mock-providers-twilio
   - Migrate to full-consolidation as official v1.0.0

---

## Scenario 3: Both Have Wiring Issues (Needs Fix)

### Criteria Met:
```
full-consolidation:
  Mounted endpoints:  <100  ❌
  Fidelity:           <65%  ❌

mock-providers-twilio:
  Mounted endpoints:  <100  ❌
  Fidelity:           <75%  ❌
```

### Decision: 🔧 **Fix Before Release**

### Root Cause Analysis:
1. **Check `api/main.py` for router includes:**
   ```python
   # Expected pattern:
   from api.routers import auth, properties, leads, ...
   app.include_router(auth.router, prefix="/api/v1")
   app.include_router(properties.router, prefix="/api/v1")
   ...
   ```

2. **Check for import errors in logs:**
   ```bash
   docker compose logs api | grep -i "error\|exception\|failed"
   ```

3. **Check for feature flags:**
   ```python
   # Anti-pattern:
   if os.getenv("ENABLE_FEATURE_X") == "true":
       app.include_router(feature_x.router)
   # Solution: Set all feature flags in .env.mock
   ```

4. **Check for conditional imports:**
   ```python
   # Anti-pattern:
   try:
       from api.routers import advanced_features
       app.include_router(advanced_features.router)
   except ImportError:
       pass  # Silently skip - BAD
   ```

### Fix Steps:
1. List all router files:
   ```bash
   find api/routers -name "*.py" | grep -v __
   ```

2. Grep for `include_router` calls:
   ```bash
   grep -n "include_router" api/main.py
   ```

3. Cross-reference:
   - If 21 router files but only 10 `include_router` calls → add missing ones

4. Check imports:
   - Run: `python -m api.main` and check for import errors

5. Re-verify:
   ```bash
   ./scripts/runtime_verification_dual.sh
   ```

### After Fix:
- Re-evaluate using Scenario 1 or 2

---

## Scenario 4: Endpoint Count Close But Not Perfect

### Criteria Met:
```
full-consolidation:
  Declared:  152
  Mounted:   145  ⚠️ (95.4% fidelity - acceptable)
  Tests:     65% pass ✅
  Demo flow: Works ✅
```

### Decision: ✅ **Accept with Documentation**

### Actions:
1. **Document the 7 missing endpoints:**
   - Run diff: `comm -23 declared_endpoints.txt mounted_endpoints.txt`
   - Classify each:
     - "Not production-ready" → OK to exclude
     - "Feature flagged" → Document flag requirements
     - "Bug" → File issue, plan fix in v1.1.0

2. **Update claims:**
   - Docs: "145 production endpoints (152 total, 7 experimental)"
   - OpenAPI: Add tags to experimental endpoints

3. **Proceed with release:**
   - If missing endpoints are non-critical, this is acceptable
   - Plan to mount remaining endpoints in v1.1.0

---

## Scenario 5: Model/Migration Mismatch

### Criteria Met:
```
SQLAlchemy models:      20
Alembic migrations:     14  ❌ (6 models not migrated)
```

### Decision: 🔧 **Fix Migrations Before Release**

### Fix Steps:
1. **Generate missing migrations:**
   ```bash
   docker compose exec api alembic revision --autogenerate -m "Add missing models"
   docker compose exec api alembic upgrade head
   ```

2. **Verify:**
   ```bash
   ./scripts/reconcile_models.sh
   # Should show: Models = Migrations
   ```

3. **Re-verify runtime:**
   ```bash
   ./scripts/runtime_verification_dual.sh
   ```

### Acceptance:
- Models = Migrations ±1 is OK (minor refactoring)
- Models = Migrations ±5+ is NOT OK (needs fix)

---

## Scenario 6: Tests Fail Completely

### Criteria Met:
```
Mounted endpoints: 150 ✅
Tests:             0 passed, 47 failed ❌
Coverage:          N/A ❌
```

### Decision: ⚠️ **Proceed with Caution OR Fix**

### Root Cause Analysis:
1. **Check test configuration:**
   - Missing `pytest.ini` or `conftest.py`?
   - Test database not configured (needs `TEST_DB_DSN`)?
   - Missing test dependencies (`pip install pytest pytest-cov`)?

2. **Run tests with verbose:**
   ```bash
   docker compose exec api pytest -v -s --tb=short
   ```

3. **Common issues:**
   - Import errors (check `sys.path`)
   - Database connection (tests need separate DB)
   - Fixtures not defined (check `conftest.py`)
   - Async tests need `pytest-asyncio`

### Options:
**Option A: Fix Tests (Recommended)**
- Invest 2-4 hours fixing test configuration
- Get at least 30% passing
- Release with partial test coverage

**Option B: Release Without Tests (Risky)**
- Document: "Tests need configuration, see #123"
- Manual testing only
- Plan test fix in v1.0.1

**Option C: Delay Release**
- Fix all tests first
- Release only when >60% pass
- More confidence, longer timeline

---

## Scenario 7: Demo Flow Fails

### Criteria Met:
```
Mounted endpoints: 150 ✅
Demo flow:         POST /properties → 401 Unauthorized ❌
```

### Decision: 🔧 **Fix Auth or Provide Test Credentials**

### Fix Steps:
1. **Check if auth is required:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/properties \
     -H "Content-Type: application/json" \
     -d '{"address":"123 Main St"}'
   # If 401: auth required
   ```

2. **Get test token:**
   ```bash
   # Register test user
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test123"}'

   # Login
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test123"}'
   # Extract token from response
   ```

3. **Update demo script:**
   ```bash
   TOKEN="..." # From login response
   curl -X POST http://localhost:8000/api/v1/properties \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"address":"123 Main St"}'
   ```

4. **Document in `DEMO_GUIDE.md`:**
   - Include registration + login steps
   - Provide test credentials
   - Show full curl commands

---

## Final Decision Criteria (Weighted)

| Factor | Weight | full-consolidation | mock-providers-twilio | Notes |
|--------|--------|--------------------|------------------------|-------|
| **Mounted Endpoints** | 30% | *[TBD]* | *[TBD]* | Most critical |
| **Endpoint Fidelity** | 20% | *[TBD]* | *[TBD]* | Declared vs mounted |
| **Tests Pass** | 15% | *[TBD]* | *[TBD]* | Quality signal |
| **Demo Flow Works** | 15% | *[TBD]* | *[TBD]* | Usability proof |
| **Mock Providers** | 10% | *[TBD]* | *[TBD]* | Development experience |
| **Test Coverage** | 5% | *[TBD]* | *[TBD]* | Nice to have |
| **Models=Migrations** | 5% | *[TBD]* | *[TBD]* | Database integrity |

**Scoring:**
- Calculate weighted score for each branch
- Highest score wins
- Minimum threshold: 70% total score to be RC-worthy

---

## Recommended Next Steps

### Step 1: Run Verification (1 hour)
```bash
chmod +x scripts/runtime_verification_dual.sh
./scripts/runtime_verification_dual.sh
```

### Step 2: Review Results (15 min)
```bash
cat audit_artifacts/runtime_verification_*/COMPARISON.txt
cat audit_artifacts/runtime_verification_*/full-consolidation/SUMMARY.txt
cat audit_artifacts/runtime_verification_*/mock-providers-twilio/SUMMARY.txt
```

### Step 3: Apply Decision Matrix (10 min)
- Match results to scenarios above
- Select appropriate action plan
- Document decision rationale

### Step 4: Execute Plan (1-5 days)
- Follow action steps from matched scenario
- Track progress with checklist
- Re-verify after any fixes

---

## Success Metrics (Post-Release)

Once RC is selected and released:

1. **Endpoint Stability:** No crashes when calling any endpoint
2. **Demo Success:** 5/5 demo flows work without errors
3. **Test Coverage:** Trend upward (each PR adds tests)
4. **Documentation Accuracy:** Claims match runtime reality
5. **Developer Onboarding:** New dev can boot stack in <10 min

**Target:** All metrics at 80%+ within 30 days of v1.0.0 release

---

## Appendix: Quick Commands

```bash
# Run full verification
./scripts/runtime_verification_dual.sh

# Check model reconciliation
./scripts/reconcile_models.sh

# Manual endpoint count
docker compose up -d
curl -s http://localhost:8000/docs/openapi.json | jq '.paths | keys | length'

# Manual test run
docker compose exec api pytest -q

# Manual demo flow
docker compose exec api python scripts/demo/test_flow.py

# Logs
docker compose logs api | tail -500
```
