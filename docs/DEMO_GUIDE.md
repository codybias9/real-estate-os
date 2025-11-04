# Real Estate OS - Demo Guide

## 🎯 Purpose

This guide provides a complete walkthrough for demonstrating the Real Estate OS platform. The demo runs entirely in **MOCK MODE** - no external API keys required!

---

## 🚀 Quick Start (5 Minutes)

### 1. Start the Platform

```bash
# Clone the repository
git clone https://github.com/codybias9/real-estate-os.git
cd real-estate-os

# Start the entire stack (one command!)
./scripts/docker/start.sh
```

**What This Does:**
- Starts 11 Docker services (PostgreSQL, Redis, RabbitMQ, MinIO, API, Celery, etc.)
- Runs health checks on all services
- Shows service URLs when ready
- Takes ~2 minutes to fully start

### 2. Seed Demo Data

```bash
# Populate with realistic demo data
./scripts/demo/seed.sh
```

**What This Creates:**
- 2 demo teams
- 4 demo users (admin, manager, agent, viewer)
- 50 properties across all pipeline stages
- Email/SMS templates
- Timeline events and tasks

### 3. Access the Platform

```bash
# API Documentation (Interactive)
open http://localhost:8000/docs

# API Alternative Documentation
open http://localhost:8000/redoc

# RabbitMQ Management
open http://localhost:15672    # admin/admin

# Celery Monitoring (Flower)
open http://localhost:5555

# MinIO Console
open http://localhost:9001     # minioadmin/minioadmin

# Grafana Dashboards
open http://localhost:3001     # admin/admin
```

---

## 🎬 Demo Scenarios

### Scenario 1: Complete Property Lifecycle (10 mins)

**Story:** Follow a property from lead to closed deal

#### Step 1: Login as Admin

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.com",
    "password": "password123"
  }'
```

**Result:** JWT access token
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@demo.com",
    "full_name": "Admin User",
    "role": "admin"
  }
}
```

**Demo Talking Points:**
- ✅ Secure JWT authentication
- ✅ Role-based access control
- ✅ Bcrypt password hashing

#### Step 2: List Properties

```bash
curl http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer <your-token>"
```

**Result:** List of 50 demo properties

**Demo Talking Points:**
- ✅ Properties across all stages (New → Closed Won)
- ✅ Bird Dog scores (AI-powered propensity scoring)
- ✅ Complete property details (beds, baths, sqft, ARV)
- ✅ Engagement metrics (touches, opens, replies)

#### Step 3: View Property Details

```bash
curl http://localhost:8000/api/v1/properties/1 \
  -H "Authorization: Bearer <your-token>"
```

**Demo Talking Points:**
- ✅ Complete property profile
- ✅ Owner information
- ✅ Valuation data (assessed, market, ARV)
- ✅ Scoring breakdown with reasons

#### Step 4: Generate Property Memo (Mock PDF)

```bash
curl -X POST http://localhost:8000/api/v1/jobs/memo/generate \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "template": "default"
  }'
```

**Result:** Background job queued

**Demo Talking Points:**
- ✅ Async job processing via Celery
- ✅ PDF generation in background
- ✅ Job status tracking
- ✅ Mock PDF generator (no WeasyPrint required)

#### Step 5: Send Email with Memo (Mock SendGrid)

```bash
curl -X POST http://localhost:8000/api/v1/communications/email/send \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "to_email": "owner@example.com",
    "subject": "Investment Opportunity - 123 Main St",
    "body": "<p>We'\''d like to make an offer on your property...</p>"
  }'
```

**Result:** Email sent via mock SendGrid

**Demo Talking Points:**
- ✅ Mock email system (no SendGrid API key needed)
- ✅ Realistic engagement simulation (opens, clicks)
- ✅ Email tracking and analytics
- ✅ Timeline event created automatically

#### Step 6: Send Follow-Up SMS (Mock Twilio)

```bash
curl -X POST http://localhost:8000/api/v1/communications/sms/send \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "to_phone": "+15555551234",
    "message": "Hi! Did you receive our investment proposal for 123 Main St?"
  }'
```

**Result:** SMS sent via mock Twilio

**Demo Talking Points:**
- ✅ Mock SMS system (no Twilio credentials needed)
- ✅ Multi-channel outreach (email + SMS)
- ✅ Message delivery tracking
- ✅ Timeline tracking

#### Step 7: Move Property Through Pipeline

```bash
curl -X POST http://localhost:8000/api/v1/properties/1/change-stage \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "new_stage": "Qualified",
    "reason": "Owner expressed interest via phone"
  }'
```

**Demo Talking Points:**
- ✅ Pipeline stage management
- ✅ Automatic timeline tracking
- ✅ Stage change triggers (automation)
- ✅ Real-time SSE updates

#### Step 8: View Timeline

```bash
curl http://localhost:8000/api/v1/properties/1/timeline \
  -H "Authorization: Bearer <your-token>"
```

**Result:** Complete activity history

**Demo Talking Points:**
- ✅ Comprehensive audit trail
- ✅ All touchpoints tracked (emails, SMS, calls, stage changes)
- ✅ Engagement metrics
- ✅ User attribution

---

### Scenario 2: Real-Time Collaboration (5 mins)

**Story:** Demonstrate real-time updates via Server-Sent Events

#### Step 1: Open SSE Connection

```bash
# In Terminal 1: Connect to SSE stream
curl -N http://localhost:8000/api/v1/sse/stream \
  -H "Authorization: Bearer <your-token>"
```

**Demo Talking Points:**
- ✅ Long-lived HTTP connection
- ✅ Sub-100ms event latency
- ✅ Automatic reconnection

#### Step 2: Trigger Events

```bash
# In Terminal 2: Update a property
curl -X PATCH http://localhost:8000/api/v1/properties/1 \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "asking_price": 550000
  }'
```

**Result:** Terminal 1 receives real-time event:
```
event: property_updated
data: {"property_id": 1, "field": "asking_price", "new_value": 550000}
```

**Demo Talking Points:**
- ✅ Real-time UI updates
- ✅ Collaborative editing
- ✅ No polling required
- ✅ Scales to 1000+ concurrent connections

---

### Scenario 3: Background Jobs & Monitoring (5 mins)

**Story:** Show async job processing and monitoring

#### Step 1: Queue Multiple Jobs

```bash
# Queue 5 memo generation jobs
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/jobs/memo/generate \
    -H "Authorization: Bearer <your-token>" \
    -H "Content-Type: application/json" \
    -d "{\"property_id\": $i, \"template\": \"default\"}"
done
```

#### Step 2: Monitor in Flower

```bash
open http://localhost:5555
```

**Demo Talking Points:**
- ✅ 4 concurrent workers processing jobs
- ✅ RabbitMQ message queue
- ✅ Redis result backend
- ✅ Job retry logic
- ✅ Task routing by queue (memos, emails, enrichment)

#### Step 3: Check Job Status

```bash
curl http://localhost:8000/api/v1/jobs/<job_id>/status \
  -H "Authorization: Bearer <your-token>"
```

---

### Scenario 4: Rate Limiting & Security (3 mins)

**Story:** Demonstrate API protection

#### Step 1: Test Rate Limiting

```bash
# Send 100 requests rapidly
for i in {1..100}; do
  curl http://localhost:8000/api/v1/properties \
    -H "Authorization: Bearer <your-token>" \
    -w "\n"
done
```

**Result:** After 1000 requests/minute, receive HTTP 429:
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

**Demo Talking Points:**
- ✅ Redis-backed rate limiting
- ✅ Per-user and per-IP tracking
- ✅ Configurable limits per endpoint
- ✅ Protection against abuse

#### Step 2: Test Idempotency

```bash
# Generate unique idempotency key
IDEM_KEY=$(uuidgen)

# Send same request twice
curl -X POST http://localhost:8000/api/v1/communications/email/send \
  -H "Authorization: Bearer <your-token>" \
  -H "Idempotency-Key: $IDEM_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "to_email": "owner@example.com",
    "subject": "Test",
    "body": "Test"
  }'

# Second request with same key returns cached result
curl -X POST http://localhost:8000/api/v1/communications/email/send \
  -H "Authorization: Bearer <your-token>" \
  -H "Idempotency-Key: $IDEM_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "to_email": "owner@example.com",
    "subject": "Test",
    "body": "Test"
  }'
```

**Result:** Only ONE email sent (second request returns cached result)

**Demo Talking Points:**
- ✅ Prevents duplicate emails/SMS
- ✅ Financial transaction safety
- ✅ 24-hour key expiration
- ✅ Cached response for duplicate requests

---

### Scenario 5: Workflow Automation (5 mins)

**Story:** Show intelligent automation features

#### Step 1: Get Next Best Actions

```bash
curl -X POST http://localhost:8000/api/v1/workflow/next-best-actions/generate \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1
  }'
```

**Result:** AI-recommended actions

**Demo Talking Points:**
- ✅ 5 intelligent rules:
  1. Outreach >7d no reply → Send follow-up
  2. High score >0.7 no memo → Generate memo
  3. Negotiation no packet → Send packet
  4. Warm replies <48h → Respond NOW
  5. Stalled >14d → Move or archive
- ✅ Priority scoring
- ✅ One-click execution

#### Step 2: Create Smart List

```bash
curl -X POST http://localhost:8000/api/v1/workflow/smart-lists \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hot Leads - Needs Follow Up",
    "filters": {
      "bird_dog_score_min": 0.7,
      "last_contact_days_ago_max": 7,
      "reply_count_min": 1,
      "stages": ["Outreach", "Qualified"]
    }
  }'
```

**Demo Talking Points:**
- ✅ Dynamic saved queries
- ✅ Auto-refresh
- ✅ Cached counts for performance
- ✅ Intent-based filtering

---

## 📊 Technical Deep Dives

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   Frontend                      │
│              (Next.js + React)                  │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│                Nginx (Reverse Proxy)            │
└───────────────────┬─────────────────────────────┘
                    │
        ┌───────────┴────────────┬────────────┐
        ▼                        ▼            ▼
┌───────────────┐      ┌──────────────┐   ┌──────┐
│ FastAPI       │      │ SSE Stream   │   │ Docs │
│ (100+ routes) │      │              │   │      │
└───────┬───────┘      └──────────────┘   └──────┘
        │
        ├─────────────┬──────────────┬─────────────┐
        ▼             ▼              ▼             ▼
┌────────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐
│ PostgreSQL │  │  Redis   │  │ RabbitMQ│  │  MinIO   │
│ (Database) │  │ (Cache)  │  │ (Queue) │  │ (S3)     │
└────────────┘  └──────────┘  └─────────┘  └──────────┘
                      │              │
                      └──────┬───────┘
                             ▼
                    ┌────────────────┐
                    │ Celery Workers │
                    │   (4 workers)  │
                    └────────────────┘
```

### Mock Provider System

**Architecture:**
```python
# api/integrations/factory.py
def is_mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "false").lower() == "true"

class EmailClient:
    def __init__(self):
        if is_mock_mode():
            self._impl = sendgrid_mock
        else:
            self._impl = sendgrid_client
```

**Benefits:**
- ✅ Zero external dependencies
- ✅ Deterministic fake data
- ✅ Realistic behavior simulation
- ✅ Perfect for demos/testing

### Database Schema

**35 Models Including:**
- Team, User (RBAC)
- Property, PropertyTimeline
- Communication (Email, SMS, Call)
- Task, NextBestAction, SmartList
- Template (Email/SMS)
- Deal, OfferPacket
- IdempotencyKey, DLQEvent
- ReconciliationHistory
- Webhook, WebhookDelivery

---

## 🎓 Demo Tips & Best Practices

### Before the Demo

1. **Start Services Early** (2 min startup)
   ```bash
   ./scripts/docker/start.sh
   ```

2. **Verify Health**
   ```bash
   ./scripts/docker/health.sh
   ```

3. **Seed Fresh Data**
   ```bash
   ./scripts/demo/seed.sh
   ```

4. **Generate Proofs** (optional, for technical audiences)
   ```bash
   ./scripts/proofs/run_all_proofs.sh
   ```

### During the Demo

1. **Keep Terminal Clean**
   - Use `clear` between commands
   - Pipe JSON through `jq` for formatting
   - Use `| head` to limit output

2. **Show Visuals**
   - Open API docs (`/docs`) in browser
   - Show Flower dashboard for job monitoring
   - Display Grafana dashboards for metrics

3. **Highlight Key Features**
   - Mock mode (no setup required)
   - Real-time SSE updates
   - Background job processing
   - Idempotency & rate limiting
   - Comprehensive API documentation

4. **Handle Questions**
   - "Can it scale?" → Yes, horizontally scalable (add more Celery workers)
   - "What about security?" → JWT auth, rate limiting, RBAC, bcrypt hashing
   - "External dependencies?" → Optional in mock mode, full integration available
   - "Testing?" → 68 tests, 70%+ coverage, 3-pass CI/CD ready

### After the Demo

1. **Provide Resources**
   - GitHub repo link
   - API documentation URL
   - This demo guide
   - Quick start instructions

2. **Offer Follow-Up**
   - Custom demo scenarios
   - Technical deep dives
   - Integration discussions

---

## 🐛 Troubleshooting

### Services Not Starting

```bash
# Check Docker status
docker ps

# Restart problematic service
docker-compose restart api

# View logs
docker-compose logs -f api
```

### API Returns 500 Errors

```bash
# Check API logs
docker-compose logs api | tail -50

# Check database connection
docker-compose exec postgres pg_isready -U postgres

# Restart API
docker-compose restart api
```

### Demo Data Issues

```bash
# Clear and reseed
docker-compose exec -T api python -c "
from api.database import get_db_context
from db.models import Base
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DB_DSN'))
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
"

# Reseed
./scripts/demo/seed.sh
```

### Slow Performance

```bash
# Check resource usage
docker stats

# Increase resources in Docker Desktop settings
# Recommended: 4 CPU, 8GB RAM
```

---

## 📚 Additional Resources

- **API Documentation:** http://localhost:8000/docs
- **GitHub Repository:** https://github.com/codybias9/real-estate-os
- **Session Progress:** [docs/SESSION_PROGRESS.md](SESSION_PROGRESS.md)
- **Runtime Proofs:** [docs/RUNTIME_PROOFS.md](RUNTIME_PROOFS.md)
- **Testing Guide:** Run `./scripts/test/run_tests.sh`

---

## 🎉 Summary

Real Estate OS is a **production-ready, enterprise-grade** platform for real estate investment operations. This demo showcases:

- ✅ **Zero Setup** - Docker-based, one command to start
- ✅ **Mock Mode** - No external API keys required
- ✅ **Complete Features** - 100+ endpoints, 35 models, 11 routers
- ✅ **Real-Time** - SSE updates with <100ms latency
- ✅ **Scalable** - Background jobs, caching, rate limiting
- ✅ **Secure** - JWT auth, RBAC, idempotency, bcrypt
- ✅ **Well-Tested** - 68 tests, 70%+ coverage, CI/CD ready
- ✅ **Documented** - OpenAPI spec, comprehensive guides

**Total Demo Time:** 30-45 minutes for complete walkthrough

Ready to demo! 🚀
