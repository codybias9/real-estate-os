# Real Estate OS - Demo Readiness Implementation Plan

**Branch**: `claude/audit-wiring-readiness-014VYQdX46CD1u2s6KGWqbGw`
**Base**: `origin/claude/review-continue-conversation-011CUxutGDfzr2gDmqgZ22uz`
**Goal**: Transform platform from 85% wired to 100% demo-ready with all features accessible

---

## PHASE 0: Recon & Baseline ✅

**Status**: Complete
**Files Reviewed**:
- Repository structure and branch state
- All 17 API routers (139 endpoints)
- All 10 frontend routes
- Docker Compose configurations
- CI/CD workflows

**Findings**:
- ✅ Auth, Properties, Templates, Pipeline functional
- ❌ Communications broken (missing quick_wins router)
- ❌ Portfolio broken (path mismatch)
- ⚠️ 90/139 endpoints unused (no UI)
- ⚠️ Only 3 mock properties (thin seed data)

---

## PHASE 1: Demo Blockers & Wiring Gaps (~4 hours)

**Objective**: Fix all issues preventing current UI from working

### 1.1 Quick-Wins Communications Endpoint
**Files**:
- `api/routers/quick_wins.py` (NEW)
- `api/main.py` (register router)

**Implementation**:
- Endpoint: `POST /api/v1/quick-wins/generate-and-send`
- Request: `{property_id, template_id}`
- Response: `{memo_content, sent_at, recipient_email, status, ...}`
- Logic:
  - Fetch property from MOCK_PROPERTIES
  - Fetch template from TEMPLATES
  - Simple variable substitution ({{property_address}}, {{owner_name}}, etc.)
  - Return mock "sent" status

**Acceptance**:
- `/dashboard/communications` → select property + template → "Generate & Send" succeeds
- No 404 errors in console
- Success toast displays

### 1.2 Portfolio Metrics Path Alias
**Files**:
- `api/routers/portfolio.py` (add GET /metrics endpoint)

**Implementation**:
- Add route alias: `@router.get("/metrics", response_model=PortfolioSummary)`
- Reuse existing `/summary` implementation
- Ensure both paths return identical data

**Acceptance**:
- `/dashboard/portfolio` loads without errors
- Metrics display: Total Deal Value, Avg Deal Size, Win Rate, etc.

### 1.3 Dashboard Metrics from API
**Files**:
- `frontend/src/lib/api.ts` (add analytics.getDashboard method)
- `frontend/src/app/dashboard/page.tsx` (fetch from API)
- `api/routers/analytics.py` (verify /dashboard endpoint)

**Implementation**:
- Verify `GET /api/v1/analytics/dashboard` exists and returns DashboardMetrics
- Add API client method if missing
- Update dashboard page to fetch both getPipelineStats and getDashboard
- Replace hardcoded `response_rate: 0.34` and `avg_days_in_pipeline: 12`

**Acceptance**:
- Dashboard shows metrics from API, not hardcoded values
- Changing backend mock data reflects in UI

### 1.4 Enhanced Seed Data (20+ Properties)
**Files**:
- `api/routers/properties.py` (expand MOCK_PROPERTIES)

**Implementation**:
- Create 20-25 properties across:
  - Stages: new (5), outreach (7), qualified (4), negotiation (2), under_contract (1), closed_won (1)
  - Cities: San Francisco, Oakland, San Jose, Berkeley, Palo Alto
  - Price range: $650k - $3.5M
- Include all frontend-expected fields:
  - `owner_name`, `bird_dog_score`, `current_stage`, `tags`, `last_contact_at`, `memo_generated_at`
- Ensure consistency: GET /properties and /stats/pipeline use same data

**Acceptance**:
- `/dashboard` shows meaningful stage breakdown (not 1-1-1)
- `/dashboard/pipeline` Kanban has 5+ cards in multiple columns
- Properties feel realistic (varied owners, locations, equity levels)

---

## PHASE 2: Template & Property UX Polish (~10 hours)

**Objective**: Complete CRUD flows for existing features

### 2.1 Template Create/Edit Wiring
**Files**:
- `frontend/src/components/TemplateForm.tsx` (NEW)
- `frontend/src/app/dashboard/templates/page.tsx` (wire handlers)

**Implementation**:
- Create TemplateForm component using react-hook-form + zod
- Fields: name, channel (email/sms), category, subject, body, tags
- Wire "New Template" button → open modal
- Wire "Edit" icon → open modal with pre-filled data
- Submit calls `apiClient.templates.create` or `.update`
- Refresh list on success

**Acceptance**:
- Click "New Template" → fill form → save → appears in grid
- Click "Edit" on existing → modify → save → updates in grid
- Delete button works (with confirmation)

### 2.2 Property Drawer Enhancement
**Files**:
- `frontend/src/components/PropertyDrawer.tsx` (enhance)
- Wire to: `/properties/{id}/timeline`, `/data-propensity/properties/{id}/signals`, `/data-propensity/properties/{id}/provenance`

**Implementation**:
- Add tabs: Overview, Timeline, Data Signals, Provenance
- Timeline tab: fetch and display activity events
- Signals tab: show high_equity, owner_occupied, etc. with strength/confidence
- Provenance tab: show data sources and freshness for key fields

**Acceptance**:
- Open property drawer from Pipeline → see all tabs populated
- Signals show realistic strengths (0.85 for high_equity, etc.)
- Provenance shows county_assessor, MLS, skip_trace sources

---

## PHASE 3: Wiring Missing Feature Groups (~40 hours)

**Objective**: Build minimal UIs for backend-only routers

### 3.1 Workflow - Smart Lists & Next-Best-Actions
**Files**:
- `frontend/src/app/dashboard/workflow/page.tsx` (NEW)
- Wire to: `/workflow/smart-lists`, `/workflow/next-best-actions`

**UI Sections**:
- Smart Lists table (name, criteria summary, property count)
- Click list → show matching properties
- Next-Best-Actions panel (recommended actions with Complete/Dismiss)

### 3.2 Automation - Cadence Rules & Compliance
**Files**:
- `frontend/src/app/dashboard/automation/page.tsx` (NEW)
- Wire to: `/automation/cadence-rules`, `/automation/compliance/*`

**UI Sections**:
- Cadence Rules table (name, trigger, steps, active toggle, stats)
- Compliance Check form (validate phone/email for DNC/consent)

### 3.3 Sharing - Share Links & Deal Rooms
**Files**:
- `frontend/src/app/dashboard/sharing/page.tsx` (NEW)
- Wire to: `/sharing/share-links`, `/sharing/deal-rooms`

**UI Sections**:
- Share Links: list with views/clicks, create/revoke actions
- Deal Rooms: list with participants/artifacts, detail view

### 3.4 Leads & Deals
**Files**:
- `frontend/src/app/dashboard/leads/page.tsx` (NEW)
- `frontend/src/app/dashboard/deals/page.tsx` (NEW)

**UI**:
- Leads: table with source, status, activities
- Deals: table with stage, value, linked property

### 3.5 Data & Propensity Overview
**Files**:
- `frontend/src/app/dashboard/data/page.tsx` (NEW)
- Wire to: `/data-propensity/*`

**UI**:
- Aggregate signals view (top signals across portfolio)
- Enrichment stats (count enriched, success rate)

### 3.6 Jobs & Admin Status
**Files**:
- `frontend/src/app/dashboard/admin/page.tsx` (NEW)
- Tabs: Jobs, Provider Status, System Health

**UI**:
- Jobs: active jobs table with retry/cancel
- Provider Status: Twilio/SendGrid/etc. health
- System Health: metrics from /system

### 3.7 Pipelines (Optional Airflow UI)
**Files**:
- `frontend/src/app/dashboard/pipelines/page.tsx` (NEW)
- Wire to: `/pipelines/dags`

**UI**:
- DAGs table with status, last run, trigger/pause actions

---

## PHASE 4: SSE & Real-Time Behavior (~3 hours)

**Objective**: Make SSE emit real events on state changes

**Files**:
- `api/routers/sse_events.py` (add active_connections dict)
- `api/routers/properties.py` (emit on PATCH /{id})
- `api/routers/communications.py` (emit on send)

**Implementation**:
- In sse_events.py: maintain `active_connections: dict[str, asyncio.Queue]`
- GET /stream: create queue, stream events, cleanup on disconnect
- On property update: enqueue `{type: "property_updated", data: {...}}` to all queues
- Frontend useSSE: confirm event handling triggers refresh

**Acceptance**:
- Two browser tabs on /dashboard/pipeline
- Drag property in tab A → tab B updates within 2 seconds (no manual refresh)

---

## PHASE 5: Auth & Platform Hardening (~4 hours)

**Objective**: Coherent auth story for demo (not production-grade)

### 5.1 Auth Enforcement
**Files**:
- `api/auth_utils.py` (add get_current_user dependency)
- All business routers (add Depends(get_current_user))

**Implementation**:
- Parse Authorization: Bearer {token} header
- In MOCK_MODE: accept any valid-looking token, look up user in DB
- Apply to: properties, leads, deals, templates, workflow, automation, sharing, etc.
- Return 401 if token missing/invalid

**Acceptance**:
- API calls without token → 401
- Frontend with valid token → all endpoints work

### 5.2 Multi-Tenant Isolation (Mock-Level)
**Files**:
- All routers returning lists (properties, templates, etc.)

**Implementation**:
- Filter mock data by team_id where applicable
- Ensure distinct teams don't see each other's data in mock responses

**Acceptance**:
- Register two users (different teams)
- User A sees different properties than User B

### 5.3 Error Handling
**Files**:
- `frontend/src/lib/api-client.ts` (improve error interceptor)

**Implementation**:
- Better error messages for 4xx/5xx
- Toast notifications for common errors
- Prevent double-submit on key actions

---

## PHASE 6: CI/Runtime Verification (~2 hours)

**Objective**: Catch regressions automatically

**Files**:
- `.github/workflows/runtime-verification.yml` (enhance)

**Implementation**:
- Add pytest run (if tests exist)
- Add `npm run build` and `npm run lint` for frontend
- Add basic E2E check: register user, login, fetch properties

**Acceptance**:
- CI workflow passes on this branch
- Breaking a wired endpoint causes CI to fail

---

## Success Criteria (All Phases)

### Functional Requirements
- ✅ All 10 frontend routes load without errors
- ✅ All visible UI actions either work or are clearly disabled
- ✅ 15-minute demo script runs 3x without failures
- ✅ SSE shows real-time updates across browser tabs
- ✅ Auth enforced on all business endpoints

### Data Quality
- ✅ 20+ properties with realistic distribution across stages
- ✅ 5+ templates with proper variable substitution
- ✅ Mock data feels coherent (not random/contradictory)

### CI/CD
- ✅ Runtime verification builds API and Frontend
- ✅ Endpoint count check passes (~139 endpoints)
- ✅ Basic E2E smoke test passes

---

## Execution Order

1. **IMMEDIATE** (Phase 1): Fix 4 demo blockers → enables basic demo
2. **THIS WEEK** (Phase 2): Polish Templates + Property Drawer → professional feel
3. **NEXT WEEK** (Phase 3): Wire 7 missing feature UIs → complete platform showcase
4. **FINAL PASS** (Phases 4-6): Real-time + Auth + CI → production-ready demo

**Estimated Total**: 60-70 hours for complete implementation

---

## File Inventory by Phase

### Phase 1 (4 files modified, 1 new)
- NEW: `api/routers/quick_wins.py`
- MODIFY: `api/main.py`, `api/routers/portfolio.py`, `api/routers/properties.py`
- MODIFY: `frontend/src/lib/api.ts`, `frontend/src/app/dashboard/page.tsx`

### Phase 2 (2 files modified, 1 new)
- NEW: `frontend/src/components/TemplateForm.tsx`
- MODIFY: `frontend/src/app/dashboard/templates/page.tsx`
- MODIFY: `frontend/src/components/PropertyDrawer.tsx`

### Phase 3 (7 new pages)
- NEW: `frontend/src/app/dashboard/workflow/page.tsx`
- NEW: `frontend/src/app/dashboard/automation/page.tsx`
- NEW: `frontend/src/app/dashboard/sharing/page.tsx`
- NEW: `frontend/src/app/dashboard/leads/page.tsx`
- NEW: `frontend/src/app/dashboard/deals/page.tsx`
- NEW: `frontend/src/app/dashboard/data/page.tsx`
- NEW: `frontend/src/app/dashboard/admin/page.tsx`
- NEW: `frontend/src/app/dashboard/pipelines/page.tsx` (optional)

### Phase 4 (3 files modified)
- MODIFY: `api/routers/sse_events.py`
- MODIFY: `api/routers/properties.py`
- MODIFY: `api/routers/communications.py`

### Phase 5 (18 files modified)
- MODIFY: `api/auth_utils.py`
- MODIFY: All 17 routers (add auth dependency)

### Phase 6 (1 file modified)
- MODIFY: `.github/workflows/runtime-verification.yml`

**Total Impact**: ~35 files modified/created across 6 phases
