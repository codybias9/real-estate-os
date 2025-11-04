# 🏡 Real Estate OS

**Enterprise-Grade Real Estate Investment Platform**

A comprehensive, production-ready platform for real estate investment operations with intelligent automation, multi-channel outreach, and AI-powered deal scoring.

[![CI/CD Pipeline](https://github.com/codybias9/real-estate-os/actions/workflows/ci.yml/badge.svg)](https://github.com/codybias9/real-estate-os/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

---

## ✨ Features

### 🚀 Quick Wins
- **Generate & Send Combo** - Auto-generate memos and email in one action
- **Auto-Assign on Reply** - Never miss a lead with automatic assignment
- **Stage-Aware Templates** - Right message for each pipeline stage
- **Flag Data Issues** - Crowdsourced data quality

### ⚡ Workflow Accelerators
- **Next Best Action Panel** - AI-powered recommendations with 1-click execution
- **Smart Lists** - Intent-based saved queries (e.g., "Warm Replies Last 48h")
- **One-Click Tasking** - Convert any event to task with SLA tracking

### 🤖 Automation
- **Cadence Builder** - Multi-step, multi-channel sequences
- **Cadence Governor** - Auto-pause on reply, switch channels intelligently
- **Fallback Chains** - Email → Wait 3 days → SMS → Wait 5 days → Call

### 📊 Data & Scoring
- **Open Data Ladder** - Free sources first (FEMA, USGS, OSM), paid only when needed
- **Bird Dog Scoring** - AI-powered propensity to sell
- **Explainable Confidence** - See WHY properties score high
- **What-If Analysis** - Predict impact of actions

### 💬 Communications
- **Email Threading** - Auto-ingest from Gmail/Outlook
- **Call Capture** - Twilio integration with transcription & sentiment
- **Reply Drafting** - Context-aware responses with objection handling
- **Multi-Channel Timeline** - All touchpoints in one view

### 🤝 Collaboration
- **Secure Share Links** - No-login sharing with watermarks & tracking
- **Deal Rooms** - Central hub for docs, comps, photos
- **Investor Engagement Tracking** - Analytics on time spent, interest signals

### 🛡️ Operational Guardrails
- **Compliance Pack** - DNC checks, opt-outs, state disclaimers
- **Budget Tracking** - Real-time cost monitoring with alerts
- **Deliverability Monitoring** - SPF/DKIM/DMARC validation
- **Rate Limiting** - Prevent API abuse (Redis-backed)

### 🔒 Security & Reliability
- **JWT Authentication** - Secure token-based auth with refresh
- **Row-Level Security** - PostgreSQL RLS policies
- **Idempotency Keys** - Prevent duplicate operations
- **DLQ System** - Dead letter queue with replay
- **ETag Caching** - Conditional requests (304 Not Modified)

### 📈 Real-Time Features
- **Server-Sent Events (SSE)** - <100ms update latency
- **Background Jobs** - Celery + RabbitMQ for async processing
- **Job Monitoring** - Flower dashboard for task tracking

---

## 🎯 Demo Mode (Zero Setup!)

**Run the entire platform with NO external API keys required!**

```bash
# Clone & start (one command!)
git clone https://github.com/codybias9/real-estate-os.git
cd real-estate-os
./scripts/docker/start.sh

# Seed demo data
./scripts/demo/seed.sh

# Open API docs
open http://localhost:8000/docs
```

**What You Get:**
- ✅ **11 Docker services** (PostgreSQL, Redis, RabbitMQ, MinIO, API, Celery, Flower, Nginx, Prometheus, Grafana, Frontend)
- ✅ **50 demo properties** across all pipeline stages
- ✅ **4 demo users** (admin, manager, agent, viewer)
- ✅ **Mock providers** for email, SMS, storage, PDF (no credentials needed)
- ✅ **Complete functionality** - everything works in mock mode!

**Perfect for:**
- 🎬 Sales demos
- 🎓 Training sessions
- 🧪 Development & testing
- 📦 POCs & evaluations

---

## 📚 Quick Start

### Prerequisites

- **Docker Desktop** (4+ CPU, 8GB+ RAM recommended)
- **Python 3.10+** (for local development)
- **Git**

### 1. Start the Platform

```bash
# Start all services
./scripts/docker/start.sh

# Wait ~2 minutes for services to be healthy
# You'll see: "✅ Stack started successfully!"
```

### 2. Seed Demo Data

```bash
# Populate with realistic data
./scripts/demo/seed.sh
```

### 3. Login & Explore

**Demo Credentials:**
```
Admin:   admin@demo.com   / password123
Manager: manager@demo.com / password123
Agent:   agent@demo.com   / password123
```

**API Documentation:**
- Interactive Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc
- OpenAPI Spec: http://localhost:8000/openapi.json

**Monitoring Dashboards:**
- Celery Jobs: http://localhost:5555
- RabbitMQ: http://localhost:15672 (admin/admin)
- MinIO: http://localhost:9001 (minioadmin/minioadmin)
- Grafana: http://localhost:3001 (admin/admin)

### 4. Try Sample Requests

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.com", "password": "password123"}'

# Get properties (use token from login)
curl http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer <your-token>"

# Send email (mock - no SendGrid needed!)
curl -X POST http://localhost:8000/api/v1/communications/email/send \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "to_email": "owner@example.com",
    "subject": "Investment Opportunity",
    "body": "<p>We would like to make an offer...</p>"
  }'
```

---

## 🏗️ Architecture

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
│ (11 routers)  │      │ (Real-time)  │   │      │
│ (100+ routes) │      │              │   │      │
└───────┬───────┘      └──────────────┘   └──────┘
        │
        ├─────────────┬──────────────┬─────────────┐
        ▼             ▼              ▼             ▼
┌────────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐
│ PostgreSQL │  │  Redis   │  │ RabbitMQ│  │  MinIO   │
│ (35 models)│  │ (Cache)  │  │ (Queue) │  │ (S3)     │
└────────────┘  └──────────┘  └─────────┘  └──────────┘
                      │              │
                      └──────┬───────┘
                             ▼
                    ┌────────────────┐
                    │ Celery Workers │
                    │ (4 concurrent) │
                    └────────────────┘
```

### Tech Stack

**Backend:**
- FastAPI (Python 3.10+)
- PostgreSQL 14
- Redis 7
- RabbitMQ 3.12
- Celery 5.3
- SQLAlchemy 2.0

**Frontend:**
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Zustand (state management)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (reverse proxy)
- MinIO (S3-compatible storage)
- Prometheus + Grafana (monitoring)

**External Integrations:**
- SendGrid (email)
- Twilio (SMS/voice)
- WeasyPrint (PDF generation)
- Stripe (payments)
- ATTOM, Regrid (property data)

---

## 🧪 Testing

**Comprehensive Test Suite: 68 Tests, 70%+ Coverage**

```bash
# Run all tests (3-pass: unit → integration → e2e)
./scripts/test/run_tests.sh

# Run specific test types
pytest tests/unit -v -m unit
pytest tests/integration -v -m integration
pytest tests/e2e -v -m e2e

# Check coverage
python scripts/test/validate_coverage.py coverage.xml --threshold 70
```

**Test Categories:**
- **Unit Tests** (48 tests) - Fast, isolated, no dependencies
- **Integration Tests** (15 tests) - Database + mock providers
- **E2E Tests** (5 tests) - Complete workflows

**CI/CD:** GitHub Actions runs all tests on every PR

---

## 📊 Runtime Proofs

**Generate evidence artifacts demonstrating feature functionality:**

```bash
# Generate all proofs
./scripts/proofs/run_all_proofs.sh

# Output: audit_artifacts/{timestamp}/proofs/
#   ├── 01_mock_providers.json
#   ├── 02_api_health.json
#   ├── 03_authentication.json
#   ├── 04_rate_limiting.json
#   ├── 05_idempotency.json
#   ├── 06_background_jobs.json
#   ├── 07_sse_events.json
#   ├── summary.json
#   └── openapi.json
```

**Proofs Include:**
1. Mock provider integration (zero dependencies)
2. API health & OpenAPI export
3. JWT authentication
4. Rate limiting enforcement
5. Idempotency key system
6. Background job processing
7. Real-time SSE updates

---

## 🔧 Development

### Local Setup (without Docker)

```bash
# Install dependencies
poetry install

# Set up database
createdb real_estate_os
alembic upgrade head

# Run migrations
alembic upgrade head

# Seed data
python scripts/seed_data.py

# Start API
uvicorn api.main:app --reload --port 8000

# Start Celery worker
celery -A api.celery_app worker --loglevel=info

# Start Celery beat
celery -A api.celery_app beat --loglevel=info
```

### Environment Configuration

```bash
# Copy example env file
cp .env.example .env

# For mock mode (no external APIs)
cp .env.mock .env

# Edit configuration
vim .env
```

**Key Settings:**
- `MOCK_MODE=true` - Use mock providers (no API keys needed)
- `DB_DSN` - Database connection string
- `REDIS_URL` - Redis connection
- `JWT_SECRET_KEY` - Secret for JWT signing

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 📖 Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get up and running in 5 minutes
- **[Demo Guide](docs/DEMO_GUIDE.md)** - Complete demo walkthrough with scenarios
- **[Runtime Proofs](docs/RUNTIME_PROOFS.md)** - Evidence generation system
- **[Testing Guide](docs/TESTING_GUIDE.md)** - Test infrastructure & coverage
- **[Session Progress](docs/SESSION_PROGRESS.md)** - Development session details
- **[DLQ System](docs/DLQ_SYSTEM.md)** - Dead letter queue documentation
- **[ETag Caching](docs/ETAG_CACHING.md)** - Conditional request caching

---

## 📈 Stats

- **100+ API Endpoints** across 11 routers
- **35 Database Models** with full relationships
- **~15,000 lines** of production code
- **68 Tests** with 70%+ coverage
- **7 Runtime Proofs** for demo evidence
- **11 Docker Services** for complete stack
- **4 Mock Providers** (email, SMS, storage, PDF)
- **Sub-100ms** SSE event latency
- **1000+** concurrent SSE connections supported

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`./scripts/test/run_tests.sh`)
5. Commit with clear messages
6. Push to your branch
7. Open a Pull Request

**Code Quality Requirements:**
- ✅ All tests pass
- ✅ Coverage ≥ 70%
- ✅ Code formatted with Black
- ✅ Linting passes (Flake8)
- ✅ Type hints where applicable

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- UI with [Next.js](https://nextjs.org/)
- Background jobs with [Celery](https://docs.celeryq.dev/)
- Data from [ATTOM](https://www.attomdata.com/), [Regrid](https://regrid.com/), FEMA, USGS

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/codybias9/real-estate-os/issues)
- **Discussions:** [GitHub Discussions](https://github.com/codybias9/real-estate-os/discussions)
- **Documentation:** See `docs/` directory

---

## 🎉 Demo Ready!

This platform is **100% demo-ready** with mock mode. No setup, no API keys, no configuration - just run and explore!

```bash
./scripts/docker/start.sh && ./scripts/demo/seed.sh
```

**Open http://localhost:8000/docs and start exploring!** 🚀

---

**Made with ❤️ for real estate investors**
