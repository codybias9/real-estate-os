# Verification Script Hardening Checklist

**Purpose:** Document all false-positive failure modes addressed in enhanced verification

**Based on feedback:** User identified 6 critical gaps where scripts can "green" despite real problems

---

## Hardening Improvements

### 1. ✅ Route Introspection (Mounted Truth)

**Problem:** OpenAPI spec may exclude routes registered after startup, admin routes, or webhooks

**Solution:**
- Add `api/introspection.py` router with `/__introspection/routes` endpoint
- Returns `app.routes` directly (source of truth)
- Compare count to OpenAPI spec
- Flag if difference >5 routes

**Files:**
- `api/introspection.py` - Introspection endpoints
- `runtime_verification_enhanced.sh` - Calls introspection API

**Acceptance:**
- `app.routes` count within ±3 of OpenAPI count
- If >5 diff, investigate missing routes

---

### 2. ✅ Alembic Multiple Heads Detection

**Problem:** "Models = Migrations" can pass even with multiple heads or missing indexes

**Solution:**
- Run `alembic heads -v` and count heads
- **FAIL HARD** if >1 head detected
- Capture `alembic history --verbose | tail -50`
- Verify `alembic current` matches single head

**Files:**
- `runtime_verification_enhanced.sh:279-295`

**Acceptance:**
- Exactly 1 Alembic head ✅
- `alembic current` at head
- `alembic upgrade head` succeeds

---

### 3. ✅ Test Coverage Rigor

**Problem:** `--maxfail=1` masks broad failures; coverage may exclude key packages

**Solution:**
- Run tests TWICE:
  1. Fast fail (`--maxfail=1`) - early signal
  2. Full run (no maxfail) - complete picture with JUnit XML
- Capture coverage debug config:
  - `coverage debug sys` - System info
  - `coverage debug config` - Include/exclude rules
- Save `coverage.xml` and `htmlcov/` for post-analysis

**Files:**
- `runtime_verification_enhanced.sh:356-385`

**Acceptance:**
- Both test runs captured
- JUnit XML generated
- Coverage config shows api/, db/, providers/ are measured

---

### 4. ✅ SSE Event Capture

**Problem:** Demo flow only tests CRUD, not async/enrichment paths

**Solution:**
- Open SSE connection (`curl -N -H "Accept: text/event-stream"`)
- Capture events for 5 seconds
- Count `data:` lines in output
- Verify at least 1 event captured

**Files:**
- `runtime_verification_enhanced.sh:424-434`

**Acceptance:**
- SSE endpoint exists and responds
- At least 1 event captured during demo flow
- Events logged to `demo/sse_events.txt`

---

### 5. ✅ Mock Provider Network Guard

**Problem:** Log scraping can miss real provider instantiation; client created but not called

**Solution:**
- Add **bogus credentials** to `.env`:
  ```bash
  SENDGRID_API_KEY=BOGUS_KEY_SHOULD_NOT_BE_USED
  TWILIO_ACCOUNT_SID=BOGUS_SID
  AWS_ACCESS_KEY_ID=BOGUS_AWS_KEY
  ```
- Search logs for:
  - Network errors: `gaierror|connection.*refused|timeout|ssl.*error`
  - Bogus credential leaks: `BOGUS`
- **FAIL** if bogus creds appear in logs
- Provider introspection endpoint returns mock class names

**Files:**
- `runtime_verification_enhanced.sh:92-99` (bogus creds)
- `runtime_verification_enhanced.sh:328-350` (network check)

**Acceptance:**
- Zero bogus credential leaks ✅
- Zero network errors (or <5 benign ones)
- Provider introspection shows `MockEmailProvider`, `MockSMSProvider`, etc.

---

### 6. ✅ Docker Compose Config Capture

**Problem:** Different compose files between branches can mask issues

**Solution:**
- Before boot: `docker compose config > compose_resolved.yml`
- Capture service list: `docker compose config --services`
- Hash compose file: `md5sum docker-compose.yml`
- Store all in `compose/` directory

**Files:**
- `runtime_verification_enhanced.sh:122-135`

**Acceptance:**
- Resolved config captured
- Service list matches expected (api, db, redis, etc.)
- Hash documented for reproducibility

---

## Additional Hardening

### 7. ✅ DLQ Smoke Test (Optional)

**What:** Verify Dead Letter Queue workflow
**How:**
1. GET `/api/v1/ops/dlq` - count before
2. POST bad message to trigger DLQ
3. GET `/api/v1/ops/dlq` - count after
4. Verify count increased

**Files:**
- `runtime_verification_enhanced.sh:437-450`

---

### 8. ✅ Error Log Extraction

**What:** Surface exceptions/errors automatically
**How:**
- Extract error lines: `grep -i "error|exception|traceback"`
- Extract warnings: `grep -i "warning"`
- Save to `logs/errors.log` and `logs/warnings.log`

**Files:**
- `runtime_verification_enhanced.sh:454-456`

---

## Setup Instructions

### Add Introspection Router (Required)

Edit `api/main.py` and add:

```python
# At top with other imports
import os
from api.introspection import router as introspection_router

# After app = FastAPI(...)
if os.getenv("VERIFY_MODE") == "true":
    app.include_router(introspection_router)
```

This enables:
- `/__introspection/routes` - All mounted routes
- `/__introspection/providers` - Provider configuration
- `/__introspection/health-detailed` - Component health

**Note:** Only enabled when `VERIFY_MODE=true` (set by verification script)

---

## Enhanced vs Standard Script

| Check | Standard (`runtime_verification_dual.sh`) | Enhanced (`runtime_verification_enhanced.sh`) |
|-------|-------------------------------------------|------------------------------------------------|
| OpenAPI endpoint count | ✅ | ✅ |
| app.routes introspection | ❌ | ✅ |
| Alembic heads validation | ❌ | ✅ Fails on multiple heads |
| Test coverage config | ❌ | ✅ Debug output captured |
| SSE event capture | ❌ | ✅ |
| Network isolation check | ❌ | ✅ Bogus creds + error detection |
| DLQ smoke test | ❌ | ✅ |
| Compose config capture | ❌ | ✅ |
| Error log extraction | ❌ | ✅ |

---

## Hard Acceptance Bars

For a branch to be **PASS** (Release Candidate worthy):

### Critical (Must Pass)
1. **Mounted endpoints:** ≥140 (or ≥95% of declared)
2. **app.routes vs OpenAPI:** Within ±3 routes
3. **Alembic heads:** Exactly 1 ✅
4. **Migration upgrade:** Succeeds without errors
5. **Bogus credential leaks:** 0 occurrences
6. **Network errors:** 0 (or <5 benign)
7. **API boot:** No unhandled exceptions

### High Priority (Should Pass)
8. **Test pass rate:** ≥60%
9. **Test coverage:** ≥30%
10. **Demo flow:** POST + GET `/properties` works
11. **SSE events:** ≥1 event captured
12. **Provider introspection:** Shows mock classes

### Nice to Have
13. **DLQ:** Smoke test passes
14. **Coverage config:** Includes api/, db/, providers/
15. **JUnit XML:** Generated successfully

---

## Failure Scenarios

### Scenario: Bogus Credentials in Logs ❌

**Symptom:**
```
network/bogus_credential_leaks.txt shows:
Authorization: BOGUS_KEY_SHOULD_NOT_BE_USED
```

**Diagnosis:** Real providers are being instantiated despite `MOCK_MODE=true`

**Fix:**
1. Check `api/providers/factory.py` or `api/integrations/factory.py`
2. Verify mock selection logic:
   ```python
   if os.getenv("MOCK_MODE") == "true":
       return MockEmailProvider()
   else:
       return SendGridEmailProvider()
   ```
3. Ensure factory is used everywhere (not direct imports)

---

### Scenario: Multiple Alembic Heads ❌

**Symptom:**
```
migrations/heads.txt shows:
abc123 (head)
def456 (head)
```

**Diagnosis:** Migration branch diverged (common after merges)

**Fix:**
```bash
# Merge heads
alembic merge abc123 def456 -m "Merge migration heads"
alembic upgrade head
```

---

### Scenario: app.routes >> OpenAPI ⚠️

**Symptom:**
```
app.routes total:    175
Mounted (OpenAPI):   152
Difference:          23
```

**Diagnosis:** Admin/internal routes not in OpenAPI spec

**Fix:**
1. Check if acceptable (internal routes OK to exclude)
2. If not, verify OpenAPI tags on all routes
3. Check for startup event routes

---

### Scenario: Zero SSE Events 🔍

**Symptom:**
```
SSE Events Captured: 0 events
```

**Diagnosis:** SSE endpoint exists but not emitting events

**Possible causes:**
1. No background jobs running during demo
2. SSE requires auth (not provided)
3. Events only emit on specific triggers

**Fix:**
- Trigger an event explicitly (POST property → enrichment)
- Check SSE endpoint requires auth, provide token
- Verify SSE implementation is wired correctly

---

## Output Interpretation

### Perfect Run (Release Candidate)

```
ENDPOINT COUNTS (CRITICAL)
Declared (static grep):  152
Mounted (OpenAPI):       152
app.routes total:        155
Difference (decl-mount): 0
Status:                  ✅ MATCH

MIGRATIONS (CRITICAL)
Alembic Heads:           1 ✅
Migration Status:        abc123def456 (head)
Upgrade Success:         ✅

TESTS (CRITICAL)
Full Run Results:        142 passed, 8 failed
Coverage:                67%

MOCK PROVIDERS (CRITICAL)
Provider Config:         MockEmailProvider, MockSMSProvider, MockStorageClient
Network Errors:          0 lines ✅
Bogus Creds in Logs:     0 occurrences ✅

DEMO FLOW
POST /properties:        ✅ Attempted
SSE Events Captured:     3 events
```

**Verdict:** ✅ **RELEASE CANDIDATE**

---

### Marginal Run (Needs Minor Fixes)

```
ENDPOINT COUNTS (CRITICAL)
Mounted (OpenAPI):       145
Declared:                152
Difference:              7 ⚠️

TESTS (CRITICAL)
Full Run Results:        89 passed, 23 failed
Coverage:                42%

MOCK PROVIDERS (CRITICAL)
Network Errors:          3 lines ⚠️
Bogus Creds:             0 ✅
```

**Verdict:** ⚠️ **Needs Investigation**
- 7 endpoints missing (check feature flags)
- 21% test failure (investigate, may be acceptable)
- Minor network errors (review logs)

---

### Failed Run (Not Ready)

```
ENDPOINT COUNTS (CRITICAL)
Mounted (OpenAPI):       2 ❌
Declared:                152

MIGRATIONS (CRITICAL)
Alembic Heads:           3 ❌ MULTIPLE HEADS!

MOCK PROVIDERS (CRITICAL)
Bogus Creds in Logs:     47 occurrences ❌ LEAK!
```

**Verdict:** ❌ **NOT READY**
- Major routing issue (only health endpoints)
- Migration branches need merging
- Real providers being used despite MOCK_MODE

---

## Checklist: Before Running Enhanced Verification

- [ ] Add introspection router to `api/main.py`
- [ ] Ensure `.env.mock` exists with `MOCK_MODE=true`
- [ ] Docker and docker-compose installed
- [ ] Ports 8000, 5432, 6379 available
- [ ] At least 4GB free disk space
- [ ] Network access for Docker pulls

---

## Checklist: After Running

- [ ] Review both `SUMMARY.txt` files
- [ ] Check critical criteria (endpoints, heads, bogus creds)
- [ ] Review error logs if any warnings
- [ ] Compare to PASS/FAIL criteria
- [ ] Select release candidate or document fixes needed
- [ ] Attach artifacts to PR if passing

---

## Commands

```bash
# Run enhanced verification
chmod +x scripts/runtime_verification_enhanced.sh
./scripts/runtime_verification_enhanced.sh

# Quick check (manual)
docker compose up -d
curl -s http://localhost:8000/__introspection/routes | jq '.total_routes'
curl -s http://localhost:8000/__introspection/providers | jq '.providers'
docker compose logs api | grep -i bogus
docker compose down -v

# Review results
cat audit_artifacts/runtime_enhanced_*/full-consolidation/SUMMARY.txt
cat audit_artifacts/runtime_enhanced_*/mock-providers-twilio/SUMMARY.txt
```

---

## Timeline

**Enhanced verification:** ~45-60 min per branch (90-120 min total)

Breakdown:
- Static analysis: 1 min
- Docker boot: 2-5 min
- Health check: 1-2 min
- OpenAPI + introspection: 1 min
- Alembic migrations: 2-5 min
- Tests (2 runs + coverage): 10-20 min
- Demo flow: 2-5 min
- SSE probe: 1 min
- Log collection: 2-5 min
- Shutdown: 1 min
- Summary generation: 1 min

**Worth it:** Catches 6 major false-positive scenarios

---

## Next Steps After Passing

1. Create `release/<branch>-rc1` branch
2. Open PR to main with artifacts attached
3. Set up CI gates using enhanced script
4. Tag as `v1.0.0-rc1`
5. Deploy to staging for manual QA

---

## Support

- Review: `scripts/DECISION_MATRIX.md` for interpretation
- Debugging: Check `logs/errors.log` and `logs/api_full.log`
- Questions: Review `scripts/README.md`
