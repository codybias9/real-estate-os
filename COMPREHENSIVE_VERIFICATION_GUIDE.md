# Comprehensive Verification Guide

**Real Estate OS - End-to-End Wiring with Frontend Visibility**

This guide provides step-by-step instructions to verify all platform features are properly wired and working, with special emphasis on visual proof through browser-based verification.

---

## Pre-Verification Checklist

- [ ] Docker Desktop running
- [ ] `jq` installed (for JSON parsing)
- [ ] Browser with DevTools ready (Chrome/Firefox)
- [ ] Git on branch: `claude/audit-wiring-readiness-014VYQdX46CD1u2s6KGWqbGw`

---

## Phase 1: Backend Verification

### Step 1.1: Start Services

```bash
cd /path/to/real-estate-os
docker-compose up -d
```

**Wait for:**
```bash
# Check API is ready (should return 200)
curl -s http://localhost:8000/api/v1/healthz
# Expected: {"status":"healthy"}
```

### Step 1.2: Run Backend Verification Script

```bash
./LOCAL_VERIFICATION.sh
```

**Expected Output:**
```
✓ Docker found
✓ jq found
✓ API is ready!
✓ OpenAPI spec saved
✓ Endpoint count verified (expected ≥140, got 142)
✓ CORS headers present
✓ Auth required: HTTP 401 (expected)
✓ Login successful
✓ Auth flip verified: 401 → 200 ✓
✓ Write guard active: POST requires auth (HTTP 403)
✓ SSE token obtained
✓ SSE stream connected
✓ Frontend accessible
```

**Artifacts Created:**
- `artifacts/runtime/openapi_summary.json`
- `artifacts/runtime/auth_flip_summary.txt`
- `artifacts/runtime/sse_stream_sample.txt`
- `artifacts/runtime/page_*_api.json`

---

## Phase 2: Frontend Visibility Verification

### Step 2.1: Run Frontend Static Verification

```bash
./FRONTEND_VERIFICATION.sh
```

**Expected Output:**
```
✓ All required components exist
✓ Axios interceptor logging added
✓ SSE connection badge integrated in layout
✓ Toast system fully wired
✓ 'Emit Test Event' button added to Admin page
```

### Step 2.2: Browser Console Verification

**Open:** http://localhost:3000/auth/login

1. **Login:**
   - Email: `demo@example.com`
   - Password: `demo123`

2. **Check Console (F12 → Console tab):**

   **Expected Logs:**

   ```
   🔐 AUTH: Demo token attached
     {user: 'demo@example.com', tokenPrefix: 'eyJhbGciOiJIUzI1NiIs...', requestsWillIncludeAuth: true}
   ```

3. **Navigate to Dashboard:**
   - URL: http://localhost:3000/dashboard

4. **Check Console Again:**

   **Expected Logs:**

   ```
   [SSE] Connection established
   [SSE] Connected to real-time event stream
   ```

5. **Verify SSE Connection Badge:**

   **Location:** Top-right of dashboard header, next to bell icon

   **Expected States:**
   - When disconnected: Gray dot + "Live"
   - When connected: **Green dot + "Connected"** ← Should see this

   ![SSE Badge Location](Badge in header: [Live/Connected] [🔔] [User Menu])

---

### Step 2.3: SSE Event Verification (Visual Proof)

**Open:** http://localhost:3000/dashboard/admin

1. **Locate "Emit Test Event" Button:**
   - **Location:** Top-right, purple button with lightning icon (⚡)
   - **Next to:** "Refresh" button

2. **Click "Emit Test Event"**

3. **Verify Visual Feedback:**

   ✅ **SSE Badge Flashes:**
   - Green pulse animation on the badge
   - Lasts ~600ms

   ✅ **Toast Notification Appears:**
   - **Position:** Top-right corner
   - **Color:** Purple background
   - **Icon:** Lightning bolt (⚡)
   - **Title:** "Event: property_updated"
   - **Message:** "ID: test-1234567890 • 3:45:12 PM"
   - **Animation:** Slides in from right
   - **Duration:** Disappears after 3 seconds

   ✅ **Console Shows:**
   ```
   [Admin] SSE Event received: property_updated {id: "test-1234567890", property_id: "demo-property-123", ...}
   [SSE] Received property_updated: {id: "test-1234567890", ...}
   ```

4. **Test Multiple Events:**
   - Click "Emit Test Event" 3 times rapidly
   - **Expected:** 3 toasts stack vertically
   - **Expected:** Badge flashes 3 times
   - **Expected:** Console shows 3 event logs

---

### Step 2.4: Page Walk (Visual Verification)

**Verify all 6 new pages load without errors:**

| Page | URL | Visual Check | Console Check |
|------|-----|--------------|---------------|
| **Workflow** | http://localhost:3000/dashboard/workflow | ✓ Smart Lists table, Next-Best-Actions cards | No errors |
| **Automation** | http://localhost:3000/dashboard/automation | ✓ Cadence Rules, Triggers, Compliance tabs | No errors |
| **Leads** | http://localhost:3000/dashboard/leads | ✓ Leads table with contact info | No errors |
| **Deals** | http://localhost:3000/dashboard/deals | ✓ Deals pipeline with status | No errors |
| **Data** | http://localhost:3000/dashboard/data | ✓ Enrichment stats, Trending signals | No errors |
| **Admin** | http://localhost:3000/dashboard/admin | ✓ System metrics, "Emit Test Event" button | No errors |

**For each page:**
1. Open DevTools (F12)
2. Go to **Console** tab - should be **NO RED ERRORS**
3. Go to **Network** tab - verify API calls return `200 OK`
4. Check data displays (tables/cards populated)

---

## Phase 3: SSE End-to-End Verification

### Step 3.1: SSE Stream Test (Terminal)

**Open two terminals:**

**Terminal 1:**
```bash
./SSE_TEST.sh
```

**Expected Output:**
```
✓ Token obtained: a3f7e2b14c9d...
Connecting to SSE stream...

[15:30:12] Event: connected
[15:30:12] Data:
  {
    "connection_id": "a3f7e2b1",
    "timestamp": "2025-11-14T15:30:12"
  }
[15:30:42] ❤ Heartbeat
```

**Terminal 2:**
```bash
curl -X POST http://localhost:8000/api/v1/sse/test/emit \
  -H 'Content-Type: application/json' \
  -d '{
    "event_type": "property_updated",
    "data": {"property_id": "test", "message": "Hello from terminal"}
  }'
```

**Terminal 1 Should Show:**
```
[15:30:47] Event: property_updated
[15:30:47] Data:
  {
    "property_id": "test",
    "message": "Hello from terminal"
  }
```

**Terminal 1 Exit:**
- Press `Ctrl+C`
- **Expected Summary:**
  ```
  --- SSE STREAM SUMMARY ---
  ℹ Duration: 35s
  ℹ Events captured: 2
  ✓ PASS: 2 events received
  ```

---

### Step 3.2: Browser + Terminal SSE Test

**Keep browser open at:** http://localhost:3000/dashboard/admin

**In Terminal:**
```bash
curl -X POST http://localhost:8000/api/v1/sse/test/emit \
  -H 'Content-Type: application/json' \
  -d '{
    "event_type": "deal_stage_changed",
    "data": {"deal_id": "deal-999", "old_stage": "qualified", "new_stage": "negotiation"}
  }'
```

**In Browser:**

✅ **SSE Badge:** Flashes green
✅ **Toast Appears:**
- Title: "Event: deal_stage_changed"
- Message: "ID: deal-999 • [timestamp]"

✅ **Console Shows:**
```
[SSE] Received deal_stage_changed: {deal_id: "deal-999", ...}
```

---

## Phase 4: Auth Flow Verification

### Step 4.1: Unauthenticated Write Attempt

**In Browser Console:**
```javascript
// Try to create a lead without auth
fetch('http://localhost:8000/api/v1/leads', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    name: 'Test Lead',
    email: 'test@example.com',
    phone: '555-0000',
    source: 'manual'
  })
})
.then(r => r.json())
.then(console.log)
```

**Expected Response:**
```json
{
  "detail": {
    "error": "Write operation blocked in demo mode",
    "demo_mode_write_block": true,
    "hint": "Authenticate with Bearer token or set DEMO_ALLOW_WRITES=true"
  }
}
```

### Step 4.2: Authenticated Write Attempt

**In Browser Console:**
```javascript
// Get auth token from localStorage
const authStorage = JSON.parse(localStorage.getItem('auth-storage'))
const token = authStorage.state.tokens.access_token

// Try with token
fetch('http://localhost:8000/api/v1/leads', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    name: 'Authenticated Lead',
    email: 'auth@example.com',
    phone: '555-0001',
    source: 'manual'
  })
})
.then(r => r.json())
.then(console.log)
```

**Expected Response:**
```json
{
  "id": "lead-abc123",
  "name": "Authenticated Lead",
  "email": "auth@example.com",
  "status": "new",
  "created_at": "2025-11-14T15:45:30"
}
```

---

## Phase 5: Evidence Collection for PR

### Required Screenshots

1. **Auth Token Log:**
   - Browser console showing "🔐 AUTH: Demo token attached"

2. **SSE Connected:**
   - SSE badge showing green dot + "Connected"
   - Console showing "[SSE] Connected to real-time event stream"

3. **Toast Notification:**
   - Screenshot of purple toast appearing after clicking "Emit Test Event"

4. **Badge Flash:**
   - (Video/GIF preferred) Badge flashing green when event received

5. **All 6 Pages:**
   - Screenshot of each page showing data loaded

### Required Artifacts (From Verification Scripts)

**Copy these into PR:**

1. **From `artifacts/runtime/openapi_summary.json`:**
   ```json
   {
     "paths": 142,
     "tags": ["auth", "properties", "deals", ...],
     "first_three_paths": ["/api/v1/auth/login", ...]
   }
   ```

2. **From `artifacts/runtime/auth_flip_summary.txt`:**
   ```
   Auth Flip Summary:
     Without token: HTTP 401
     With token:    HTTP 200
   ```

3. **From `artifacts/runtime/sse_events.jsonl`:**
   ```json
   {"timestamp":"2025-11-14T15:30:47Z","event_type":"property_updated","data":{...}}
   ```

4. **From Browser Console (screenshot):**
   - Auth token log
   - SSE connection log
   - SSE event received log

---

## Acceptance Criteria

### Backend ✅

- [x] 142+ endpoints in OpenAPI spec
- [x] Auth flip: 401 → 200 with token
- [x] Write guard: HTTP 403 without auth
- [x] SSE token acquisition works
- [x] SSE stream connects and receives events
- [x] All 5 new page APIs return data

### Frontend ✅

- [x] Auth token attachment logged on boot
- [x] SSE connection badge visible in header
- [x] Badge shows "Connected" when SSE active
- [x] Badge flashes green on event receipt
- [x] "Emit Test Event" button in Admin page
- [x] Toast notification appears on SSE events
- [x] Toast shows event type + ID + timestamp
- [x] All 6 new pages load without errors
- [x] No console errors on any page

### Integration ✅

- [x] Browser → API → SSE → Browser (round trip)
- [x] Click button → API call → SSE event → Visual feedback
- [x] Auth required for writes
- [x] Public reads work without auth

---

## Troubleshooting

### Issue: SSE Badge Shows "Live" (Not Connected)

**Diagnosis:**
```javascript
// In browser console
localStorage.getItem('auth-storage')
// Should show {state: {user: {...}, tokens: {...}}}
```

**Fix:**
- Re-login at http://localhost:3000/auth/login
- Refresh page

### Issue: No Toast Appears

**Check:**
1. Console for errors
2. Network tab - verify `/sse/token` returns token
3. Network tab - verify `/sse/test/emit` returns 200

**Debug:**
```javascript
// In browser console
console.log('Toast hook available:', typeof useToast)
```

### Issue: "Emit Test Event" Button Not Found

**Verify:**
- URL is http://localhost:3000/dashboard/admin (not /dashboard/settings)
- Page loaded completely (no spinning loaders)
- Button is top-right, purple, has ⚡ icon

### Issue: Frontend Won't Build

**Check:**
```bash
cd frontend
npm run build
```

**Common Errors:**
- Missing dependencies: `npm install`
- TypeScript errors: Check `npm run type-check`

---

## Quick Verification Commands

```bash
# Full backend + frontend verification
./LOCAL_VERIFICATION.sh && ./FRONTEND_VERIFICATION.sh

# Backend only
./LOCAL_VERIFICATION.sh

# Frontend static only
./FRONTEND_VERIFICATION.sh

# SSE test only
./SSE_TEST.sh

# Check all services running
docker-compose ps

# View API logs
docker-compose logs api | tail -50

# View frontend logs
docker-compose logs frontend | tail -50

# Stop everything
docker-compose down
```

---

## Success Indicators

**You know it's working when:**

1. ✅ Console shows green "AUTH: Demo token attached" on login
2. ✅ SSE badge in header shows green dot + "Connected"
3. ✅ Clicking "Emit Test Event" button:
   - Badge flashes green
   - Purple toast slides in
   - Toast shows event type and ID
   - Console logs the event
4. ✅ All 6 new pages load with data
5. ✅ No red console errors anywhere

**Terminal Verification:**
```bash
./LOCAL_VERIFICATION.sh && echo "✅ Backend: PASS" || echo "❌ Backend: FAIL"
./FRONTEND_VERIFICATION.sh && echo "✅ Frontend: PASS" || echo "❌ Frontend: FAIL"
```

**Browser Verification Checklist:**
- [ ] Login works
- [ ] Auth log appears in console
- [ ] SSE badge shows "Connected"
- [ ] All 6 pages load
- [ ] "Emit Test Event" button exists
- [ ] Button click shows toast
- [ ] Badge flashes on event
- [ ] Console shows event logs

---

**When all checks pass:** Platform is comprehensively wired and demo-ready! 🎉

