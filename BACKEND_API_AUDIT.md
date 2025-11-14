# Backend API Audit - Real Estate OS

## ✅ Currently Implemented (7 Routers)

### 1. Auth Router (`/api/v1/auth`)
- ✅ POST `/register` - User registration
- ✅ POST `/login` - User authentication (returns TokenResponse with access_token)
- ✅ GET `/me` - Get current user profile

### 2. Analytics Router (`/api/v1/analytics`)
- ✅ GET `/dashboard` - Business metrics (properties, leads, deals)
- ✅ GET `/pipeline` - Lead pipeline by stage
- ✅ GET `/revenue` - Revenue trends
- ✅ GET `/platform` - **Technical platform metrics** (NEW)
- ✅ GET `/data-quality` - **Data completeness metrics** (NEW)
- ✅ GET `/throughput` - **Processing throughput** (NEW)

### 3. Properties Router (`/api/v1/properties`)
- ✅ GET `/` - List properties with filters
- ✅ GET `/{property_id}` - Get property details
- ✅ POST `/` - Create property
- ✅ PATCH `/{property_id}` - Update property
- ✅ DELETE `/{property_id}` - Delete property
- ✅ GET `/stats/pipeline` - Pipeline statistics

### 4. Leads Router (`/api/v1/leads`)
- ✅ GET `/` - List leads with filters
- ✅ GET `/{lead_id}` - Get lead details
- ✅ POST `/` - Create lead
- ✅ POST `/{lead_id}/activities` - Add activity
- ✅ GET `/{lead_id}/activities` - Get activities

### 5. Deals Router (`/api/v1/deals`)
- ✅ GET `/` - List deals with filters
- ✅ GET `/{deal_id}` - Get deal details
- ✅ POST `/` - Create deal
- ✅ PATCH `/{deal_id}` - Update deal

### 6. Pipelines Router (`/api/v1/pipelines`) **[Technical Platform]**
- ✅ GET `/dags` - List all Airflow DAGs
- ✅ GET `/dags/{dag_id}` - Get DAG details
- ✅ GET `/dags/{dag_id}/runs` - Get DAG run history
- ✅ POST `/dags/{dag_id}/trigger` - Trigger DAG manually
- ✅ POST `/dags/{dag_id}/pause` - Pause DAG
- ✅ POST `/dags/{dag_id}/unpause` - Unpause DAG
- ✅ GET `/metrics` - Pipeline metrics
- ✅ GET `/scraping/jobs` - Scraping job stats
- ✅ GET `/enrichment/jobs` - Enrichment job stats

### 7. System Router (`/api/v1/system`) **[Technical Platform]**
- ✅ GET `/health` - Service health status
- ✅ GET `/workers` - Celery worker info
- ✅ GET `/queues` - Task queue stats
- ✅ GET `/storage` - Storage system info
- ✅ GET `/metrics` - System performance
- ✅ GET `/logs/recent` - Recent logs
- ✅ GET `/errors/recent` - Recent errors

---

## ❌ Missing Routers (9 areas needed for Sales Ops)

### 1. Workflow Router (`/api/v1/workflow`) **MISSING**
Required for Sourcing/Targeting features:
- ❌ GET `/smart-lists` - List all smart lists
- ❌ POST `/smart-lists` - Create smart list
- ❌ GET `/smart-lists/{id}` - Get smart list details
- ❌ GET `/smart-lists/{id}/properties` - Get properties matching smart list
- ❌ POST `/next-best-actions/generate` - Generate NBA for property
- ❌ POST `/next-best-actions/{nba_id}/complete` - Mark NBA as complete

### 2. Data & Propensity Router (`/api/v1/data-propensity`) **MISSING**
Required for Enrichment/Signals:
- ❌ GET `/.../signals` - Get data signals for property
- ❌ POST `/provenance/update-source` - Update data source info

### 3. Communications Router (`/api/v1/communications`) **MISSING**
Required for Templates & Outreach:
- ❌ POST `/email-thread` - Start email thread
- ❌ GET `/threads/{property_id}` - Get email threads for property
- ❌ GET `/{thread_id}/messages` - Get messages in thread
- ❌ POST `/send-test` - Send test email
- ❌ POST `/send-batch` - Send batch emails

### 4. Automation Router (`/api/v1/automation`) **MISSING**
Required for Cadence & Compliance:
- ❌ GET `/cadence-rules` - List cadence rules
- ❌ POST `/cadence-rules` - Create cadence rule
- ❌ POST `/cadence-rules/{rule_id}/toggle` - Toggle rule on/off
- ❌ POST `/compliance/validate-send` - Pre-send compliance check
- ❌ GET `/compliance/dnc-check` - DNC list check
- ❌ GET `/compliance/consent-status` - Consent status check

### 5. Sharing Router (`/api/v1/sharing`) **MISSING**
Required for Deal Rooms & Collaboration:
- ❌ GET `/share-links` - List share links
- ❌ POST `/share-links` - Create share link
- ❌ DELETE `/share-links/{link_id}` - Revoke share link
- ❌ GET `/deal-rooms` - List deal rooms
- ❌ POST `/deal-rooms` - Create deal room
- ❌ GET `/deal-rooms/{room_id}/artifacts` - List artifacts in room
- ❌ POST `/deal-rooms/{room_id}/artifacts` - Upload artifact

### 6. Portfolio Router (`/api/v1/portfolio`) **MISSING**
Required for Portfolio Analytics:
- ❌ GET `/deals/{deal_id}/scenarios` - Get deal scenarios
- ❌ GET `/properties/{id}/investor-readiness` - Get investor readiness badge

### 7. Jobs Router (`/api/v1/jobs`) **MISSING**
Required for Status/Observability:
- ❌ GET `/active` - List active background jobs

### 8. SSE Events Router (`/api/v1/sse-events`) **MISSING**
Required for Real-time Updates:
- ❌ GET `/token` - Get SSE authentication token
- ❌ GET `/stream` - SSE event stream
- ❌ GET `/stats` - SSE connection stats
- ❌ POST `/test/emit` - Emit test event

### 9. Status Router (`/api/v1/status`) **MISSING**
Required for Provider Health:
- ❌ GET `/providers` - Get mock provider status (email, SMS, enrichment, etc.)

---

## 🔧 Missing Endpoints in Existing Routers

### Properties Router Additions Needed:
- ❌ PATCH `/properties/{id}/stage` - Update property stage (for Kanban)
- ❌ GET `/properties/{id}/timeline` - Get property activity timeline
- ❌ GET `/properties/{id}/communications` - Get communications for property

### Templates Router **MISSING ENTIRELY**
- ❌ GET `/templates` - List templates
- ❌ POST `/templates` - Create template
- ❌ GET `/templates/{id}` - Get template
- ❌ PUT `/templates/{id}` - Update template
- ❌ POST `/templates/{id}/preview` - Preview template with variables

---

## 📊 Summary

**Current State:**
- ✅ 7 routers implemented
- ✅ ~40 endpoints working
- ✅ Technical platform monitoring (Airflow, system health)
- ✅ Basic CRM (properties, leads, deals)

**What's Missing for Full Sales Ops Platform:**
- ❌ 9 new routers needed
- ❌ ~50 additional endpoints required
- ❌ All sales ops features (workflow, communications, automation, collaboration)

**Priority Implementation Order:**
1. **Workflow** - Needed for Sourcing/Targeting (critical path)
2. **Communications + Templates** - Needed for outreach
3. **Automation** - Needed for compliance and cadences
4. **Portfolio** - Needed for investor readiness
5. **Sharing** - Needed for deal rooms
6. **Data Propensity** - Needed for signals
7. **Jobs** - Needed for observability
8. **SSE Events** - Needed for real-time updates
9. **Status** - Nice to have

---

## 🎯 Implementation Plan

### Phase 1: Core Sales Ops (Sourcing → Communications)
1. Create `workflow.py` router with smart lists & NBA
2. Create `templates.py` router with CRUD
3. Create `communications.py` router with email threads
4. Add missing endpoints to `properties.py` (stage, timeline)

### Phase 2: Automation & Compliance
1. Create `automation.py` router with cadence rules
2. Add compliance validation endpoints
3. Add DNC/consent checks

### Phase 3: Collaboration & Portfolio
1. Create `sharing.py` router with deal rooms
2. Create `portfolio.py` router with scenarios & readiness

### Phase 4: Observability
1. Create `jobs.py` router
2. Create `sse_events.py` router
3. Create `status.py` router (providers)

---

## Questions Before Implementation

1. **Should I implement ALL 9 missing routers?**
   - Or focus on specific priority areas?

2. **Mock Data Strategy:**
   - Use in-memory mock data like current routers?
   - Or connect to actual database tables?

3. **Database Models:**
   - Need to create models for: SmartList, CadenceRule, ShareLink, DealRoom, etc.?
   - Or keep everything in-memory for demo?

4. **Frontend Location:**
   - Where is the React frontend repo?
   - Same repo, different branch?
   - Separate repository?

5. **Airflow Integration:**
   - The technical platform features reference Airflow - is that running?
   - Or should those endpoints also be mocked?

---

## Recommendation

Since you want BOTH technical platform + sales ops working together, I suggest:

1. **Keep technical platform as-is** (pipelines, system routers working great)
2. **Add all 9 sales ops routers** systematically
3. **Use mock data** for demo (consistent with current approach)
4. **Create database models only if needed** for persistence

This gives you a complete platform showing:
- **Technical Side**: Data pipeline orchestration, system health
- **Sales Side**: Smart targeting, communications, deal rooms, compliance

Sound good? Should I proceed with building all the missing sales ops routers?
