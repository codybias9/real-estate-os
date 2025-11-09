# Runtime Verification Plan - Dual Branch Proof

**Objective:** Prove which branch has the complete, working platform by measuring MOUNTED endpoints vs DECLARED endpoints, and verifying all subsystems work.

**Date:** 2025-11-09
**Verification Script:** `scripts/runtime_verification_dual.sh`

---

## Branches Under Test

### Primary: `full-consolidation`
- **Static Analysis:** 152 declared endpoints, 21 routers, 20 models
- **Expected:** 140-152 mounted endpoints
- **Features:** Versioned API, full mock providers, 47 tests, production middleware

### Secondary: `mock-providers-twilio`
- **Static Analysis:** 132 declared endpoints, 16 routers, 20 models
- **Expected:** 120-132 mounted endpoints
- **Features:** Mock integrations, Docker Compose, demo-focused

---

## Verification Checklist

### ✅ Static Analysis (Pre-Boot)
- [ ] Count declared endpoints via `grep @router.*`
- [ ] Count SQLAlchemy Base subclasses (authoritative model count)
- [ ] List Alembic migration files
- [ ] Verify `.env.mock` exists and contains `MOCK_MODE=true`
- [ ] List router files and verify imports in `main.py`

### ✅ Docker Compose Boot
- [ ] `docker compose up -d --wait` succeeds
- [ ] All services start (check `docker compose ps`)
- [ ] API health endpoint responds within 120s
- [ ] No crash loops in logs

### ✅ OpenAPI Spec Validation
- [ ] Fetch `http://localhost:8000/docs/openapi.json`
- [ ] Count mounted endpoints: `jq '.paths | keys | length'`
- [ ] Extract all endpoint paths for audit
- [ ] **Critical:** Compare mounted vs declared counts
  - Match (±2) = ✅ All routers mounted
  - Diff >10 = ⚠️ Some routers not included
  - Diff >50 = ❌ Major wiring issue

### ✅ Database & Migrations
- [ ] Run `alembic upgrade head` inside container
- [ ] Check migration status: `alembic current`
- [ ] Verify no migration failures in logs
- [ ] Cross-check: migration count vs model count
  - Expected: ~1-3 migrations per 5-10 models
  - Red flag: 20 models but 0 migrations = models not persisted

### ✅ Test Execution
- [ ] Run `pytest -q --maxfail=1 --disable-warnings`
- [ ] Capture test summary (passed/failed/errors)
- [ ] Run with coverage: `pytest --cov=. --cov-report=xml`
- [ ] Extract coverage percentage
- [ ] **Acceptance:** >60% pass rate, >30% coverage for RC candidate

### ✅ Demo Flow (End-to-End)
- [ ] Test: `POST /api/v1/properties` with sample payload
- [ ] Verify: 201 Created or 200 OK (depending on auth requirements)
- [ ] Test: `GET /api/v1/properties` returns list
- [ ] Verify: Response contains created property OR list is queryable
- [ ] **Critical:** At least 1 CRUD flow works without external dependencies

### ✅ Mock Provider Verification
- [ ] Check `api/providers/factory.py` or `api/integrations/factory.py` exists
- [ ] Verify MOCK_MODE flag selects mock implementations
- [ ] Test email mock: check logs for "MockEmailProvider" or similar
- [ ] Test SMS mock: check logs for "MockSMSProvider"
- [ ] Test storage mock: check logs for "MockStorageClient"
- [ ] **Goal:** Confirm all external services are mocked (no real API calls)

### ✅ Middleware & Features
- [ ] Verify rate limiting middleware loaded (check logs or test endpoint)
- [ ] Verify ETag middleware loaded
- [ ] Check for DLQ endpoints in OpenAPI spec
- [ ] Check for `/metrics` endpoint (Prometheus)
- [ ] Check for SSE endpoints (real-time events)

### ✅ Logs & Diagnostics
- [ ] Capture full API logs: `docker compose logs api > api_full.log`
- [ ] Tail last 500 lines: `docker compose logs api | tail -500`
- [ ] Look for errors, warnings, or exceptions
- [ ] Verify no import errors (common cause of missing routes)

---

## Decision Matrix

### Outcome 1: full-consolidation Wins
**Criteria:**
- Mounted endpoints: 140-152 ✅
- Models vs migrations: Balanced (no orphans) ✅
- Tests: >60% pass, >30% coverage ✅
- Demo flow: Works ✅
- Mock providers: Wired correctly ✅

**Action:**
- Make `full-consolidation` the release candidate
- Create `release/full-consolidation-rc1` branch
- Run CI gates (lint, type checks, tests, Docker build)
- Open PR to main with evidence pack

---

### Outcome 2: mock-providers-twilio Wins
**Criteria:**
- full-consolidation has <100 mounted routes (major wiring issue)
- mock-providers-twilio has 120-132 mounted routes ✅
- Tests and demo flow work on mock branch ✅

**Action:**
- Make `mock-providers-twilio` the release candidate
- Investigate full-consolidation wiring issues (likely `main.py` import problem)
- Back-port fixes from full-consolidation once routing is fixed

---

### Outcome 3: Both Have Issues
**Criteria:**
- Both branches have <100 mounted routes
- OR migrations fail on both
- OR tests fail completely on both

**Action:**
- Review `api/main.py` on both branches for `app.include_router()` calls
- Check for feature flags that disable routers
- Check for circular import issues (common cause)
- Fix wiring, re-verify, then pick winner

---

### Outcome 4: Endpoint Count Mismatch (Declared > Mounted)
**Criteria:**
- Declared: 152, Mounted: 85 (example)
- Difference >20 endpoints

**Root Causes:**
1. **Missing include_router() calls:** Routers defined but not mounted in `main.py`
2. **Feature flags:** Some routers only mount if `ENABLE_FEATURE_X=true`
3. **Conditional imports:** Routers in try/except that fail silently
4. **Version mismatch:** Decorators in v1/ and v2/ folders but only v1 mounted

**Fix:**
- Audit `api/main.py` for all `app.include_router(...)` calls
- Cross-reference with router file list
- Add missing routers or document as "not production-ready"

---

## Model Count Reconciliation

### Expected Count Sources:
1. **SQLAlchemy Base subclasses** (authoritative):
   ```bash
   find . -name "*.py" | xargs grep "class.*Base" | grep -v "^#" | wc -l
   ```

2. **Alembic migrations** (should match models):
   ```bash
   ls -1 db/versions/*.py | wc -l
   ```

3. **Pydantic schemas** (API contracts, not DB models):
   ```bash
   find api/schemas -name "*.py" | wc -l
   ```

### Reconciliation Rules:
- **Base subclasses = Migration coverage:** ✅ Good
- **Base subclasses > Migrations:** ⚠️ Missing migrations (models not persisted)
- **Base subclasses < Migrations:** ⚠️ Orphan migrations (old models removed)

### Action if Mismatch:
- List all Base subclasses: `grep -r "class.*Base" api/ db/ | cut -d: -f2 | sort > models_actual.txt`
- List all migration targets: `grep -r "create_table\|drop_table" db/versions/ | cut -d'"' -f2 | sort -u > models_in_migrations.txt`
- Diff: `diff models_actual.txt models_in_migrations.txt`

---

## Expected Artifacts (Per Branch)

After running `scripts/runtime_verification_dual.sh`, you'll get:

```
audit_artifacts/runtime_verification_<timestamp>/
├── COMPARISON.txt (side-by-side table)
├── full-consolidation/
│   ├── SUMMARY.txt (one-page overview)
│   ├── openapi/
│   │   ├── openapi.json (MOUNTED endpoints)
│   │   ├── mounted_endpoints_count.txt (e.g., "152")
│   │   ├── endpoint_paths.txt (list of all paths)
│   │   └── reconciliation.txt (declared vs mounted)
│   ├── models/
│   │   └── base_subclasses.txt (SQLAlchemy models)
│   ├── migrations/
│   │   ├── migration_files.txt (Alembic versions)
│   │   ├── upgrade_output.txt (alembic upgrade head)
│   │   └── current.txt (current migration)
│   ├── tests/
│   │   ├── pytest_output.txt (test results)
│   │   ├── coverage_output.txt (coverage report)
│   │   ├── summary.txt (e.g., "42 passed, 3 failed")
│   │   └── coverage_pct.txt (e.g., "67%")
│   ├── demo/
│   │   ├── property_payload.json (sample POST)
│   │   ├── post_property.json (response)
│   │   └── get_properties.json (list response)
│   └── logs/
│       ├── api_full.log (complete API logs)
│       ├── api_tail.log (last 500 lines)
│       ├── compose_up.log
│       └── compose_ps.txt
└── mock-providers-twilio/
    └── (same structure)
```

---

## Success Criteria (Release Candidate)

A branch qualifies as RC if:

1. **Endpoint Fidelity:** Mounted ≥ 95% of declared (±5 endpoints acceptable)
2. **Database Integrity:** Models = Migrations (±2 orphans acceptable)
3. **Test Quality:** >60% pass rate, >30% coverage
4. **Demo Flow:** At least 1 CRUD operation works end-to-end
5. **Mock Providers:** All external services mocked (no real API calls)
6. **No Critical Errors:** API boots without exceptions, logs are clean

---

## Timeline

**Duration:** ~30-45 minutes per branch (with Docker)

**Steps:**
1. Run `chmod +x scripts/runtime_verification_dual.sh` (5 min)
2. Execute script: `./scripts/runtime_verification_dual.sh` (30-40 min)
3. Review artifacts: `cat audit_artifacts/runtime_verification_*/COMPARISON.txt` (5 min)
4. Make decision based on matrix above (5 min)

**Total:** ~1 hour for both branches

---

## Troubleshooting

### Issue: "API never became healthy"
**Fix:**
- Check `docker compose logs api`
- Common causes: DB connection failure, import errors, missing env vars
- Verify `.env.mock` has all required keys

### Issue: "Mounted endpoints = 2 (only /healthz and /ping)"
**Fix:**
- Check `api/main.py` for `app.include_router()` calls
- Verify routers are imported at top of file
- Check for try/except blocks that swallow import errors

### Issue: "Tests fail completely"
**Fix:**
- Check if pytest is installed: `docker compose exec api pip list | grep pytest`
- Verify test database is configured (often needs separate `TEST_DB_DSN`)
- Try running with verbose: `pytest -v -s`

### Issue: "Migrations fail"
**Fix:**
- Check if Alembic is configured: `ls db/alembic.ini`
- Verify database connection in container
- Run `alembic history` to check for duplicate heads

---

## Next Steps After Verification

### If full-consolidation wins:
1. Create `release/full-consolidation-rc1` branch
2. Set up CI gates (see below)
3. Add demo seed script if missing
4. Open PR to main with evidence pack

### If mock-providers-twilio wins:
1. Use as interim release candidate
2. Fix full-consolidation wiring issues
3. Plan merge strategy

### CI Gates (for RC branch):
```yaml
- name: Lint & Type Checks
  run: ruff check . && mypy api/

- name: Tests
  run: pytest --maxfail=5 -q

- name: Docker Build
  run: docker compose build api

- name: Runtime Verification
  run: ./scripts/runtime_verification_dual.sh

- name: Artifact Upload
  uses: actions/upload-artifact@v3
  with:
    name: runtime-verification
    path: audit_artifacts/runtime_verification_*/
```

---

## Contact / Escalation

If both branches fail verification or results are unclear:
- Review `audit_artifacts/runtime_verification_*/SUMMARY.txt` for both branches
- Compare `openapi/reconciliation.txt` to diagnose routing issues
- Check logs for import errors or circular dependencies
- Consider rolling back to last known-good commit and re-verifying
