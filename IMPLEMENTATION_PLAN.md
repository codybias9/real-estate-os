# Real Estate OS - Complete Demo Implementation Plan

**Goal:** Build a fully functional demo platform that showcases the entire property investment automation pipeline

**Timeline:** Systematic implementation across 6 phases
**Approach:** Backend-first, then frontend, then integration

---

## Phase 1: Foundation - Data Models & API (Priority 1)

### 1A. Property Data Models
**Files to Create:**
- `src/models/property.py` - Property model with all fields
- `src/models/enrichment.py` - Enrichment data model
- `src/models/score.py` - Scoring model
- `src/models/document.py` - Generated documents model
- `src/models/campaign.py` - Email campaign model

**Property Fields:**
```python
- id, source, source_id, url
- address, city, state, zip_code, county
- price, bedrooms, bathrooms, sqft, lot_size, year_built
- property_type, status, listing_date
- description, features, images
- latitude, longitude
- created_at, updated_at
```

### 1B. Database Schema
**Files to Create:**
- `db/versions/001_create_properties_table.py`
- `db/versions/002_create_enrichment_table.py`
- `db/versions/003_create_scores_table.py`
- `db/versions/004_create_documents_table.py`
- `db/versions/005_create_campaigns_table.py`

**Tables:**
1. `properties` - Core property data
2. `property_enrichment` - Assessor/public records
3. `property_scores` - ML scores and features
4. `generated_documents` - PDFs and memos
5. `email_campaigns` - Outreach tracking
6. `outreach_log` - Individual email events

### 1C. Property Scrapers
**Files to Update:**
- `src/scraper/spiders/listings.py` - Change from books to properties
- `src/scraper/items.py` - Update to PropertyItem
- Add: `src/scraper/spiders/zillow_spider.py` (simulated)
- Add: `src/scraper/spiders/redfin_spider.py` (simulated)

**Data Source:** Generate realistic simulated property data

### 1D. API Endpoints
**File to Update:** `api/main.py`

**Endpoints to Add:**
```
Properties:
- GET    /api/properties              - List with filters
- GET    /api/properties/{id}         - Single property
- POST   /api/properties              - Create (manual entry)
- PUT    /api/properties/{id}         - Update
- DELETE /api/properties/{id}         - Delete

Enrichment:
- GET    /api/properties/{id}/enrichment     - Get enrichment data
- POST   /api/properties/{id}/enrich         - Trigger enrichment

Scoring:
- GET    /api/properties/{id}/score          - Get score
- POST   /api/properties/{id}/score          - Trigger scoring
- GET    /api/scores/top                     - Top scored properties

Documents:
- GET    /api/properties/{id}/memo           - Get/generate memo
- GET    /api/properties/{id}/memo.pdf       - Download PDF

Campaigns:
- GET    /api/campaigns                      - List campaigns
- POST   /api/campaigns                      - Create campaign
- POST   /api/campaigns/{id}/send            - Send (simulate)

Dashboard:
- GET    /api/dashboard/stats                - Overview stats
- GET    /api/dashboard/pipeline             - Pipeline status
```

---

## Phase 2: Intelligence - Enrichment & Scoring (Priority 1)

### 2A. Enrichment Service
**Files to Update:**
- `agents/enrichment/enrich.py` - Replace mock with realistic simulator

**Data to Add:**
- Assessor parcel number (APN)
- Tax assessment value
- Last sale date and price
- Zoning information
- School district and ratings
- Crime statistics (simulated)
- Walkability score
- Nearby amenities
- Market trends

### 2B. ML Scoring System
**Files to Create:**
- `agents/scoring/scorer.py` - Scoring logic
- `agents/scoring/train_model.py` - Model training script
- `agents/scoring/features.py` - Feature engineering
- `agents/scoring/models/lightgbm_model.pkl` - Trained model

**Scoring Features:**
- Price below market average
- Price reduction amount
- Days on market
- Estimated rental yield
- Equity opportunity percentage
- Neighborhood appreciation trend
- Condition indicators
- Flip potential score

**Algorithm:** LightGBM with realistic weights or rule-based fallback

### 2C. Airflow DAG Updates
**Files to Update:**
- `dags/enrichment_property.py` - Implement actual enrichment
- `dags/score_master.py` - Implement actual scoring
- `dags/discovery_offmarket.py` - Fix to use property scrapers

**Add:**
- `dags/data_pipeline_master.py` - Orchestrate full pipeline

---

## Phase 3: Frontend - Dashboard & UI (Priority 1)

### 3A. Next.js Setup
**Directory to Create:** `frontend/`

**Structure:**
```
frontend/
├── package.json
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
├── public/
│   └── images/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx (Dashboard)
│   │   ├── properties/
│   │   │   ├── page.tsx (List)
│   │   │   └── [id]/
│   │   │       └── page.tsx (Detail)
│   │   ├── pipeline/
│   │   │   └── page.tsx (Status)
│   │   └── campaigns/
│   │       └── page.tsx (Email)
│   ├── components/
│   │   ├── PropertyCard.tsx
│   │   ├── PropertyTable.tsx
│   │   ├── ScoreBadge.tsx
│   │   ├── StatCard.tsx
│   │   ├── PipelineFlow.tsx
│   │   └── Layout/
│   ├── lib/
│   │   ├── api.ts
│   │   └── types.ts
│   └── styles/
│       └── globals.css
```

### 3B. Key Pages

**Dashboard (`/`):**
- Total properties discovered
- Properties enriched
- Properties scored
- Top 10 scored properties table
- Pipeline health status
- Recent activity feed

**Properties List (`/properties`):**
- Filterable table (by score, price, location, status)
- Sortable columns
- Search functionality
- Pagination
- Score badges with color coding
- Click to detail view

**Property Detail (`/properties/[id]`):**
- Hero section with main image and key stats
- Property information grid
- Enrichment data section
- Score breakdown with visualization
- Investment highlights
- Comparable properties
- Action buttons (Generate Memo, Add to Campaign)
- Status timeline

**Pipeline Status (`/pipeline`):**
- Visual pipeline diagram (Discovery → Enrichment → Scoring → Docgen → Email)
- Properties in each stage
- DAG run status from Airflow
- Recent errors and warnings
- Performance metrics

**Campaigns (`/campaigns`):**
- Create new campaign
- Campaign list with stats
- Campaign detail with recipients
- Send simulation

### 3C. Component Library
- PropertyCard - Compact property display
- PropertyTable - Sortable table
- ScoreBadge - Color-coded score (0-100)
- StatCard - Dashboard metrics
- PipelineFlow - Visual workflow
- FilterBar - Search and filters
- Pagination - Table pagination

---

## Phase 4: Document Generation (Priority 2)

### 4A. PDF Generation
**Files to Create:**
- `agents/docgen/generator.py` - PDF generation logic
- `agents/docgen/requirements.txt` - Dependencies

**Files to Update:**
- `templates/investor_memo.mjml` - Expand template

**Template Sections:**
1. Cover page with property image
2. Executive summary
3. Property details
4. Market analysis
5. Financial projections
6. Investment highlights
7. Risk factors
8. Next steps

**Tech Stack:**
- MJML → HTML conversion
- Puppeteer or WeasyPrint for HTML → PDF

### 4B. MinIO Integration
**Files to Create:**
- `agents/docgen/storage.py` - MinIO client

**Storage Structure:**
```
minio://documents/
  └── properties/
      └── {property_id}/
          ├── memo.pdf
          └── images/
```

### 4C. Airflow DAG
**File to Update:**
- `dags/docgen_packet.py` - Implement actual generation

---

## Phase 5: Email Outreach - Simulated (Priority 2)

### 5A. Email Service
**Files to Create:**
- `agents/outreach/sender.py` - Email simulation
- `agents/outreach/templates.py` - Email templates
- `agents/outreach/tracker.py` - Event tracking

**Features:**
- Simulate SendGrid API calls
- Log "sent" emails to database
- Track opens, clicks (simulated)
- Unsubscribe handling
- Campaign analytics

### 5B. Email Templates
- Investment opportunity notification
- Property highlights
- Market report
- Follow-up sequences

### 5C. Airflow DAG
**File to Create:**
- `dags/outreach_campaign.py` - Email sending DAG

---

## Phase 6: Demo Data & Integration (Priority 1)

### 6A. Demo Data Generator
**File to Create:**
- `scripts/generate_demo_data.py`

**Generate:**
- 50 realistic properties across 3 cities
- Mix of property types (SFH, condo, multifamily)
- Range of scores (20-95)
- Various statuses (new, enriched, scored, documented)
- Realistic addresses, prices, features
- Sample images (placeholder or stock)

### 6B. Integration Tests
**Files to Create:**
- `tests/integration/test_pipeline.py`
- `tests/integration/test_api.py`
- `tests/e2e/test_demo_flow.py`

### 6C. Demo Script
**File to Create:**
- `DEMO_SCRIPT.md` - Step-by-step demo walkthrough

---

## Docker Compose Updates

**Add frontend service:**
```yaml
frontend:
  build: ./frontend
  ports:
    - "3000:3000"
  environment:
    - NEXT_PUBLIC_API_URL=http://api:8000
  depends_on:
    - api
```

---

## Success Criteria

### Demo Must Showcase:
1. ✅ Properties being discovered (simulated scraping)
2. ✅ Data enrichment with assessor information
3. ✅ ML-based scoring with explanations
4. ✅ Professional dashboard UI
5. ✅ Property detail pages with all data
6. ✅ PDF investor packet generation
7. ✅ Email campaign simulation
8. ✅ End-to-end pipeline visibility
9. ✅ Real-time status updates
10. ✅ Professional appearance and UX

### Technical Requirements:
- All API endpoints functional
- Database fully normalized
- Airflow DAGs running
- Frontend responsive and fast
- Demo data realistic
- Zero errors during demo
- Can run locally with `docker-compose up`

---

## Execution Order

**Week 1:**
1. Phase 1A-B: Data models & database (Days 1-2)
2. Phase 1C: Fix scrapers with simulated data (Day 2)
3. Phase 1D: Build all API endpoints (Days 3-4)
4. Phase 2A-B: Enrichment & scoring (Day 5)

**Week 2:**
5. Phase 2C: Update Airflow DAGs (Day 6)
6. Phase 3A: Setup Next.js frontend (Day 7)
7. Phase 3B: Build all pages (Days 8-9)
8. Phase 3C: Integrate with API (Day 10)

**Week 3:**
9. Phase 4: PDF generation (Days 11-12)
10. Phase 5: Email simulation (Day 13)
11. Phase 6A-B: Demo data & tests (Day 14)
12. Phase 6C: Demo polish & practice (Day 15)

---

## File Checklist

### Backend
- [ ] `src/models/*.py` (5 files)
- [ ] `db/versions/*.py` (5 migrations)
- [ ] `src/scraper/spiders/*.py` (updated)
- [ ] `api/main.py` (expanded)
- [ ] `api/routes/*.py` (new routers)
- [ ] `api/schemas/*.py` (Pydantic models)
- [ ] `agents/enrichment/enrich.py` (updated)
- [ ] `agents/scoring/*.py` (new)
- [ ] `agents/docgen/*.py` (new)
- [ ] `agents/outreach/*.py` (new)
- [ ] `dags/*.py` (5 DAGs updated)

### Frontend
- [ ] `frontend/package.json`
- [ ] `frontend/src/app/page.tsx`
- [ ] `frontend/src/app/properties/page.tsx`
- [ ] `frontend/src/app/properties/[id]/page.tsx`
- [ ] `frontend/src/app/pipeline/page.tsx`
- [ ] `frontend/src/app/campaigns/page.tsx`
- [ ] `frontend/src/components/*.tsx` (10+ components)
- [ ] `frontend/src/lib/api.ts`

### Infrastructure
- [ ] `docker-compose.yaml` (updated)
- [ ] `frontend/Dockerfile`
- [ ] `scripts/generate_demo_data.py`
- [ ] `DEMO_SCRIPT.md`

**Total New/Updated Files:** ~50-60 files

This plan creates a complete, demo-ready platform systematically.
