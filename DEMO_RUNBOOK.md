## Real Estate OS - Demo Runbook

**Comprehensive guide to running and interacting with the platform demo**

---

## Quick Start (2 Minutes)

```bash
# 1. Start the demo (full-consolidation branch)
./demo_quickstart.sh

# 2. Run interactive demo
./demo_interactive.sh

# 3. Open API docs
# Visit http://localhost:8000/docs in your browser
```

**Done!** You now have a running demo with 140+ API endpoints.

---

## Prerequisites

### System Requirements
- **Docker Engine** 20.10+ with Compose V2
- **RAM:** 4GB free (8GB recommended)
- **Disk:** 10GB free
- **Network:** Internet access for Docker image pulls
- **Ports:** 8000, 5432, 6379, 8025, 5555, 9001 available

### Tools (Optional)
- `curl` - For API calls
- `jq` - For JSON formatting
- Browser - For API docs and UI tools

### Check Prerequisites
```bash
# Docker
docker --version  # Should be 20.10+
docker compose version  # Should be v2.x.x

# Ports available
netstat -tuln | grep -E ':(8000|5432|6379|8025|5555|9001)'
# Should return empty (ports not in use)

# Disk space
df -h .  # Should show >10GB free
```

---

## Branch Selection

### Option 1: full-consolidation (Recommended)
**Best for:** Complete feature demonstration, testing, production preview

**Stats:**
- 152 declared endpoints
- 21 routers (auth, properties, workflow, automation, etc.)
- 20 database models
- 47 test files
- Production middleware (rate limiting, ETag, metrics, DLQ)
- Complete mock providers

**Start:**
```bash
./demo_quickstart.sh full-consolidation
```

---

### Option 2: mock-providers-twilio (Fallback)
**Best for:** Quick demos, lighter resource usage, troubleshooting

**Stats:**
- 132 declared endpoints
- 16 routers
- 20 database models
- 3 test files
- Mock providers focused

**Start:**
```bash
./demo_quickstart.sh mock-providers-twilio
```

---

## Step-by-Step Manual Demo

### 1. Environment Setup

```bash
# Checkout branch
git fetch --all --prune
git checkout -B full-consolidation origin/claude/full-consolidation-011CUo8XMMdfTgWrwjpAVcE1

# Configure environment
cp .env.mock .env
echo "MOCK_MODE=true" >> .env

# Start stack
docker compose up -d --wait

# Check status
docker compose ps
```

**Expected output:**
```
NAME                STATUS              PORTS
api                 Up (healthy)        0.0.0.0:8000->8000/tcp
db                  Up (healthy)        0.0.0.0:5432->5432/tcp
redis               Up (healthy)        0.0.0.0:6379->6379/tcp
mailhog             Up                  0.0.0.0:8025->8025/tcp
```

---

### 2. Health Checks

```bash
# Basic health
curl http://localhost:8000/healthz
# {"status":"ok"}

# OpenAPI endpoint count
curl -s http://localhost:8000/docs/openapi.json | jq '.paths | keys | length'
# 152 (or similar large number)

# Check for errors
docker compose logs api --tail=100 | grep -i error
# Should be minimal/none
```

---

### 3. Run Migrations (if needed)

```bash
# Apply migrations
docker compose exec api alembic upgrade head

# Check current migration
docker compose exec api alembic current
```

---

### 4. Authentication Flow

#### Register a User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "demo@example.com",
    "password": "SecurePass123!",
    "name": "Demo User"
  }' | jq .
```

**Expected response:**
```json
{
  "id": "uuid-here",
  "email": "demo@example.com",
  "name": "Demo User",
  "role": "user",
  "created_at": "2025-11-09T..."
}
```

#### Login
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "demo@example.com",
    "password": "SecurePass123!"
  }' | jq -r '.access_token')

echo "Token: $TOKEN"
```

**Export token for subsequent calls:**
```bash
export TOKEN="your-token-here"
```

---

### 5. Property Management

#### Create a Property
```bash
curl -X POST http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "address": "456 Oak Avenue",
    "city": "Austin",
    "state": "TX",
    "zip": "78701",
    "property_type": "single_family",
    "bedrooms": 4,
    "bathrooms": 3,
    "sqft": 2400,
    "lot_size": 8000,
    "year_built": 2018,
    "status": "active"
  }' | jq .
```

**Expected response:**
```json
{
  "id": "prop-uuid-123",
  "address": "456 Oak Avenue",
  "city": "Austin",
  "state": "TX",
  "enrichment_status": "pending",
  "created_at": "2025-11-09T...",
  ...
}
```

Save the property ID:
```bash
PROPERTY_ID="prop-uuid-123"
```

#### List Properties
```bash
curl http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Get Property Details (with enrichment)
```bash
curl http://localhost:8000/api/v1/properties/$PROPERTY_ID \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Look for enriched fields:**
- `assessed_value`
- `market_value`
- `tax_amount`
- `owner_name`
- `last_sale_date`
- `neighborhood_data`

#### Update Property
```bash
curl -X PATCH http://localhost:8000/api/v1/properties/$PROPERTY_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "under_contract",
    "notes": "Buyer submitted offer"
  }' | jq .
```

#### Delete Property
```bash
curl -X DELETE http://localhost:8000/api/v1/properties/$PROPERTY_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

### 6. Communications (Mock Mode)

#### Send Email
```bash
curl -X POST http://localhost:8000/api/v1/communications/email \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "to": "investor@example.com",
    "subject": "New Property Match",
    "template": "property_alert",
    "data": {
      "property_address": "456 Oak Avenue",
      "price": "$850,000",
      "beds": 4,
      "baths": 3
    }
  }' | jq .
```

**View mock emails:**
Open http://localhost:8025 in your browser (MailHog interface)

#### Send SMS
```bash
curl -X POST http://localhost:8000/api/v1/communications/sms \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "to": "+15125551234",
    "message": "New property alert: 456 Oak Ave, Austin TX - $850K"
  }' | jq .
```

---

### 7. Workflow Automation

#### Get Next Best Action
```bash
curl http://localhost:8000/api/v1/workflow/next-best-action \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Example response:**
```json
{
  "action": "follow_up_investor",
  "priority": "high",
  "context": {
    "investor_id": "inv-123",
    "property_id": "prop-456",
    "last_contact": "2025-11-01"
  },
  "suggested_templates": ["follow_up_email", "property_update"]
}
```

#### Create a Task
```bash
curl -X POST http://localhost:8000/api/v1/workflow/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Schedule property viewing",
    "description": "Coordinate with buyer for 456 Oak Ave",
    "priority": "high",
    "due_date": "2025-11-15",
    "assigned_to": "demo@example.com"
  }' | jq .
```

#### List Smart Lists
```bash
curl http://localhost:8000/api/v1/workflow/smart-lists \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

### 8. Quick Wins

#### List Templates
```bash
curl http://localhost:8000/api/v1/quick-wins/templates \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Generate Document
```bash
curl -X POST http://localhost:8000/api/v1/quick-wins/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "template": "investment_memo",
    "property_id": "'$PROPERTY_ID'",
    "format": "pdf"
  }' | jq .
```

**Download generated PDF:**
```bash
DOCUMENT_URL=$(curl -s -X POST http://localhost:8000/api/v1/quick-wins/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"template":"investment_memo","property_id":"'$PROPERTY_ID'"}' | jq -r '.download_url')

curl "$DOCUMENT_URL" -o investment_memo.pdf
```

---

### 9. Real-time Events (SSE)

#### Open SSE Stream (in separate terminal)
```bash
curl -N -H "Accept: text/event-stream" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/events/stream
```

**Then in another terminal, trigger events:**
```bash
# Create a property (triggers property.created event)
curl -X POST http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"address":"789 Pine St","city":"Austin","state":"TX","zip":"78701"}'
```

**You should see in the SSE terminal:**
```
event: property.created
data: {"id":"prop-789","address":"789 Pine St",...}

event: enrichment.started
data: {"property_id":"prop-789","sources":["assessor"]}
```

---

### 10. Background Jobs

#### List Jobs
```bash
curl http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Trigger Enrichment Job
```bash
curl -X POST http://localhost:8000/api/v1/jobs/enrich \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "property_id": "'$PROPERTY_ID'",
    "sources": ["assessor", "market_data", "demographics"]
  }' | jq .
```

**Check job status:**
```bash
JOB_ID="job-uuid-here"
curl http://localhost:8000/api/v1/jobs/$JOB_ID \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**View Celery Flower (job monitoring):**
Open http://localhost:5555 in your browser

---

### 11. Portfolio Analytics

#### Portfolio Overview
```bash
curl http://localhost:8000/api/v1/portfolio/overview \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Example response:**
```json
{
  "total_properties": 15,
  "total_value": "$12,500,000",
  "avg_appreciation": "8.2%",
  "top_markets": ["Austin", "San Francisco", "Denver"],
  "deals_in_pipeline": 8
}
```

#### Deal Economics
```bash
curl http://localhost:8000/api/v1/portfolio/deals/economics \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

### 12. Admin & System

#### System Health (Detailed)
```bash
curl http://localhost:8000/api/v1/admin/health \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Example response:**
```json
{
  "status": "healthy",
  "components": {
    "database": "connected",
    "redis": "connected",
    "celery": "active",
    "email": "mock_active",
    "sms": "mock_active"
  },
  "uptime": "2h 15m",
  "version": "1.0.0"
}
```

#### Dead Letter Queue (DLQ)
```bash
# List failed jobs
curl http://localhost:8000/api/v1/admin/dlq \
  -H "Authorization: Bearer $TOKEN" | jq .

# Retry failed job
curl -X POST http://localhost:8000/api/v1/admin/dlq/retry/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Web Interfaces

### API Documentation (Swagger UI)
- **URL:** http://localhost:8000/docs
- **Features:** Interactive API exploration, try endpoints directly
- **Auth:** Click "Authorize" and enter your Bearer token

### ReDoc (Alternative API Docs)
- **URL:** http://localhost:8000/redoc
- **Features:** Clean, read-only documentation

### MailHog (Mock Email Capture)
- **URL:** http://localhost:8025
- **Features:** View all outbound emails, test templates

### Flower (Celery Monitoring)
- **URL:** http://localhost:5555
- **Features:** Monitor background jobs, task queue status

### MinIO Console (Mock Storage)
- **URL:** http://localhost:9001
- **Credentials:** See `.env.mock` for MINIO_ROOT_USER/PASSWORD
- **Features:** Browse uploaded files, test storage

---

## Troubleshooting

### Issue: API won't start

**Check logs:**
```bash
docker compose logs api --tail=100
```

**Common causes:**
- Port 8000 already in use: `lsof -i :8000` (kill or change port)
- Database not ready: Wait 30s and try again
- Environment vars missing: Check `.env` file exists

**Fix:**
```bash
docker compose down -v
docker compose up -d --wait
```

---

### Issue: Only 2 endpoints showing

**Check OpenAPI count:**
```bash
curl -s http://localhost:8000/docs/openapi.json | jq '.paths | keys | length'
```

**If < 10:**
- Routers not mounted in `api/main.py`
- Check for import errors: `docker compose logs api | grep -i error`
- Verify branch: `git branch --show-current`

**Fix:**
```bash
# Ensure you're on the right branch
git checkout full-consolidation
docker compose restart api
```

---

### Issue: 401 Unauthorized on all endpoints

**Token expired or missing:**
```bash
# Re-login and get fresh token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"SecurePass123!"}' | jq -r '.access_token')

export TOKEN
```

---

### Issue: No enrichment data showing

**Enrichment may be async:**
```bash
# Wait a few seconds, then check property again
sleep 5
curl http://localhost:8000/api/v1/properties/$PROPERTY_ID \
  -H "Authorization: Bearer $TOKEN" | jq .enrichment_data
```

**Check Celery worker logs:**
```bash
docker compose logs celery-worker --tail=50
```

---

### Issue: Mock emails not showing in MailHog

**Verify MOCK_MODE:**
```bash
docker compose exec api env | grep MOCK_MODE
# Should show: MOCK_MODE=true
```

**Check email provider:**
```bash
docker compose logs api | grep -i "email\|provider"
# Should see: "Using MockEmailProvider"
```

**Restart with clean state:**
```bash
docker compose down -v
cp .env.mock .env
docker compose up -d --wait
```

---

### Issue: Database connection errors

**Check Postgres is running:**
```bash
docker compose ps db
# Should show "Up (healthy)"
```

**Test connection:**
```bash
docker compose exec db psql -U postgres -c "SELECT 1;"
```

**Reset database:**
```bash
docker compose down -v
docker compose up -d db --wait
docker compose exec api alembic upgrade head
```

---

### Issue: Migrations failing

**Check migration status:**
```bash
docker compose exec api alembic current
docker compose exec api alembic heads
```

**If multiple heads:**
```bash
# Merge heads
docker compose exec api alembic merge heads -m "Merge migration branches"
docker compose exec api alembic upgrade head
```

**Reset migrations (destructive):**
```bash
docker compose down -v
docker compose up -d db --wait
docker compose exec api alembic upgrade head
```

---

## Advanced Usage

### Seed Demo Data

Create `scripts/demo/seed.sh`:
```bash
#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@demo.com","password":"password123"}' | jq -r '.access_token')

# Create 10 sample properties
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/properties \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d "{
      \"address\": \"$i00 Demo St\",
      \"city\": \"Austin\",
      \"state\": \"TX\",
      \"zip\": \"7870$i\",
      \"property_type\": \"single_family\"
    }"
  sleep 1
done
```

Run:
```bash
chmod +x scripts/demo/seed.sh
./scripts/demo/seed.sh
```

---

### Custom Docker Compose

Create `docker-compose.override.yml` for local customizations:
```yaml
version: '3.8'

services:
  api:
    ports:
      - "9000:8000"  # Different port
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
```

---

### Shell Access

```bash
# API container
docker compose exec api bash

# Inside container:
python
>>> from api.database import engine
>>> from sqlalchemy import text
>>> with engine.connect() as conn:
...     result = conn.execute(text("SELECT COUNT(*) FROM properties"))
...     print(result.scalar())
```

---

### Database Access

```bash
# psql shell
docker compose exec db psql -U postgres -d realestate

# Inside psql:
\dt                    -- List tables
SELECT * FROM properties LIMIT 5;
\q                     -- Quit
```

---

## Performance Tips

### 1. Reduce log verbosity
```bash
# In .env
LOG_LEVEL=WARNING  # Instead of INFO or DEBUG
```

### 2. Skip non-essential services
```bash
# Only start API and DB
docker compose up -d api db --wait
```

### 3. Use smaller dataset
```bash
# Limit enrichment sources
# In API calls, only request necessary data
```

### 4. Monitor resource usage
```bash
docker stats

# Limit container resources
docker compose up -d --scale celery-worker=1
```

---

## Cleanup

### Stop demo (keep data)
```bash
docker compose stop
```

### Stop and remove containers (keep volumes)
```bash
docker compose down
```

### Complete cleanup (removes all data)
```bash
docker compose down -v --remove-orphans
docker system prune -f
```

---

## Next Steps

1. **Explore API docs:** http://localhost:8000/docs
2. **Review code:** Browse `api/routers/` for implementation
3. **Run tests:** `docker compose exec api pytest`
4. **Customize:** Edit endpoints, add features
5. **Deploy:** See deployment guides for production

---

## Support Resources

- **API Docs:** http://localhost:8000/docs
- **Scripts:** `./demo_quickstart.sh`, `./demo_interactive.sh`
- **Logs:** `docker compose logs -f api`
- **Verification:** `./scripts/runtime_verification_enhanced.sh`

---

## Quick Reference

```bash
# Start
./demo_quickstart.sh

# Interactive demo
./demo_interactive.sh

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"SecurePass123!"}' | jq -r '.access_token')

# Create property
curl -X POST http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"address":"123 Main St","city":"Austin","state":"TX","zip":"78701"}'

# List properties
curl http://localhost:8000/api/v1/properties -H "Authorization: Bearer $TOKEN"

# View logs
docker compose logs -f api

# Stop
docker compose down -v
```

---

**Demo runbook version:** 1.0.0
**Last updated:** 2025-11-09
**Branch:** full-consolidation / mock-providers-twilio
