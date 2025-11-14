# Verification Quickstart

This guide helps you run the complete runtime verification and collect evidence for the pull request.

## Prerequisites

- Docker Desktop is running
- You're in the repository root directory
- You have Python 3 installed (for parsing JSON)

## Quick Start

### For Linux/macOS/Git Bash (Recommended)

```bash
# Run the comprehensive verification script
./RUN_ALL_VERIFICATION.sh
```

### For Windows PowerShell

```powershell
# Run the PowerShell verification script
.\RUN_ALL_VERIFICATION.ps1
```

## What the Script Does

The verification script runs 8 phases automatically:

### Phase A: Repository Setup
- Locates repository root
- Verifies correct branch (`claude/audit-wiring-readiness-014VYQdX46CD1u2s6KGWqbGw`)
- Creates `artifacts/pr_evidence/` directory
- Captures commit SHA and branch name

### Phase B: Service Health
- Starts Docker services with `docker compose up -d`
- Waits for API to become healthy (up to 2 minutes)
- Confirms API is responding on `http://localhost:8000`

### Phase C: OpenAPI Verification
- Downloads OpenAPI spec from `/openapi.json`
- Counts endpoints (should be ≥140)
- Verifies tags: workflow, automation, data, system
- Saves summary to `openapi_summary.json`

### Phase D: Auth Testing
- **Test 1**: PATCH without token → Expect 401/403 (write guard blocks)
- **Test 2**: Login with demo credentials → Get auth token
- **Test 3**: PATCH with token → Expect 200/204 (auth works)
- Saves all responses and status codes

### Phase E: CORS Verification
- Sends OPTIONS preflight request
- Sends GET request with Origin header
- Verifies `Access-Control-Allow-Origin` header present
- Saves all headers

### Phase F: SSE End-to-End Test
- Opens SSE stream connection in background
- Emits test event via POST `/sse/test/emit`
- Captures received events in stream
- Verifies event was received within timeout
- Saves captured stream data

### Phase G: Page Walk (API Layer)
- Tests API endpoints used by all 6 dashboard pages:
  - `/api/v1/workflow/smart-lists` (Workflow page)
  - `/api/v1/automation/cadence-rules` (Automation page)
  - `/api/v1/leads` (Leads page)
  - `/api/v1/deals` (Deals page)
  - `/api/v1/data/summary` (Data page)
  - `/api/v1/system/health` (Admin page)
- Captures all status codes

### Phase H: Gate Evaluation
- Evaluates 5 backend gates (G1-G5)
- Generates `PR_BODY.md` with all evidence
- Creates `gates_summary.txt` with pass/fail results

## Output Files

All artifacts are saved to: `artifacts/pr_evidence/`

| File | Description |
|------|-------------|
| `repo_root.txt` | Repository root path |
| `branch.txt` | Current branch name |
| `commit_sha.txt` | Current commit SHA |
| `wait_api.log` | API health check log |
| `openapi.json` | Complete OpenAPI specification |
| `openapi_summary.json` | Endpoint count and tags |
| `auth_flip_summary.txt` | Auth test results (401→200) |
| `login.json` | Login response with token |
| `token.txt` | Extracted auth token |
| `patch_no_token.json` | PATCH response without auth |
| `patch_with_token.json` | PATCH response with auth |
| `cors_preflight_headers.txt` | OPTIONS request headers |
| `cors_get_headers.txt` | GET request headers with CORS |
| `cors_get_body.json` | Response body |
| `sse_stream.jsonl` | Captured SSE events |
| `sse_stream_head.txt` | First 10 lines of stream |
| `sse_emit_resp.json` | Emit endpoint response |
| `sse_emit_code.txt` | Emit status code |
| `page_walk.txt` | All page API endpoint results |
| `gates_summary.txt` | Gate pass/fail summary |
| **`PR_BODY.md`** | **Complete PR description with evidence** |

## Gate Results

The script evaluates 5 backend gates:

| Gate | Criteria | Pass Condition |
|------|----------|----------------|
| **G1** | OpenAPI coverage | ≥140 paths + workflow/automation/data/system tags |
| **G2** | Auth flip | 401/403 without token, 200/204 with token |
| **G3** | Write guard | 401/403 blocks unauthenticated writes |
| **G4** | CORS headers | `Access-Control-Allow-Origin` present |
| **G5** | SSE stream | Event emitted and received |

**Expected Result**: All 5 gates should **PASS**

## Browser-Based Verification (Manual)

After the script completes, you need to verify 4 things in the browser:

### Step 1: Auth Token Console Log

1. Open: http://localhost:3000/auth/login
2. Login with:
   - Email: `demo@example.com`
   - Password: `demo123`
3. Press **F12** → **Console** tab
4. **Look for**: `🔐 AUTH: Demo token attached` (green styled log)

✅ **PASS**: Green console log appears
❌ **FAIL**: No log or "🔓 No token found"

### Step 2: SSE Connection Badge

1. Navigate to: http://localhost:3000/dashboard
2. Look at **top-right corner** of header (next to bell icon 🔔)
3. **Look for**: Badge showing **🟢 Connected** (green dot)
4. **Console should show**: `[SSE] Connected to real-time event stream`

✅ **PASS**: Badge shows green dot + "Connected"
❌ **FAIL**: Badge shows gray dot + "Live" or missing

### Step 3: SSE Event + Toast Test

1. Navigate to: http://localhost:3000/dashboard/admin
2. Find purple **"Emit Test Event"** button (⚡ icon)
3. Click the button
4. **Watch for 3 things**:
   - **SSE Badge flashes green** (pulse animation ~600ms)
   - **Purple toast appears** top-right: "Event: property_updated"
   - **Console logs**: `[Admin] SSE Event received: property_updated`

✅ **PASS**: All 3 happen (badge flash + toast + console log)
❌ **FAIL**: Any missing

### Step 4: Page Walk (All Pages Load)

Visit each page and verify no console errors:

1. http://localhost:3000/dashboard/workflow - Smart Lists
2. http://localhost:3000/dashboard/automation - Cadence Rules
3. http://localhost:3000/dashboard/leads - Leads table
4. http://localhost:3000/dashboard/deals - Deals pipeline
5. http://localhost:3000/dashboard/data - Enrichment stats
6. http://localhost:3000/dashboard/admin - System metrics

For each page:
- **F12** → **Console** tab
- **Look for**: NO red errors
- **Network tab**: API calls return `200 OK`

✅ **PASS**: All 6 pages load with no console errors
❌ **FAIL**: Any page has red errors

## Screenshots Needed

Capture these 4 screenshots:

1. **auth_console_log.png** - Console showing green auth banner after login
2. **sse_badge_connected.png** - Dashboard header showing green "Connected" badge
3. **toast_notification.png** - Toast appearing after clicking "Emit Test Event"
4. **pages_no_errors.png** - Console showing no errors on any page

## Final Steps

### 1. Review Generated PR Body

```bash
cat artifacts/pr_evidence/PR_BODY.md
```

This file contains:
- All gate results (PASS/FAIL)
- OpenAPI summary
- Auth flip evidence
- SSE stream capture
- Page walk results
- Browser verification checklist

### 2. Verify All Gates Passed

```bash
cat artifacts/pr_evidence/gates_summary.txt
```

**Expected Output**:
```
G1 OpenAPI/tag coverage: PASS (paths=142, workflow=true, automation=true, data=true, system=true)
G2 Auth flip 401→200: PASS (no_token=401, with_token=200)
G3 Write guard unauth write blocked: PASS (no_token=401)
G4 CORS headers present: PASS
G5 SSE emit→receive: PASS
```

### 3. Paste Evidence into Pull Request

1. Create pull request on GitHub
2. Copy contents of `artifacts/pr_evidence/PR_BODY.md`
3. Paste into PR description
4. Attach 4 screenshots
5. Check all browser verification boxes

### 4. Commit and Push

```bash
git add .
git commit -m "docs: Add comprehensive runtime verification scripts and evidence"
git push -u origin claude/audit-wiring-readiness-014VYQdX46CD1u2s6KGWqbGw
```

## Troubleshooting

### API Not Healthy

```bash
# Check logs
docker compose logs api

# Restart services
docker compose down
docker compose up -d
```

### SSE Stream Not Captured

- Ensure API is running
- Check SSE endpoint exists: `curl http://localhost:8000/api/v1/sse/test/emit`
- Verify SSE stream endpoint: `curl -N http://localhost:8000/api/v1/sse/stream`

### Auth Token Not Obtained

- Verify demo user exists in database
- Check login endpoint: `curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"demo@example.com","password":"demo123"}'`

### Frontend Not Loading

```bash
# Check frontend service
docker compose logs frontend

# Restart frontend
docker compose restart frontend
```

## Success Criteria

**Backend (Automated)**: All 5 gates (G1-G5) show **PASS** in `gates_summary.txt`

**Frontend (Manual)**: All 4 browser checks pass:
- ✅ Auth token console log appears
- ✅ SSE badge shows "Connected"
- ✅ Toast notification works
- ✅ All 6 pages load without errors

**Evidence Ready**: `PR_BODY.md` generated + 4 screenshots captured

---

**Platform is DEMO-READY when all criteria met!** 🎉
