# Real Estate Platform — End-to-End Audit Canvas (User-Centric)

**Date**: 2025-11-02
**Auditor**: Claude Code (Automated Analysis)
**Repository**: codybias9/real-estate-os
**Branch**: claude/realestate-audit-canvas-011CUjnrkmyeMSTozDmpy6xx
**Commit**: 64ab64b

---

## 0) TL;DR Scoreboard

### Overall Readiness
- **Overall Readiness (User POV)**: 🔴 **RED** — No user interface exists; zero end-user capabilities
- **Overall Readiness (Technical)**: 🟡 **YELLOW** — Backend infrastructure operational, but features incomplete

### Capability Summary

| Area | Status | Evidence | Owner | ETA | Risks/Notes |
| --------------------------------------- | -------- | -------- | ----- | --- | ----------- |
| A. Discover → Triage (Analyst) | 🔴 R | [§2.A](#a-discover--triage-analyst) | TBD | Q1 2026 | No UI; backend 30% complete |
| B. Deep-dive → Prioritize | 🔴 R | [§2.B](#b-deep-dive--prioritize-analyst) | TBD | Q1 2026 | No scoring engine, no UI |
| C. Investor Memo (Underwriter) | 🔴 R | [§2.C](#c-investor-memo-underwriter) | TBD | Q2 2026 | Template exists; no generator |
| D. Outreach → Follow-ups (Ops) | 🔴 R | [§2.D](#d-outreach--follow-ups-ops) | TBD | Q2 2026 | Zero implementation |
| E. Pipeline Management | 🔴 R | [§2.E](#e-pipeline-management-opsanalyst) | TBD | Q2 2026 | No CRM, no UI |
| F. Portfolio & Reporting | 🔴 R | [§2.F](#f-portfolio--reporting-execlp) | TBD | Q3 2026 | No analytics, no dashboards |
| G. Collaboration & Governance | 🔴 R | [§2.G](#g-collaboration--governance) | TBD | Q3 2026 | No auth, no RBAC |
| H. Speed, Stability, Trust | 🟡 Y | [§2.H](#h-speed-stability-trust) | DevOps | Q1 2026 | Infra stable; no testing/monitoring |
| I. Differentiators (Wow) | 🔴 R | [§2.I](#i-differentiators-wow) | TBD | Q3 2026 | All features unimplemented |
| **Technical Backbone** | 🟡 Y | [§3](#3-technical-backbone-audit) | DevOps | Ongoing | Infra good; security/obs gaps |

### Value Score (Weighted)

| Category | Score | Weight | Weighted |
| -------- | ----- | ------ | -------- |
| **Must-Have (A–E)** | 0.5/5 | 70% | 7/100 |
| **Nice-to-Have (F–I)** | 0.5/4 | 30% | 4/100 |
| **Total** | | | **11/100** |

**Interpretation**: 🔴 **Pre-MVP** — Platform is a backend data pipeline with no user-facing capabilities. 12+ months from production readiness.

---

## 1) Personas & Journeys (Scope of Value)

### Personas
1. **Acquisitions Analyst** — Sources & triages properties from multiple channels
2. **Investor/Underwriter** — Consumes a memo, makes buy/pass decisions
3. **Ops/Disposition** — Executes outreach campaigns, tracks outcomes
4. **Exec/LP** — Portfolio insight; process repeatability & quality metrics

### Primary Journey
**Discover** → **Enrich** → **Score** → **Memo** → **Outreach** → **Pipeline progress** → **Decision**

### Secondary Journeys
- Portfolio reporting & analytics
- Team collaboration & governance
- Speed, stability, and trust (non-functional requirements)

---

## 2) User-Centric Capability Audit

For each capability: ✅ **Green** (ready), 🟡 **Yellow** (partial), 🔴 **Red** (missing/blocked)

---

### A. Discover → Triage (Analyst)
**User value**: *"I can source, skim, and pick the next best properties in minutes."*

#### A1. Freshness & Volume Visible 🔴 RED
- **Evidence**: No UI exists; backend has `prospect_queue` table with timestamps
  - File: `src/database/schema.sql:15` (created_at, updated_at fields)
  - File: `dags/discovery_dag.py:1-20` (scraper runs on-demand, not scheduled)
- **Checks Failed**:
  - ❌ No list view with timestamps
  - ❌ No count badges
  - ❌ No "New in last 24h" filter
  - ❌ No pagination/infinite scroll
- **Backend Status**: 🟡 **Partial** — Data ingestion works (PostgreSQL pipeline), but:
  - Only scrapes books.toscrape.com (placeholder spider)
  - Off-market scraper is a TODO (`agents/discovery/offmarket_scraper/src/offmarket_scraper/scraper.py:1` - empty)
- **Gaps**:
  1. No frontend application (React/Vue/Svelte)
  2. No REST API endpoint to fetch properties (`api/main.py` has only `/healthz` and `/ping`)
  3. No real property data source integration
- **Next Actions**:
  1. **Implement** `/api/properties` endpoint with filters (source, status, date range, pagination)
  2. **Build** React/Next.js frontend with property list view
  3. **Complete** off-market scraper with Playwright for Clark County, NV
  4. **Schedule** discovery DAG to run daily (currently `schedule=None`)
- **Owner/ETA**: Frontend Dev + Backend Dev | 8–12 weeks

---

#### A2. Fast Triage 🔴 RED
- **Evidence**: No UI; no search/filter API endpoints
- **Checks Failed**:
  - ❌ No filters (county/zip/price/bed/bath/lot/owner type)
  - ❌ No saved views
  - ❌ No APN/address search
- **Backend Status**: 🔴 **Missing** — No filtering logic in API
  - `prospect_queue.payload` is JSONB (flexible storage exists)
  - No indexed fields for search (only `status` index exists)
- **Gaps**:
  1. No search API (`GET /api/properties?q=123+Main+St`)
  2. No PostgreSQL full-text search or GIN indexes on JSONB
  3. No user preferences storage for saved filters
- **Next Actions**:
  1. **Design** property data schema (address, APN, county, price, beds, baths, lot size)
  2. **Migrate** from flexible JSONB to typed columns for searchable fields
  3. **Add** PostgreSQL indexes (GIN for JSONB, B-tree for address/APN)
  4. **Implement** filter API with query parameters
  5. **Build** UI filter panel with multi-select dropdowns
- **Owner/ETA**: Backend Dev + Data Engineer | 6–8 weeks

---

#### A3. Signal at a Glance 🔴 RED
- **Evidence**: No scoring system; no flags; no UI cards
- **Checks Failed**:
  - ❌ No 0–100 score
  - ❌ No flags (vacant/absentee/distress)
  - ❌ No quick-view drawer
- **Backend Status**: 🔴 **Missing** — Scoring DAG is placeholder
  - File: `dags/score_master.py:1` (TODO: implement LightGBM inference)
  - Qdrant vector DB provisioned but unused
  - MinIO bucket for models exists (`models/lightgbm/latest.txt`) but empty
- **Gaps**:
  1. No scoring model (LightGBM training pipeline)
  2. No feature engineering (comps, days on market, owner type)
  3. No property flags logic (vacancy detection, absentee owner matching)
  4. No score storage (need `property_scores` table)
- **Next Actions**:
  1. **Define** scoring features (location, comps, owner history, distress signals)
  2. **Train** LightGBM model on historical deal data
  3. **Implement** batch scoring DAG (runs after enrichment)
  4. **Create** `property_scores` table with score + breakdown JSON
  5. **Build** property card component with score badge + flags
- **Owner/ETA**: Data Scientist + Backend Dev + Frontend Dev | 12–16 weeks

---

#### A4. Batch Actions 🔴 RED
- **Evidence**: No UI; no batch API endpoints
- **Checks Failed**:
  - ❌ No multi-select
  - ❌ No "Enrich Selected" action
  - ❌ No "Create Packets" action
  - ❌ No toast notifications
- **Backend Status**: 🟡 **Partial** — Enrichment agent exists
  - File: `agents/enrichment/enrich.py:1-50` (adds fake assessor data)
  - No batch trigger endpoint
- **Gaps**:
  1. No `POST /api/properties/batch/enrich` endpoint
  2. No job queue for async processing (could use Celery, already in stack)
  3. No progress tracking for long-running batches
- **Next Actions**:
  1. **Implement** `POST /api/properties/batch/enrich` with property IDs array
  2. **Trigger** Airflow DAG programmatically via API
  3. **Add** WebSocket or SSE for real-time progress updates
  4. **Build** multi-select UI with action toolbar
  5. **Add** toast notification system (react-hot-toast or similar)
- **Owner/ETA**: Backend Dev + Frontend Dev | 4–6 weeks

---

### B. Deep-dive → Prioritize (Analyst)
**User value**: *"I understand why a property is interesting and what to do next."*

#### B1. Drawer < 2s Load 🔴 RED
- **Evidence**: No UI; no property detail endpoint
- **Checks Failed**: ❌ No drawer component
- **Backend Status**: 🔴 **Missing** — No `GET /api/properties/{id}` endpoint
- **Gaps**: Entire detail view missing
- **Next Actions**:
  1. **Implement** `GET /api/properties/{id}` with all enriched data
  2. **Optimize** query (eager load related tables, avoid N+1)
  3. **Build** slide-over drawer with lazy-loaded sections
  4. **Target** < 200ms API response time
- **Owner/ETA**: Backend Dev + Frontend Dev | 3–4 weeks

---

#### B2. Score Explainability 🔴 RED
- **Evidence**: No scoring system (see A3)
- **Checks Failed**: ❌ No score breakdown panel
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No SHAP/LIME explainability for LightGBM model
  2. No "top 5 features" extraction
- **Next Actions**:
  1. **Add** SHAP library to score DAG
  2. **Store** feature contributions in `property_scores.breakdown` JSON
  3. **Build** accordion panel showing top features with +/− impact
- **Owner/ETA**: Data Scientist + Frontend Dev | 4–6 weeks (after scoring implemented)

---

#### B3. Data Quality Status 🔴 RED
- **Evidence**: No validation logic; no quality tracking
- **Checks Failed**: ❌ No data quality badges
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No geocoding service integration
  2. No owner matching logic
  3. No comp data source
  4. No quality score per property
- **Next Actions**:
  1. **Integrate** geocoding API (Google Maps, Mapbox)
  2. **Add** owner normalization (fuzzy matching, entity resolution)
  3. **Create** `data_quality` JSONB field with coverage % per category
  4. **Build** badge components with "Fix Now" CTAs
- **Owner/ETA**: Backend Dev + Data Engineer | 6–8 weeks

---

#### B4. Action Suggestions 🔴 RED
- **Evidence**: No recommendation engine
- **Checks Failed**: ❌ No "Recommended next action" panel
- **Backend Status**: 🔴 **Missing**
- **Gaps**: No business logic for action recommendations
- **Next Actions**:
  1. **Define** decision tree (e.g., score > 80 → "Generate Memo", missing owner → "Enrich Contact Info")
  2. **Add** `recommended_action` field to property response
  3. **Build** action card with single-click CTA
- **Owner/ETA**: Product Manager + Backend Dev | 4–6 weeks

---

### C. Investor Memo (Underwriter)
**User value**: *"I can open one link and decide quickly."*

#### C1. One-click Memo ≤ 30s 🔴 RED
- **Evidence**: Template exists; no generator
  - File: `templates/investor_memo.mjml:1-12` (basic MJML template with {address}, {score}, {price})
- **Checks Failed**: ❌ No memo generation pipeline
- **Backend Status**: 🔴 **Missing** — DAG is placeholder
  - File: `dags/docgen_packet.py:1` (empty file)
  - MinIO storage configured but no PDF upload logic
- **Gaps**:
  1. No MJML-to-HTML compiler
  2. No HTML-to-PDF renderer (wkhtmltopdf, Puppeteer, weasyprint)
  3. No `POST /api/properties/{id}/memo` endpoint
  4. No `action_packets` table to store generated PDFs
- **Next Actions**:
  1. **Implement** MJML compiler (mjml npm package or Python binding)
  2. **Add** Puppeteer to Airflow image for PDF rendering
  3. **Create** `action_packets` table (id, property_id, type, s3_key, created_at)
  4. **Build** DAG task: fetch property → render template → save to MinIO → insert record
  5. **Expose** `GET /api/properties/{id}/memo` (returns pre-generated PDF URL or triggers on-demand)
- **Owner/ETA**: Backend Dev + DevOps | 6–8 weeks

---

#### C2. Memo Contents 🔴 RED
- **Evidence**: Template has only 3 fields (address, score, price)
- **Checks Failed**: ❌ Missing P1 content (risks, charts, photos)
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No photo scraping/storage
  2. No comp analysis (nearby sales)
  3. No rent roll data
  4. No zoning/permit data
  5. Template needs expansion to 5+ sections
- **Next Actions**:
  1. **Expand** MJML template with sections: Summary, Risks, Comps, Photos, Investment Thesis
  2. **Integrate** photo sources (Zillow API, MLS, Google Street View)
  3. **Add** comp analysis to enrichment pipeline
  4. **Store** photos in MinIO; reference in property data
- **Owner/ETA**: Backend Dev + Data Engineer | 8–12 weeks

---

#### C3. Shareable & Trackable 🔴 RED
- **Evidence**: No sharing system; no analytics
- **Checks Failed**: ❌ No external link generation; ❌ No view tracking
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No public URL generation for memos
  2. No view counter
  3. No click tracking
- **Next Actions**:
  1. **Generate** signed URLs for MinIO objects (time-limited access)
  2. **Create** `memo_views` table (memo_id, viewer_ip, timestamp)
  3. **Implement** pixel tracking or link proxy for view counts
  4. **Build** "Share" button with copy-to-clipboard
- **Owner/ETA**: Backend Dev | 3–4 weeks (after C1 complete)

---

### D. Outreach → Follow-ups (Ops)
**User value**: *"I can contact owners at scale and know what happened."*

#### D1. Contact Readiness 🔴 RED
- **Evidence**: No contact data; no owner enrichment
- **Checks Failed**: ❌ No email/phone/mailing address per entity
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No `contacts` table
  2. No skip tracing integration (TLOxp, IDI, BeenVerified)
  3. No email validation (NeverBounce, ZeroBounce)
- **Next Actions**:
  1. **Create** `contacts` table (id, property_id, owner_name, email, phone, mailing_address, verified_at)
  2. **Integrate** skip tracing API
  3. **Add** email validation step in enrichment DAG
  4. **Build** contact quality score (0–100 based on data completeness)
- **Owner/ETA**: Backend Dev + Data Engineer | 8–10 weeks

---

#### D2. Sequenced Outreach 🔴 RED
- **Evidence**: No outreach system; no email integration
- **Checks Failed**: ❌ No sequences; ❌ No templates
- **Backend Status**: 🔴 **Missing** — SendGrid mentioned but not integrated
- **Gaps**:
  1. No email service provider (SendGrid, Mailgun, SES)
  2. No `campaigns` table
  3. No `campaign_sequences` table
  4. No template management
- **Next Actions**:
  1. **Create** tables: `campaigns`, `campaign_sequences`, `email_templates`
  2. **Integrate** SendGrid API
  3. **Implement** sequence scheduler (Day 0: Email 1, Day 3: Email 2, Day 7: Call)
  4. **Build** campaign builder UI
- **Owner/ETA**: Backend Dev + Frontend Dev | 10–12 weeks

---

#### D3. Personalization 🔴 RED
- **Evidence**: No templating system
- **Checks Failed**: ❌ No token rendering ({owner_name}, {address})
- **Backend Status**: 🔴 **Missing**
- **Gaps**: No Jinja2/Mustache template engine
- **Next Actions**:
  1. **Add** Jinja2 template rendering to email service
  2. **Define** available tokens (property fields, contact fields, company info)
  3. **Build** template preview with sample data
- **Owner/ETA**: Backend Dev | 2–3 weeks (after D2 complete)

---

#### D4. Send & Track 🔴 RED
- **Evidence**: No email delivery tracking
- **Checks Failed**: ❌ No status flow (QUEUED → SENT → DELIVERED → OPENED)
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No `outreach_log` table
  2. No webhook handling for email events (SendGrid webhooks)
  3. No open/click tracking pixels
- **Next Actions**:
  1. **Create** `outreach_log` table (id, campaign_id, contact_id, status, sent_at, delivered_at, opened_at, clicked_at)
  2. **Implement** webhook endpoint (`POST /api/webhooks/sendgrid`)
  3. **Add** tracking pixels to email templates
  4. **Build** timeline view in UI
- **Owner/ETA**: Backend Dev | 4–6 weeks (after D2 complete)

---

#### D5. Reply Capture & Classify 🔴 RED
- **Evidence**: No email inbox integration
- **Checks Failed**: ❌ No reply parsing; ❌ No sentiment classification
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No SendGrid Inbound Parse configuration
  2. No NLP model for sentiment (Positive/Neutral/Negative/OoO)
  3. No reply storage
- **Next Actions**:
  1. **Configure** SendGrid Inbound Parse webhook
  2. **Implement** reply parser (extract thread, detect OoO auto-replies)
  3. **Add** basic sentiment classifier (keyword-based or GPT-4 API)
  4. **Store** replies in `outreach_log` with classification
- **Owner/ETA**: Backend Dev + ML Engineer | 6–8 weeks (after D4 complete)

---

#### D6. Audit Trail & Export 🔴 RED
- **Evidence**: No activity logging; no export functionality
- **Checks Failed**: ❌ No property timeline; ❌ No CSV/PDF export
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No `activity_log` table
  2. No export API
- **Next Actions**:
  1. **Create** `activity_log` table (id, property_id, actor_id, action_type, metadata, timestamp)
  2. **Implement** `GET /api/properties/{id}/timeline`
  3. **Add** CSV export (`GET /api/properties?format=csv`)
  4. **Add** PDF campaign report generator
- **Owner/ETA**: Backend Dev | 4–5 weeks

---

### E. Pipeline Management (Ops/Analyst)
**User value**: *"Nothing falls through the cracks."*

#### E1. Kanban Stages 🔴 RED
- **Evidence**: No CRM; no pipeline UI
- **Checks Failed**: ❌ No drag-drop; ❌ No live updates
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No `pipeline_stages` table
  2. No WebSocket/SSE for live updates
  3. No Kanban component
- **Next Actions**:
  1. **Create** `pipeline_stages` table (id, name, order)
  2. **Add** `property_pipeline` table (property_id, stage_id, assigned_to, updated_at)
  3. **Implement** WebSocket server (FastAPI supports WebSockets natively)
  4. **Build** React DnD Kanban board
  5. **Broadcast** stage changes to all connected clients
- **Owner/ETA**: Backend Dev + Frontend Dev | 8–10 weeks

---

#### E2. Ownership & SLA 🔴 RED
- **Evidence**: No assignment system; no SLA tracking
- **Checks Failed**: ❌ No assignee; ❌ No due dates; ❌ No overdue badges
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No `users` table
  2. No SLA configuration
  3. No overdue detection logic
- **Next Actions**:
  1. **Create** `users` table (id, name, email, role)
  2. **Add** assignee_id, due_date to `property_pipeline`
  3. **Implement** SLA checker DAG (runs hourly, flags overdue items)
  4. **Build** assignee dropdown + date picker in UI
  5. **Add** red badge for overdue properties
- **Owner/ETA**: Backend Dev + Frontend Dev | 5–6 weeks

---

#### E3. Notes & Tasks 🔴 RED
- **Evidence**: No note-taking system; no task management
- **Checks Failed**: ❌ No notes; ❌ No tasks; ❌ No "My Tasks" view
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No `notes` table
  2. No `tasks` table
- **Next Actions**:
  1. **Create** `notes` table (id, property_id, author_id, content, created_at)
  2. **Create** `tasks` table (id, property_id, assignee_id, title, due_date, completed_at)
  3. **Implement** `GET /api/tasks?assignee={user_id}&completed=false`
  4. **Build** note editor (rich text or Markdown)
  5. **Build** "My Tasks" dashboard widget
- **Owner/ETA**: Backend Dev + Frontend Dev | 6–8 weeks

---

#### E4. Bulk Updates 🔴 RED
- **Evidence**: No bulk edit functionality
- **Checks Failed**: ❌ No multi-select stage change; ❌ No bulk assignee change
- **Backend Status**: 🔴 **Missing**
- **Gaps**: No `PATCH /api/properties/batch` endpoint
- **Next Actions**:
  1. **Implement** `PATCH /api/properties/batch` (accepts array of IDs + updates)
  2. **Add** transaction handling (atomic bulk update)
  3. **Build** bulk edit modal with field selectors
- **Owner/ETA**: Backend Dev + Frontend Dev | 3–4 weeks (after E1 complete)

---

### F. Portfolio & Reporting (Exec/LP)
**User value**: *"See deal flow quality at a glance."*

#### F1. Funnel Dashboard 🔴 RED
- **Evidence**: No analytics; no dashboard
- **Checks Failed**: ❌ No funnel metrics; ❌ No conversion rates; ❌ No backlog alerts
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No analytics queries
  2. No dashboard UI
  3. No caching layer for expensive aggregations
- **Next Actions**:
  1. **Implement** `GET /api/analytics/funnel` (count by stage, conversion %, median time-in-stage)
  2. **Add** Redis caching (refresh every 5 minutes)
  3. **Build** dashboard with charts (Chart.js, Recharts, or Tremor)
  4. **Add** backlog alerts (stages with > 50 items aged > 7 days)
- **Owner/ETA**: Backend Dev + Frontend Dev + Data Analyst | 8–10 weeks

---

#### F2. Quality Metrics 🔴 RED
- **Evidence**: No quality tracking
- **Checks Failed**: ❌ No avg score by source; ❌ No top 10 list; ❌ No outreach response rates
- **Backend Status**: 🔴 **Missing**
- **Gaps**: No metrics aggregation queries
- **Next Actions**:
  1. **Implement** `GET /api/analytics/quality` (avg score by source/county, top 10 properties, response rate by template)
  2. **Build** quality dashboard page
  3. **Add** drill-down capability (click chart to see details)
- **Owner/ETA**: Data Analyst + Frontend Dev | 6–8 weeks (requires scoring + outreach first)

---

#### F3. Export/Share 🔴 RED
- **Evidence**: No export functionality
- **Checks Failed**: ❌ No CSV export; ❌ No scheduled PDF emails
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No CSV serializer
  2. No scheduled report DAG
- **Next Actions**:
  1. **Add** CSV export to property list endpoint (`GET /api/properties?format=csv`)
  2. **Create** weekly report DAG (generates PDF, emails to stakeholders)
  3. **Integrate** email delivery for reports
- **Owner/ETA**: Backend Dev | 4–5 weeks

---

### G. Collaboration & Governance
**User value**: *"The team coordinates safely with history."*

#### G1. Roles (Admin/Analyst/Read-only) 🔴 RED
- **Evidence**: No authentication; no RBAC
- **Checks Failed**: ❌ No role-based access control
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No auth system (JWT, OAuth, Auth0, Clerk)
  2. No `users` table with role field
  3. No permission middleware
- **Next Actions**:
  1. **Choose** auth provider (Auth0, Clerk, or self-hosted JWT)
  2. **Create** `users` table with role enum (ADMIN, ANALYST, READ_ONLY)
  3. **Implement** permission decorator for FastAPI routes
  4. **Add** frontend route guards
  5. **Test** with two accounts (Admin can edit, Read-only cannot)
- **Owner/ETA**: Backend Dev + Frontend Dev + Security | 6–8 weeks

---

#### G2. Comments & @mentions 🔴 RED
- **Evidence**: No commenting system; no notifications
- **Checks Failed**: ❌ No comments; ❌ No @mentions; ❌ No notifications
- **Backend Status**: 🔴 **Missing**
- **Gaps**:
  1. No `comments` table
  2. No mention parser
  3. No notification service (email, Slack)
- **Next Actions**:
  1. **Create** `comments` table (id, property_id, author_id, content, mentions, created_at)
  2. **Implement** mention parser (`@username` detection)
  3. **Integrate** email notifications (SendGrid) or Slack webhook
  4. **Build** comment thread UI with mention autocomplete
- **Owner/ETA**: Backend Dev + Frontend Dev | 6–8 weeks

---

#### G3. Change History 🔴 RED
- **Evidence**: No audit log; no change tracking
- **Checks Failed**: ❌ No stage/owner/score change history
- **Backend Status**: 🔴 **Missing**
- **Gaps**: No `activity_log` table (see D6)
- **Next Actions**:
  1. **Create** `activity_log` table (if not done in D6)
  2. **Add** trigger on `property_pipeline` updates to log changes
  3. **Implement** `GET /api/properties/{id}/history`
  4. **Build** timeline component with diff view
- **Owner/ETA**: Backend Dev + Frontend Dev | 4–5 weeks

---

### H. Speed, Stability, Trust
**User value**: *"It's fast and doesn't break."*

#### H1. Performance 🟡 YELLOW
- **Evidence**: Infrastructure is fast; no UI to test
  - PostgreSQL queries are basic (no N+1 detected in scraper pipeline)
  - MinIO/S3 storage is high-performance
  - Redis caching available but unused
- **Checks**:
  - ❓ List < 2s — **Untestable** (no API endpoint)
  - ❓ Drawer < 2s — **Untestable** (no UI)
  - ❓ Memo < 30s — **Untestable** (no generator)
- **Backend Status**: 🟡 **Partial** — Infrastructure capable of sub-2s responses
  - File: `api/main.py:13-25` (ping endpoint responds in ~100ms)
  - PostgreSQL indexed on `status` field
- **Gaps**:
  1. No query performance testing
  2. No response time monitoring
  3. No N+1 query prevention (no ORM best practices yet)
- **Next Actions**:
  1. **Add** `EXPLAIN ANALYZE` to all queries during development
  2. **Implement** eager loading for related data
  3. **Set up** New Relic or Datadog APM
  4. **Enforce** < 200ms API response SLA
  5. **Add** database query logging with slow query alerts (> 500ms)
- **Owner/ETA**: Backend Dev + DevOps | 3–4 weeks (ongoing)

---

#### H2. Resilience 🟡 YELLOW
- **Evidence**: Basic error handling exists; no retry logic; no friendly UI states
  - File: `src/scraper/scraper/pipelines.py:1-50` (no try/except in PostgreSQL insert)
  - File: `agents/enrichment/enrich.py:1-50` (no error handling for S3 failures)
- **Checks**:
  - ❌ No pending states in UI (no UI exists)
  - ❌ No retry logic with deduplication
  - ✅ Airflow DAG retries enabled (default 3 retries)
- **Backend Status**: 🟡 **Partial** — Airflow handles task retries; application code lacks resilience
- **Gaps**:
  1. No exponential backoff for external API calls
  2. No idempotency keys for critical operations
  3. No circuit breakers
  4. No graceful degradation (e.g., missing photos shouldn't block memo generation)
- **Next Actions**:
  1. **Add** `tenacity` library for retries with exponential backoff
  2. **Implement** idempotency middleware (track request IDs in Redis)
  3. **Add** circuit breakers for external services (skip tracing, geocoding)
  4. **Build** loading skeletons + error boundaries in UI
  5. **Add** health checks for all dependencies (PostgreSQL, MinIO, Qdrant, SendGrid)
- **Owner/ETA**: Backend Dev + DevOps | 5–6 weeks

---

#### H3. Accessibility 🔴 RED
- **Evidence**: No UI; no accessibility testing
- **Checks Failed**: ❌ No keyboard nav; ❌ No ARIA labels; ❌ No contrast testing
- **Backend Status**: N/A
- **Gaps**: Entire frontend missing
- **Next Actions**:
  1. **Choose** accessible component library (Radix UI, Headless UI, or Chakra UI)
  2. **Enforce** WCAG 2.1 AA standards (use axe DevTools)
  3. **Add** keyboard shortcuts (J/K for list nav, Esc to close drawer)
  4. **Test** with screen readers (NVDA, JAWS)
  5. **Add** focus management on route changes
- **Owner/ETA**: Frontend Dev + UX | 4–6 weeks (parallel with UI build)

---

### I. Differentiators (Wow)
**User value**: *"Clearly better than spreadsheets + generic CRM."*

#### I1. Trustworthy Score Explainability 🔴 RED
- **Evidence**: No scoring system (see B2)
- **Checks Failed**: ❌ No explainability
- **Backend Status**: 🔴 **Missing**
- **Next Actions**: See B2 (SHAP values, feature breakdown)
- **Owner/ETA**: Data Scientist | 4–6 weeks (after scoring)

---

#### I2. Instant Investor-Ready Memo 🔴 RED
- **Evidence**: Template exists; no generator (see C1, C2)
- **Checks Failed**: ❌ No one-click memo
- **Backend Status**: 🔴 **Missing**
- **Next Actions**: See C1 (MJML compiler, PDF generator)
- **Owner/ETA**: Backend Dev | 6–8 weeks

---

#### I3. Live Pipeline for Multi-user 🔴 RED
- **Evidence**: No WebSocket/SSE; no CRM (see E1)
- **Checks Failed**: ❌ No real-time updates
- **Backend Status**: 🔴 **Missing**
- **Next Actions**: See E1 (WebSocket server, Kanban board)
- **Owner/ETA**: Backend Dev + Frontend Dev | 8–10 weeks

---

#### I4. One-click Sequences with Outcomes 🔴 RED
- **Evidence**: No outreach system (see D2, D4, D5)
- **Checks Failed**: ❌ No sequences; ❌ No open/click/reply tracking
- **Backend Status**: 🔴 **Missing**
- **Next Actions**: See D2 (campaign builder, SendGrid integration)
- **Owner/ETA**: Backend Dev | 10–12 weeks

---

#### I5. Batch Triage at Speed 🔴 RED
- **Evidence**: No filters; no batch actions (see A2, A4)
- **Checks Failed**: ❌ No fast filtering; ❌ No bulk actions
- **Backend Status**: 🔴 **Missing**
- **Next Actions**: See A2, A4 (search API, batch endpoints)
- **Owner/ETA**: Backend Dev + Frontend Dev | 6–8 weeks

---

## 3) Technical Backbone Audit

### 3.1 Infrastructure ✅ GREEN
**Evidence**: Kubernetes cluster with all core services deployed
- File: `infra/k8s/api.yaml:1` (FastAPI deployment)
- File: `infra/charts/overrides/values-postgres.yaml:1` (PostgreSQL with Bitnami chart)
- File: `infra/charts/overrides/values-airflow.yaml:1` (Airflow with CeleryExecutor)
- File: `docker-compose.yaml:1` (local dev environment)

**Components**:
- ✅ **PostgreSQL** — Main database (Bitnami chart, HA-ready)
- ✅ **Redis** — Celery result backend
- ✅ **RabbitMQ** — Message queue for Celery
- ✅ **MinIO** — Object storage (S3-compatible)
- ✅ **Qdrant** — Vector database (unused currently)
- ✅ **Airflow** — Orchestration with custom image (`codybias9/reo-airflow:0.1.0`)
- ✅ **FastAPI** — REST API (`codybias9/reo-api:0.1.3`)

**Strengths**:
- Multi-stage Docker builds for efficiency
- Poetry for dependency management
- Docker Compose for local development
- Helm charts for production deployment

**Gaps**:
- No CI/CD pipeline (GitHub Actions, Jenkins)
- No staging environment
- No blue/green deployment strategy
- No auto-scaling (HPA for FastAPI pods)

**Next Actions**:
1. **Set up** GitHub Actions for CI (lint, test, build, push images)
2. **Add** staging namespace to Kubernetes
3. **Configure** HorizontalPodAutoscaler for API (target: 70% CPU)
4. **Document** deployment runbook

---

### 3.2 Security 🔴 RED
**Evidence**: No authentication; secrets in plain YAML files
- File: `infra/k8s/db-secret.yaml:1` (base64-encoded secrets, not encrypted)

**Critical Gaps**:
- ❌ No authentication system
- ❌ No API key management
- ❌ No secrets encryption (Sealed Secrets, Vault, AWS Secrets Manager)
- ❌ No network policies (Kubernetes NetworkPolicy)
- ❌ No rate limiting on API endpoints
- ❌ No SQL injection prevention (Pydantic validation exists but underused)
- ❌ No HTTPS/TLS for API (no Ingress controller mentioned)
- ❌ No security scanning (Trivy, Snyk)

**Next Actions**:
1. **Implement** JWT authentication (Auth0 or self-hosted)
2. **Migrate** secrets to Kubernetes Sealed Secrets or HashiCorp Vault
3. **Add** rate limiting (slowapi or NGINX Ingress)
4. **Configure** HTTPS with Let's Encrypt (cert-manager)
5. **Add** Trivy to CI pipeline for vulnerability scanning
6. **Implement** SQL injection prevention (use SQLAlchemy ORM exclusively)
7. **Add** CORS configuration (restrict origins)
8. **Enable** audit logging for all API requests

**Owner/ETA**: Security Engineer + DevOps | 8–10 weeks

---

### 3.3 Observability 🟡 YELLOW
**Evidence**: Basic logging; no monitoring/alerting
- File: `src/scraper/spiders/listings.py:1` (imports loguru but minimal usage)
- File: `dags/sys_heartbeat.py:1` (health check DAG exists)

**Current State**:
- ✅ **Health checks** exist (`/healthz`, `sys_heartbeat` DAG)
- ✅ **Structured logging** library available (loguru)
- ❌ **No centralized logging** (no ELK, Loki, or CloudWatch)
- ❌ **No metrics collection** (no Prometheus, Datadog)
- ❌ **No APM** (no New Relic, Datadog APM, OpenTelemetry)
- ❌ **No error tracking** (no Sentry, Rollbar)
- ❌ **No uptime monitoring** (no PagerDuty, Pingdom)
- ❌ **No dashboards** (no Grafana)

**Gaps**:
1. No visibility into production errors
2. No alerting for service failures
3. No performance metrics (request latency, DB query times)
4. No distributed tracing for DAG runs

**Next Actions**:
1. **Deploy** Prometheus + Grafana in Kubernetes
2. **Instrument** FastAPI with OpenTelemetry
3. **Add** Sentry for error tracking
4. **Configure** Airflow metrics export (StatsD → Prometheus)
5. **Create** dashboards:
   - API latency (p50, p95, p99)
   - DAG success/failure rates
   - Database connection pool usage
   - MinIO storage usage
6. **Set up** PagerDuty alerts for:
   - API 5xx errors > 10/min
   - DAG failures
   - Database connection pool exhaustion
   - Disk usage > 80%

**Owner/ETA**: DevOps + SRE | 6–8 weeks

---

### 3.4 Data Pipeline ✅ PARTIAL GREEN
**Evidence**: Basic pipeline operational
- File: `dags/scrape_listings_dag.py:1-20` (working Scrapy DAG)
- File: `src/scraper/scraper/pipelines.py:1-50` (PostgreSQL storage)
- File: `src/database/schema.sql:8-17` (prospect_queue table)

**Current State**:
- ✅ **Ingestion**: Scrapy spider → PostgreSQL (working for books.toscrape.com)
- 🟡 **Enrichment**: Agent exists (`agents/enrichment/enrich.py`) but not fully integrated
- 🔴 **Scoring**: Placeholder DAG only
- 🔴 **Document Generation**: Placeholder DAG only
- ✅ **Storage**: MinIO configured, Qdrant ready

**Strengths**:
- Flexible JSONB payload for schema-less ingestion
- Auto-updating timestamps (PostgreSQL trigger)
- Status field for processing state machine

**Gaps**:
- No real property data sources (MLS, Zillow, Realtor.com)
- No data validation/cleaning
- No duplicate detection
- No backfill capability
- No data lineage tracking

**Next Actions**:
1. **Integrate** real property data sources (start with Clark County, NV assessor data)
2. **Add** duplicate detection (hash on address + APN)
3. **Implement** data validation (Pydantic models for property schema)
4. **Add** backfill DAG (reprocess historical data)
5. **Create** data quality dashboard (missing fields, geocode failures)

**Owner/ETA**: Data Engineer | 8–10 weeks

---

### 3.5 Testing 🔴 RED
**Evidence**: No tests found
- Command: `find . -name "*test*.py"` → 0 results

**Critical Gaps**:
- ❌ No unit tests
- ❌ No integration tests
- ❌ No E2E tests
- ❌ No test coverage tracking
- ❌ No CI test automation

**Next Actions**:
1. **Add** pytest framework
2. **Write** unit tests for:
   - Scraper spiders (mock HTTP responses)
   - Enrichment agent (mock S3, test data transformations)
   - API endpoints (mock database)
3. **Write** integration tests:
   - DAG execution (Airflow test mode)
   - Database migrations (Alembic)
   - End-to-end pipeline (scrape → enrich → score)
4. **Add** E2E tests (Playwright or Cypress when UI exists)
5. **Set up** coverage reporting (pytest-cov, Codecov)
6. **Enforce** 80% coverage threshold in CI

**Owner/ETA**: All Developers | 6–8 weeks (parallel with feature work)

---

## 4) Summary & Recommendations

### 4.1 Current State
This is a **backend data infrastructure platform** in **Phase 0–2** of an 8-phase roadmap. The platform has:

✅ **Working**:
- Airflow orchestration with Scrapy integration
- PostgreSQL ingestion pipeline
- MinIO/Qdrant storage provisioned
- Basic enrichment agent (fake data)
- Health checks and deployment scripts

🔴 **Missing**:
- **Entire frontend** (0 UI components)
- **Scoring engine** (no LightGBM model)
- **Memo generation** (template exists but no compiler/renderer)
- **Outreach system** (no email integration)
- **CRM/pipeline management** (no tables, no UI)
- **Analytics/reporting** (no dashboards)
- **Authentication** (no user system)
- **Testing** (0 tests)
- **Production monitoring** (no Prometheus, Sentry, APM)

### 4.2 Readiness Assessment
- **User Readiness**: 🔴 **RED (0/100)** — Platform has zero end-user capabilities. Not usable by analysts, underwriters, or ops teams.
- **Technical Readiness**: 🟡 **YELLOW (45/100)** — Infrastructure is solid, but features/security/testing incomplete.

### 4.3 Time to Production-Ready
**Estimated Timeline**: **12–18 months** (with 4-person team)

| Phase | Features | Duration | Dependencies |
| ----- | -------- | -------- | ------------ |
| **Phase 1** (Q1 2026) | Property list UI, search/filters, detail view, basic scoring | 12 weeks | Frontend Dev + Backend Dev + Data Scientist |
| **Phase 2** (Q2 2026) | Memo generation, outreach (email), contact enrichment | 12 weeks | Backend Dev + Data Engineer |
| **Phase 3** (Q2 2026) | Pipeline/CRM, Kanban board, notes/tasks | 10 weeks | Backend Dev + Frontend Dev |
| **Phase 4** (Q3 2026) | Analytics dashboard, reporting, auth/RBAC | 10 weeks | Data Analyst + Frontend Dev + Security |
| **Phase 5** (Q3 2026) | Collaboration (comments, @mentions, change history) | 6 weeks | Backend Dev + Frontend Dev |
| **Phase 6** (Q4 2026) | Performance optimization, testing, security hardening | 8 weeks | All team + SRE |
| **Phase 7** (Q1 2027) | Production monitoring, alerting, runbooks | 6 weeks | DevOps + SRE |

### 4.4 Critical Path
**Blockers** (must be resolved before user value):
1. **Frontend framework selection** (React, Vue, Svelte) — 1 week
2. **Authentication system** (Auth0, Clerk, or custom JWT) — 3 weeks
3. **Property data source integration** (Clark County assessor data) — 4 weeks
4. **Scoring model training** (requires historical deal data) — 6 weeks

**First Milestone** (MVP): Property discovery + scoring + memo generation (20 weeks)

### 4.5 Top 10 Next Actions (Prioritized)
1. **Choose frontend stack** and scaffold app (React + Next.js recommended) — **1 week**
2. **Implement `/api/properties` endpoint** with pagination/filters — **2 weeks**
3. **Integrate real property data source** (Clark County, NV) — **4 weeks**
4. **Build property list UI** with search/filters — **3 weeks**
5. **Train LightGBM scoring model** (need historical deal data) — **6 weeks**
6. **Implement memo generation** (MJML → PDF pipeline) — **4 weeks**
7. **Add authentication** (Auth0 or JWT) — **3 weeks**
8. **Set up CI/CD** (GitHub Actions: lint, test, build, deploy) — **2 weeks**
9. **Add testing framework** (pytest + initial test suite) — **3 weeks**
10. **Deploy monitoring stack** (Prometheus + Grafana + Sentry) — **2 weeks**

**Total**: 30 weeks (7.5 months) to functional MVP

### 4.6 Resource Requirements
**Recommended Team**:
- 1x **Frontend Engineer** (React/Next.js)
- 1x **Backend Engineer** (FastAPI/PostgreSQL)
- 1x **Data Scientist** (LightGBM, feature engineering)
- 1x **DevOps/SRE** (Kubernetes, monitoring, security)
- 0.5x **Product Manager** (prioritization, user testing)
- 0.5x **UX Designer** (UI/UX, accessibility)

**Budget** (rough estimate):
- Personnel: $1.2M/year (6 people, blended rate $200k/year)
- Infrastructure: $2k/month (Kubernetes cluster, databases, monitoring)
- Third-party services: $1k/month (Auth0, SendGrid, geocoding APIs)

### 4.7 Risk Mitigation
| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| No historical deal data for scoring | 🔴 High | Partner with investor/broker for labeled data; start with rule-based scoring as fallback |
| Property data sources require licensing | 🟡 Medium | Budget $5k–$20k/year for MLS/assessor data access; start with free county data |
| Team bandwidth (current devs overloaded) | 🔴 High | Hire dedicated team; avoid splitting time with other projects |
| Scope creep (feature requests from stakeholders) | 🟡 Medium | Enforce MVP scope; defer nice-to-haves to Phase 2+ |
| Security vulnerabilities delay launch | 🟡 Medium | Start security hardening early; schedule penetration test 8 weeks before launch |

---

## 5) Conclusion

**Status**: 🔴 **Pre-MVP** — Platform is a **backend data pipeline** with **no user-facing capabilities**. While the infrastructure is solid (Airflow, PostgreSQL, MinIO, Kubernetes), the product is **12–18 months from production-ready** with a dedicated team.

**Recommendation**: **Do NOT launch** to users until:
1. ✅ Frontend application exists
2. ✅ Property discovery + scoring + memo generation working
3. ✅ Authentication + RBAC implemented
4. ✅ Test coverage > 60%
5. ✅ Production monitoring (Prometheus, Sentry, APM) deployed

**Next Step**: Prioritize **Phase 1** (property list UI + scoring) as the critical path to demonstrable user value.

---

## Appendix: File Evidence Index

### Backend Infrastructure
- `api/main.py:1-26` — FastAPI app (health + ping endpoints)
- `src/database/schema.sql:8-35` — prospect_queue table
- `dags/discovery_dag.py:8-20` — Scrapy execution DAG
- `dags/sys_heartbeat.py:1-20` — Health check DAG
- `src/scraper/spiders/listings.py:1-50` — Web scraper spider
- `src/scraper/scraper/pipelines.py:1-50` — PostgreSQL pipeline
- `agents/enrichment/enrich.py:1-50` — Property enrichment agent

### Configuration
- `infra/k8s/api.yaml:1` — FastAPI deployment manifest
- `infra/charts/overrides/values-postgres.yaml:1` — PostgreSQL Helm config
- `infra/charts/overrides/values-airflow.yaml:1` — Airflow Helm config
- `docker-compose.yaml:1` — Local dev environment
- `pyproject.toml:1` — Python dependencies (Poetry)

### Placeholders (TODO)
- `dags/score_master.py:1` — Scoring DAG (empty)
- `dags/docgen_packet.py:1` — Memo generation DAG (empty)
- `agents/discovery/offmarket_scraper/src/offmarket_scraper/scraper.py:1` — Property scraper (TODO)
- `templates/investor_memo.mjml:1-12` — Email template (basic)

### Missing (No Files)
- Frontend: 0 files
- Tests: 0 files
- Monitoring: 0 files
- Documentation: Minimal (README only)

---

**End of Audit**
Generated by Claude Code on 2025-11-02
