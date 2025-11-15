# Real Estate OS - Demo Guide

Complete guide for running and demonstrating the Real Estate OS platform.

## Table of Contents

1. [System Overview](#system-overview)
2. [Quick Start](#quick-start)
3. [Demo Data Setup](#demo-data-setup)
4. [Platform Components](#platform-components)
5. [Demo Walkthrough](#demo-walkthrough)
6. [API Endpoints](#api-endpoints)
7. [Troubleshooting](#troubleshooting)

---

## System Overview

Real Estate OS is an automated platform for discovering, analyzing, and reaching out to property investment opportunities. It includes:

- **Property Discovery**: Automated scraping and data ingestion
- **Enrichment**: Add assessor data, market metrics, and location intelligence
- **AI Scoring**: Multi-factor investment analysis and recommendations
- **Document Generation**: Professional investor memo PDFs
- **Email Outreach**: Campaign management and engagement tracking
- **Dashboard**: Modern web interface for managing the pipeline

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL (via Docker)

### 1. Start the Backend Services

```bash
# Start all services (PostgreSQL, Airflow, API)
docker-compose up -d

# Wait for services to be healthy
docker-compose ps
```

### 2. Run Database Migration

```bash
# Apply database schema
cd db
alembic upgrade head
```

### 3. Generate Demo Data

```bash
# Populate the database with sample properties
python scripts/generate_demo_data.py
```

This will create:
- 50 properties across 5 cities
- Enrichment data for all properties
- Investment scores (0-100) for each property
- 20 investor memo PDFs for top properties
- 3 email campaigns with sample outreach logs

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: http://localhost:3000

### 5. Access the Platform

- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Airflow**: http://localhost:8080 (username: `airflow`, password: `airflow`)

---

## Demo Data Setup

### Running the Demo Data Generator

The demo data generator creates a complete, realistic dataset:

```bash
python scripts/generate_demo_data.py
```

**What it creates:**

1. **50 Properties** in Las Vegas, Henderson, Phoenix, Scottsdale, and Reno
   - Realistic prices based on market data
   - Property features, descriptions, images
   - Various property types (single_family, condo, multi_family)

2. **Enrichment Data** for each property
   - Tax assessments and annual taxes
   - School ratings (0-10)
   - Walk scores (0-100)
   - Crime rates (Low/Medium/High)
   - Market data (median rent, vacancy rates)

3. **Investment Scores** (0-100)
   - Multi-factor analysis:
     - Price Analysis (25%)
     - Market Timing (20%)
     - Investment Metrics (25%)
     - Location Quality (15%)
     - Property Condition (15%)
   - Recommendations: STRONG BUY / BUY / HOLD / PASS
   - Risk assessments: LOW / MEDIUM / HIGH

4. **Investor Memos** (Top 20 properties)
   - Professional PDF documents
   - Complete property analysis
   - Investment recommendations
   - Stored in `/output/documents/`

5. **Email Campaigns**
   - Sample campaigns with various statuses
   - Outreach logs with simulated engagement
   - Opens, clicks, and replies tracked

---

## Platform Components

### 1. Property Discovery (Scraper)

**Location**: `src/scraper/`

Scrapy-based scraper that generates realistic property data:

```bash
# Run the scraper manually
cd src/scraper
scrapy crawl listings -a count=20
```

**Configuration**:
- Cities: Las Vegas, Henderson, Phoenix, Scottsdale, Reno
- Property types: single_family, condo, townhouse, multi_family
- Price ranges: $150K - $2.5M based on city/type

### 2. Enrichment Service

**Location**: `agents/enrichment/`

Adds value-add data to raw properties:

```python
from agents.enrichment.service import EnrichmentService

service = EnrichmentService(db)
service.enrich_property(property_id)
```

**Data Added**:
- Tax assessment values
- Ownership information
- School district and ratings
- Walkability scores
- Crime statistics
- Median area rent and home prices
- Market trends (population growth, unemployment)

### 3. Scoring Engine

**Location**: `agents/scoring/`

Multi-factor investment analysis:

```python
from agents.scoring.scorer import PropertyScorer

scorer = PropertyScorer(db)
score = scorer.score_property(property_id)
```

**Scoring Factors**:

1. **Price Analysis** (25%)
   - Price vs. assessed value
   - Price per square foot
   - Market positioning

2. **Market Timing** (20%)
   - Days on market
   - Market trends
   - Seasonal factors

3. **Investment Metrics** (25%)
   - Cap rate
   - Cash-on-cash return
   - Gross yield

4. **Location Quality** (15%)
   - School ratings
   - Walk score
   - Crime rate
   - Market growth

5. **Property Condition** (15%)
   - Age of property
   - Recent updates
   - Condition indicators

### 4. Document Generation

**Location**: `agents/docgen/`

Professional PDF investor memos:

```python
from agents.docgen.service import DocumentService

service = DocumentService(db)
document = service.generate_investor_memo(property_id)
```

**PDF Includes**:
- Property details and photos
- Investment score and breakdown
- Financial analysis (cap rate, CoC, yield)
- Market and location data
- Risk assessment
- Investment recommendation

### 5. Email Outreach

**Location**: `agents/outreach/`

Campaign management and email tracking:

```python
from agents.outreach.email_service import EmailService

service = EmailService(db)
result = service.send_campaign(campaign_id)
service.simulate_engagement(campaign_id)  # For demo
```

**Features**:
- Campaign targeting (by score, location, price)
- Simulated email sending (no real emails)
- Engagement tracking (opens, clicks, replies)
- Campaign analytics

### 6. Airflow DAGs

**Location**: `dags/`

Automated pipeline orchestration:

1. **Property Discovery** (`discover_property.py`)
   - Schedule: Every 2 hours
   - Runs property scraper
   - Saves to database

2. **Enrichment** (`enrichment_property.py`)
   - Schedule: Every hour
   - Enriches new properties
   - Updates status to 'enriched'

3. **Scoring** (`score_master.py`)
   - Schedule: Every hour
   - Scores enriched properties
   - Updates status to 'scored'

4. **Document Generation** (`docgen_packet.py`)
   - Schedule: Every 2 hours
   - Generates memos for scored properties
   - Updates status to 'documented'

5. **Email Outreach** (`email_outreach.py`)
   - Schedule: Daily at 9 AM
   - Executes active campaigns
   - Simulates engagement

---

## Demo Walkthrough

### Part 1: Dashboard Overview (5 minutes)

1. Navigate to http://localhost:3000
2. Show **Dashboard** page:
   - Total properties count
   - Enriched/scored percentages
   - High-quality properties (score ≥ 80)
   - Pipeline status visualization
   - Quick actions

### Part 2: Property Discovery (5 minutes)

1. Click **Properties** in navigation
2. Show properties list:
   - Filter by city, status, price range
   - Different property statuses (new, enriched, scored, documented)
   - Property cards with key details

3. Click on a high-scoring property
4. Show property detail page:
   - Full property information
   - Enrichment data section
   - Investment score card
   - Score breakdown by factor
   - Risk assessment

### Part 3: Pipeline Visualization (3 minutes)

1. Click **Pipeline** in navigation
2. Show pipeline flow:
   - Discovery → Enrichment → Scoring → Documentation → Outreach
   - Property counts at each stage
   - Recent DAG runs
   - Error monitoring

### Part 4: Campaign Management (5 minutes)

1. Click **Campaigns** in navigation
2. Show campaigns overview:
   - Total campaigns and stats
   - Campaign cards with metrics
   - Open rates, click rates, reply rates

3. Click **Create Campaign**
4. Create new campaign:
   - Name: "Demo Investor Outreach"
   - Description: "Reaching out to high-value property owners"
   - Template: Investor Outreach

5. Launch campaign (triggers simulated sends)
6. Show engagement metrics

### Part 5: API Capabilities (3 minutes)

1. Navigate to http://localhost:8000/docs
2. Show API documentation:
   - Properties endpoints (CRUD, search, filters)
   - Enrichment endpoints
   - Scoring endpoints
   - Documents endpoints (PDF generation)
   - Campaigns endpoints (execution, logs)
   - Dashboard endpoints (stats, pipeline)

3. Try a few endpoints:
   - GET `/api/properties?city=Las Vegas&min_score=80`
   - GET `/api/dashboard/stats`
   - POST `/api/properties/{id}/generate-memo`

### Part 6: Airflow Orchestration (2 minutes)

1. Navigate to http://localhost:8080
2. Login: `airflow` / `airflow`
3. Show DAGs:
   - All 5 pipeline DAGs
   - Schedules and recent runs
   - Task success/failure status

---

## API Endpoints

### Properties

```
GET    /api/properties              # List properties (with filters)
POST   /api/properties              # Create property
GET    /api/properties/{id}         # Get property details
PUT    /api/properties/{id}         # Update property
DELETE /api/properties/{id}         # Delete property
```

**Filters**: `city`, `state`, `status`, `property_type`, `min_price`, `max_price`, `min_score`, `max_score`, `search`

### Enrichment

```
GET  /api/enrichment/{property_id}     # Get enrichment data
POST /api/enrichment/{property_id}     # Trigger enrichment
```

### Scoring

```
GET  /api/scores/{property_id}         # Get property score
POST /api/scores/{property_id}         # Trigger scoring
GET  /api/scores/leaderboard           # Top-scored properties
```

### Documents

```
GET  /api/properties/{id}/documents    # List property documents
POST /api/properties/{id}/generate-memo # Generate investor memo
GET  /api/properties/{id}/memo.pdf     # Download memo PDF
```

### Campaigns

```
GET  /api/campaigns                    # List campaigns
POST /api/campaigns                    # Create campaign
GET  /api/campaigns/{id}               # Get campaign details
POST /api/campaigns/{id}/send          # Execute campaign
GET  /api/campaigns/{id}/logs          # Get outreach logs
```

### Dashboard

```
GET /api/dashboard/stats               # Overall statistics
GET /api/dashboard/pipeline            # Pipeline status
```

---

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres psql -U airflow -d airflow -c "SELECT 1;"

# Restart services
docker-compose restart
```

### Airflow DAGs Not Running

```bash
# Check Airflow scheduler
docker-compose logs airflow-scheduler

# Trigger DAG manually
docker-compose exec airflow-scheduler airflow dags trigger discover_property
```

### Frontend Not Loading

```bash
# Check API is running
curl http://localhost:8000/health

# Check frontend dev server
cd frontend
npm run dev
```

### PDF Generation Fails

Install WeasyPrint for PDF generation:

```bash
pip install weasyprint
# OR
pip install pdfkit
```

If neither works, the system will save as HTML instead.

### No Demo Data

Run the generator again:

```bash
python scripts/generate_demo_data.py
```

---

## Production Considerations

For production deployment:

1. **Security**:
   - Change default passwords
   - Add authentication/authorization
   - Use HTTPS
   - Secure API keys

2. **Scalability**:
   - Use production database (managed PostgreSQL)
   - Scale Airflow workers
   - Add Redis for caching
   - Use CDN for frontend

3. **Real Data**:
   - Integrate real MLS APIs
   - Connect to actual assessor databases
   - Use real email service (SendGrid, Mailgun)
   - Implement actual ML models for scoring

4. **Monitoring**:
   - Add logging (ELK stack)
   - Application monitoring (Datadog, New Relic)
   - Error tracking (Sentry)
   - Uptime monitoring

---

## Support

For issues or questions:

- Check logs: `docker-compose logs [service]`
- Review API docs: http://localhost:8000/docs
- Check Airflow logs: http://localhost:8080

---

**Platform Version**: 1.0.0
**Last Updated**: January 2025
