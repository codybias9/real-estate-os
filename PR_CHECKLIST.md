# PR Checklist - Do Not Merge Without This Evidence

**Branch:** `claude/audit-wiring-readiness-014VYQdX46CD1u2s6KGWqbGw`

---

## ⚠️ REALITY CHECK

**What's PROVEN (Static Analysis):**
- ✅ Code exists (142 endpoints, 6 frontend pages, SSE infrastructure, auth framework)
- ✅ Imports correct (TypeScript compiles)
- ✅ Scripts exist (verification scripts created)
- ✅ Documentation complete (comprehensive guides written)

**What's THEORETICAL (Not Yet Proven):**
- ⚠️ Services actually start
- ⚠️ Auth flip works (401 → 200)
- ⚠️ Write guard blocks unauthenticated writes
- ⚠️ SSE stream connects and receives events
- ⚠️ Frontend pages load without errors
- ⚠️ Auth token logs in console
- ⚠️ SSE badge shows "Connected"
- ⚠️ Toast appears when event emitted
- ⚠️ CI passes

**Until you run the services and capture artifacts, "demo-ready" is a CLAIM, not PROOF.**

---

## MUST-PASS GATES (Backend/API)

### Gate 1: OpenAPI Parity
**Command:**
```bash
./COLLECT_PR_EVIDENCE.sh
```

**Required Evidence:**
```json
{
  "paths": >= 140,
  "tags": ["auth", "properties", "workflow", "automation", "data", "system", ...]
}
```

**Paste in PR:** `artifacts/pr_evidence/openapi_summary.json`

**Status:** [ ] PASS / [ ] FAIL

---

### Gate 2: Auth Flip
**Required Evidence:**
```
PATCH /properties/{id} (no token) → 401
Response: {"detail": {"demo_mode_write_block": true, ...}}

login demo@example.com → token eyJ...

PATCH /properties/{id} (with token) → 200
Response: {id: "...", tags: ["verified"], updated_at: "..."}
```

**Paste in PR:** `artifacts/pr_evidence/auth_flip_summary.txt`

**Status:** [ ] PASS / [ ] FAIL

---

### Gate 3: Write Guard Default
**Required Evidence:**
```
POST /leads (no token) → 401 or 403
Response: {"detail": {"demo_mode_write_block": true, ...}}
```

**Paste in PR:** `artifacts/pr_evidence/write_guard_test.txt`

**Status:** [ ] PASS / [ ] FAIL

---

### Gate 4: CORS Preflight
**Required Evidence:**
```
OPTIONS /properties
Headers include:
  Access-Control-Allow-Origin: http://localhost:3000
  Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE
  Access-Control-Allow-Headers: Content-Type, Authorization
```

**Paste in PR:** First 5 lines of `artifacts/pr_evidence/cors_preflight.txt`

**Status:** [ ] PASS / [ ] FAIL

---

### Gate 5: SSE Headless
**Required Evidence:**
```
12:03:10 stream open
12:03:11 emit property_updated id=test-123
12:03:11 receive (stream contains 1+ events)
```

**Paste in PR:** `artifacts/pr_evidence/sse_timestamps.txt`

**Status:** [ ] PASS / [ ] FAIL

---

## MUST-PASS GATES (Frontend)

### Gate 6: Auth Banner Appears
**Manual Test:**
1. Open http://localhost:3000/auth/login
2. Login: demo@example.com / demo123
3. F12 → Console tab

**Required Evidence (screenshot):**
```
🔐 AUTH: Demo token attached
  {user: "demo@example.com", tokenPrefix: "eyJ...", requestsWillIncludeAuth: true}
```

**Status:** [ ] SCREENSHOT CAPTURED / [ ] NOT DONE

---

### Gate 7: SSE Badge Shows Connected
**Manual Test:**
1. Navigate to http://localhost:3000/dashboard
2. Check header (top-right, next to bell icon)
3. F12 → Console tab

**Required Evidence:**
- Screenshot: Badge showing "🟢 Connected"
- Console log: "[SSE] Connected to real-time event stream"

**Status:** [ ] SCREENSHOT CAPTURED / [ ] NOT DONE

---

### Gate 8: Emit Test Event Works
**Manual Test:**
1. Navigate to http://localhost:3000/dashboard/admin
2. Click purple "Emit Test Event" button (top-right, ⚡ icon)

**Required Evidence:**
- Screenshot: Purple toast showing "Event: property_updated" + ID + timestamp
- Console log: "[Admin] SSE Event received: property_updated {...}"
- Video/GIF (optional): Badge flashing green (600ms pulse)

**Status:** [ ] SCREENSHOT CAPTURED / [ ] NOT DONE

---

### Gate 9: All 6 Pages Load
**Manual Test:**
For each page, verify:
- Page loads without errors
- At least one API request fires (Network tab)
- API returns 200
- Data displays (or empty state shows)
- No red console errors

| Page | URL | API Call | Status | Screenshot |
|------|-----|----------|--------|------------|
| Workflow | /dashboard/workflow | GET /workflow/smart-lists | [ ] 200 | [ ] Captured |
| Automation | /dashboard/automation | GET /automation/cadence-rules | [ ] 200 | [ ] Captured |
| Leads | /dashboard/leads | GET /leads | [ ] 200 | [ ] Captured |
| Deals | /dashboard/deals | GET /deals | [ ] 200 | [ ] Captured |
| Data | /dashboard/data | GET /data-propensity/enrichment/stats | [ ] 200 | [ ] Captured |
| Admin | /dashboard/admin | GET /system/health | [ ] 200 | [ ] Captured |

**Required Evidence:**
- Page walk summary from `artifacts/pr_evidence/page_walk.txt`
- Screenshot of Network tab showing 200 responses
- Screenshot of one page showing data loaded

**Status:** [ ] ALL PAGES PASS / [ ] SOME FAIL

---

### Gate 10: No Console Errors
**Manual Test:**
1. Walk through all 6 pages
2. Check console for red errors

**Required Evidence:**
- Statement: "Checked all 6 pages, zero red console errors"
- OR: List of errors found (with fix plan)

**Status:** [ ] NO ERRORS / [ ] ERRORS FOUND

---

## NICE-TO-HAVE (CI/CD)

### Gate 11: CI Passes
**Command:**
```bash
gh workflow run runtime-verification.yml --ref claude/audit-wiring-readiness-014VYQdX46CD1u2s6KGWqbGw
```

**Required Evidence:**
```
| Job | Status | Duration |
|-----|--------|----------|
| verify-platform | ✅ | 2m 15s |
| lint-and-test | ✅ | 1m 45s |
| frontend-build | ✅ | 3m 10s |
| security-scan | ✅ | 1m 20s |
```

**Paste in PR:** GitHub Actions run URL + job matrix

**Status:** [ ] ALL GREEN / [ ] SOME RED / [ ] NOT RUN

---

## PR SUBMISSION CHECKLIST

**Before creating PR:**

**Evidence Collected:**
- [ ] Ran `./COLLECT_PR_EVIDENCE.sh` successfully
- [ ] All artifacts exist in `artifacts/pr_evidence/`
- [ ] Captured 5+ screenshots (auth log, badge, toast, pages, console)
- [ ] Triggered CI workflow (optional but recommended)

**Gates Passed:**
- [ ] Gate 1: OpenAPI parity (140+ paths)
- [ ] Gate 2: Auth flip (401 → 200)
- [ ] Gate 3: Write guard (401/403 without token)
- [ ] Gate 4: CORS preflight (headers present)
- [ ] Gate 5: SSE headless (event received)
- [ ] Gate 6: Auth banner (console log captured)
- [ ] Gate 7: SSE badge (Connected screenshot)
- [ ] Gate 8: Emit test event (toast screenshot)
- [ ] Gate 9: All 6 pages load (200 responses)
- [ ] Gate 10: No console errors

**PR Description Contains:**
- [ ] OpenAPI summary block (JSON)
- [ ] Auth flip proof (4 lines)
- [ ] Write guard proof (HTTP 403)
- [ ] SSE timestamps (3 lines)
- [ ] Page walk (6 bullets)
- [ ] Screenshot: Auth token log
- [ ] Screenshot: SSE badge connected
- [ ] Screenshot: Toast notification
- [ ] Screenshot: Console event logs
- [ ] CI run URL (if available)

---

## WHAT TO PASTE IN PR

### Block 1: OpenAPI Summary
````json
{
  "paths": 142,
  "tags": ["auth", "properties", "workflow", "automation", "data", "system", ...],
  "first_three_paths": ["/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/properties"]
}
````

### Block 2: Auth Flip
````
PATCH /api/v1/properties/abc123 (no token) → 401
Response: {"detail": ...}

login demo@example.com → token eyJ...

PATCH /api/v1/properties/abc123 (with token) → 200
Response: {id: "abc123", tags: ["verified"], updated_at: "2025-11-14T..."}
````

### Block 3: SSE Timestamps
````
12:03:10 stream open
12:03:11 emit property_updated id=test-1731610991
12:03:11 receive (stream contains 1 events)
````

### Block 4: Page Walk
````
- Workflow: GET /api/v1/workflow/smart-lists → 200 → fields: [id, name, criteria]
- Automation: GET /api/v1/automation/cadence-rules → 200 → fields: [id, name, enabled]
- Leads: GET /api/v1/leads → 200 → fields: [id, name, email]
- Deals: GET /api/v1/deals → 200 → fields: [id, property_id, status]
- Data: GET /api/v1/data-propensity/enrichment/stats → 200 → fields: [total_properties, enriched]
- Admin: System health dashboard with Emit Test Event button
````

### Block 5: Screenshots
````
![Auth Token Log](path/to/screenshot1.png)
![SSE Badge Connected](path/to/screenshot2.png)
![Toast Notification](path/to/screenshot3.png)
![Console Event Logs](path/to/screenshot4.png)
````

---

## RED FLAGS (DO NOT MERGE IF PRESENT)

**Backend:**
- ❌ OpenAPI returns < 140 paths
- ❌ Auth flip shows 200 without token (no auth enforcement)
- ❌ Write guard allows 200/201 without token (public writes)
- ❌ CORS missing (frontend will fail)
- ❌ SSE stream fails to connect or receive events

**Frontend:**
- ❌ Console shows red errors on any page
- ❌ Auth token log never appears
- ❌ SSE badge stuck on "Live" (never connects)
- ❌ "Emit Test Event" button missing or broken
- ❌ Toast never appears when button clicked
- ❌ Any page returns 404 or 500

**CI/CD:**
- ❌ Any job fails (red ✗)
- ❌ Build fails
- ❌ Tests fail

---

## APPROVAL CRITERIA

**Minimum for merge:**
- ✅ Gates 1-5 PASS (backend must-pass)
- ✅ Gates 6-10 PASS (frontend must-pass)
- ✅ All evidence pasted in PR
- ✅ No red flags present

**Ideal state:**
- ✅ Gates 1-11 PASS (including CI)
- ✅ All screenshots captured
- ✅ Video/GIF of badge flash

---

## IF GATES FAIL

**Do NOT merge. Instead:**

1. Document which gate failed
2. Capture error logs/screenshots
3. Debug locally
4. Fix the issue
5. Re-run `./COLLECT_PR_EVIDENCE.sh`
6. Re-check gates
7. Update PR with new evidence

**Do not claim "demo-ready" until all gates pass.**

---

## FINAL VERIFICATION COMMAND

```bash
# Start services
docker-compose up -d

# Wait 30s for services to be ready
sleep 30

# Collect all evidence
./COLLECT_PR_EVIDENCE.sh

# Check output - should end with:
# "✓ Evidence collection complete!"

# If any errors, fix and re-run
```

**Expected artifacts:**
```
artifacts/pr_evidence/
├── openapi.json
├── openapi_summary.json
├── auth_flip_summary.txt
├── login_response.json
├── patch_no_token.txt
├── patch_with_token.txt
├── write_guard_test.txt
├── emit_response.txt
├── sse_stream.txt
├── sse_timestamps.txt
├── page_walk.txt
└── cors_preflight.txt
```

**If all exist and gates pass:** Ready to create PR

**If any missing or gates fail:** Fix issues before PR

---

**Status:** [ ] READY FOR PR / [ ] NOT READY (missing evidence)

**Evidence Completeness:** ___/11 gates passed

**Last Verification:** [Date] [Time]

