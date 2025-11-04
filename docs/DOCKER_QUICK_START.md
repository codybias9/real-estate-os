# Real Estate OS - Docker Quick Start Guide

**Mock Mode**: Fully self-contained, no external credentials required

---

## Prerequisites

- Docker Engine 20.10+ ([Install Guide](https://docs.docker.com/engine/install/))
- Docker Compose v2.x ([Install Guide](https://docs.docker.com/compose/install/))
- 8GB+ RAM available for Docker
- Ports available: 80, 3000, 3001, 5432, 5555, 6379, 8000, 8025, 9000, 9090, 15672

---

## Quick Start (3 Commands)

```bash
# 1. Start the stack (15 services)
./scripts/start_docker_stack.sh

# 2. Validate health
./scripts/validate_docker_stack.sh

# 3. Run introspection (generates endpoints.json + models.json)
./scripts/run_introspection.sh
```

---

## What Gets Started?

### Infrastructure Services (7)
- **PostgreSQL** (port 5432): Database with 35+ tables
- **Redis** (port 6379): Cache & session store
- **RabbitMQ** (ports 5672, 15672): Message queue + management UI
- **MinIO** (ports 9000, 9001): S3-compatible object storage
- **Gotenberg** (port 3000): PDF generation service
- **MailHog** (ports 1025, 8025): SMTP server + email capture UI
- **Mock Twilio** (port 4010): SMS capture service

### Application Services (8)
- **API** (port 8000): FastAPI application (118 endpoints)
- **Celery Worker**: Background task processor (4 workers, 3 queues)
- **Celery Beat**: Scheduled task manager (nightly reconciliation, etc.)
- **Frontend** (port 3000): Next.js 14 application
- **Nginx** (port 80): Reverse proxy
- **Flower** (port 5555): Celery monitoring UI
- **Prometheus** (port 9090): Metrics collection
- **Grafana** (port 3001): Metrics visualization (admin/admin)

---

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **API (FastAPI)** | http://localhost:8000 | - |
| **API Docs (Swagger)** | http://localhost:8000/docs | - |
| **Frontend (Next.js)** | http://localhost:3000 | - |
| **MailHog (Email UI)** | http://localhost:8025 | - |
| **RabbitMQ Mgmt** | http://localhost:15672 | guest/guest |
| **MinIO Console** | http://localhost:9001 | minioadmin/minioadmin |
| **Flower (Celery)** | http://localhost:5555 | - |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana** | http://localhost:3001 | admin/admin |

---

## Verify Health

### Quick Check
```bash
# Test API health
curl http://localhost:8000/healthz

# Check all services
docker compose ps
```

### Comprehensive Validation
```bash
# Run full health validation suite
./scripts/validate_docker_stack.sh

# Generates: audit_artifacts/<timestamp>/bringup_health.json
```

---

## Common Operations

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f celery-worker
docker compose logs -f frontend
```

### Restart Service
```bash
docker compose restart api
```

### Run Migrations
```bash
docker compose exec api alembic upgrade head
```

### Access Database
```bash
docker compose exec postgres psql -U postgres -d real_estate_os

# List tables
\dt

# Count properties
SELECT COUNT(*) FROM properties;
```

### Access Redis
```bash
docker compose exec redis redis-cli

# Check keys
KEYS *

# Get rate limit counter
GET rate_limit:127.0.0.1:/api/v1/auth/login
```

### Check RabbitMQ Queues
```bash
# Via CLI
docker compose exec rabbitmq rabbitmqctl list_queues

# Via UI: http://localhost:15672 (guest/guest)
```

### View Captured Emails
```bash
# Via UI: http://localhost:8025
# Or via API
curl http://localhost:8025/api/v2/messages
```

---

## Run Introspection

Generate authoritative evidence of endpoints and models:

```bash
# Run introspection suite
./scripts/run_introspection.sh

# Generates:
#   audit_artifacts/<timestamp>/endpoints.json (118 endpoints)
#   audit_artifacts/<timestamp>/models.json (35+ models)
```

Validate:
```bash
# Check endpoint count
jq '.statistics.total_endpoints' audit_artifacts/*/endpoints.json

# Check model count
jq '.statistics.total_models' audit_artifacts/*/models.json
```

---

## Troubleshooting

### Services Not Starting
```bash
# Check service status
docker compose ps

# View specific service logs
docker compose logs api
docker compose logs postgres
```

### Port Conflicts
If ports are already in use, edit `.env`:
```bash
# Example: Change API port
BACKEND_URL=http://localhost:8001

# Rebuild
docker compose down
./scripts/start_docker_stack.sh --build
```

### Out of Memory
```bash
# Check Docker resources
docker system df

# Prune unused images
docker system prune -a

# Increase Docker memory limit (Docker Desktop):
# Settings → Resources → Memory → 8GB+
```

### Database Connection Issues
```bash
# Reset database
docker compose down -v  # WARNING: Deletes data
docker compose up -d postgres
docker compose exec api alembic upgrade head
```

### Rebuild Everything
```bash
# Full reset (WARNING: Deletes all data)
docker compose down -v
docker system prune -af
./scripts/start_docker_stack.sh --build
```

---

## Stop Stack

```bash
# Stop services (preserves data)
docker compose down

# Stop and remove volumes (deletes data)
docker compose down -v
```

---

## Mock Mode Guarantees

✅ **What Works**:
- All 118 API endpoints functional
- Email sending → captured in MailHog
- SMS sending → captured in Mock Twilio
- PDF generation → Gotenberg
- File storage → MinIO
- Background jobs → Celery
- Real-time updates → SSE
- Database → PostgreSQL with 35+ tables
- Caching → Redis
- Message queue → RabbitMQ

❌ **What's Mocked** (No Real External Calls):
- Email: MailHog SMTP (not SendGrid)
- SMS: Mock Twilio (not real Twilio)
- LLM: Deterministic templates (not OpenAI)
- Data enrichment: Mock data (not ATTOM/Regrid)
- Monitoring: Local only (not Sentry/DataDog)

---

## Next Steps

After stack is healthy:

1. **Run Tests**: `pytest --cov=. --cov-report=xml`
2. **Generate Proofs**: `./scripts/generate_proofs.sh` (Phase 4)
3. **Seed Demo Data**: `python scripts/seed_demo.py` (Phase 5)
4. **Open PR**: Create PR to main with Evidence Pack

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     NGINX (Port 80)                          │
│                    Reverse Proxy                             │
└────────┬───────────────────────────────────────────┬────────┘
         │                                            │
         │                                            │
    ┌────▼──────┐                              ┌─────▼──────┐
    │  Frontend │                              │     API    │
    │ Next.js   │                              │  FastAPI   │
    │  :3000    │                              │   :8000    │
    └───────────┘                              └────┬───────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────┐
                    │                               │                       │
               ┌────▼──────┐              ┌────────▼────────┐    ┌─────────▼────────┐
               │ PostgreSQL│              │      Redis      │    │     RabbitMQ     │
               │   :5432   │              │      :6379      │    │  :5672, :15672   │
               └───────────┘              └─────────────────┘    └──────────────────┘
                                                                           │
                    ┌──────────────────────────────────────────────────────┘
                    │                               │
               ┌────▼──────────┐         ┌─────────▼──────────┐
               │ Celery Worker │         │   Celery Beat      │
               │  (4 workers)  │         │ (Scheduler)        │
               └───────────────┘         └────────────────────┘
```

---

## Support

For issues or questions:
- Check logs: `docker compose logs -f [service]`
- Review health: `./scripts/validate_docker_stack.sh`
- Consult: `docs/WORK_JOURNAL.md`
