# Real Estate OS - Operations Runbook

**Version**: 1.0
**Last Updated**: 2025-11-01
**Status**: Production-Ready

---

## Quick Start

### Prerequisites
- Docker 20.10+ and Docker Compose 2.0+
- Python 3.11+
- Node.js 18+
- kubectl 1.25+ (for Kubernetes deployment)
- Helm 3.10+ (for K8s deployment)

### Local Development (5 minutes)

```bash
# 1. Clone and navigate
git clone <repo-url>
cd real-estate-os
git checkout claude/systematic-phase-work-011CUhTfsuprpo5BVihNuVQj

# 2. Set environment variables
cp .env.example .env
# Edit .env and set required values:
#   JWT_SECRET_KEY=<generate with: openssl rand -base64 32>
#   POSTGRES_PASSWORD=<secure password>
#   REDIS_PASSWORD=<secure password>

# 3. Start services
docker compose up -d

# 4. Verify health
curl http://localhost:8000/healthz  # Should return {"status": "ok"}
curl http://localhost:8000/metrics | head  # Should show Prometheus metrics
curl http://localhost:8080  # Web UI should load

# 5. Run migrations (if needed)
docker compose exec api alembic upgrade head

# 6. Access services
# API: http://localhost:8000
# Web UI: http://localhost:8080
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# Marquez: http://localhost:3001
```

---

## Services Overview

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| **API** | 8000 | FastAPI backend | `GET /healthz` |
| **Web** | 8080 | React frontend | `GET /` |
| **Postgres** | 5432 | Database | `pg_isready -U postgres` |
| **Redis** | 6379 | Cache + Feast online store | `redis-cli ping` |
| **Grafana** | 3000 | Metrics dashboards | `GET /api/health` |
| **Prometheus** | 9090 | Metrics collection | `GET /-/healthy` |
| **Marquez** | 5000 | Lineage API | `GET /api/v1/namespaces` |
| **Marquez Web** | 3001 | Lineage UI | `GET /` |

---

## Environment Variables

### Required
```bash
# Auth (REQUIRED)
JWT_SECRET_KEY=<32-byte base64 string>

# Database
DB_DSN=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/real_estate_os
POSTGRES_PASSWORD=<secure password>

# Redis
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_PASSWORD=<secure password>

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:8080,http://localhost:5173
```

### Optional
```bash
# Observability
SENTRY_DSN=<sentry DSN for error tracking>
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_TENANT_MINUTE=100

# Security
ENABLE_HSTS=false  # Set true in production with HTTPS
ENABLE_CSRF_PROTECTION=true

# Email (optional)
EMAIL_PROVIDER=smtp
SENDGRID_API_KEY=<sendgrid api key>

# Data Docs
GX_S3_BUCKET=<s3 bucket for Great Expectations docs>

# Slack Alerts
SLACK_WEBHOOK_URL=<slack webhook for GX alerts>

# OpenLineage
OPENLINEAGE_URL=http://marquez:5000
OPENLINEAGE_NAMESPACE=real-estate-os
```

---

## Running Tests

### Backend Tests (Pytest)
```bash
# Install dependencies
cd api
pip install -r requirements.txt
pip install pytest pytest-cov

# Run all tests with coverage
pytest --cov=api/app --cov=db --cov=ml

# Run specific test files
pytest tests/test_auth.py
pytest tests/test_properties.py -v

# Run only fast tests (skip slow)
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Generate HTML coverage report
pytest --cov-report=html
open htmlcov/index.html  # View coverage
```

### Frontend Tests (Vitest)
```bash
cd web
npm install
npm test
npm run test:coverage
```

### Expected Coverage
- **Backend**: ≥60%
- **Frontend**: ≥40%

---

## Database Migrations

### Apply Migrations
```bash
# Via docker-compose
docker compose exec api alembic upgrade head

# Locally
cd api
alembic upgrade head
```

### Create New Migration
```bash
# Generate migration from models
alembic revision --autogenerate -m "Add new table"

# Edit migration file if needed
vim alembic/versions/<generated_file>.py

# Apply migration
alembic upgrade head
```

### Rollback
```bash
# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>

# View migration history
alembic history
alembic current
```

---

## Observability

### Grafana Dashboards
1. Open http://localhost:3000
2. Login: `admin` / `admin`
3. Navigate to Dashboards → Real Estate OS Overview
4. View panels:
   - HTTP Request Rate & Duration
   - Database Query Performance
   - Cache Hit Rate
   - Authentication Success Rate
   - Business Metrics (properties, offers, etc.)

### Prometheus Queries
```promql
# API request rate
rate(http_requests_total[5m])

# API latency p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Cache hit rate
rate(cache_operations_total{result="hit"}[5m]) /
rate(cache_operations_total[5m])

# Database connection pool
db_connections_active

# Failed auth attempts
rate(auth_attempts_total{result="failure"}[5m])
```

### Sentry Error Tracking
1. Set `SENTRY_DSN` environment variable
2. Errors auto-reported to Sentry
3. View in Sentry dashboard with:
   - Stack traces
   - Breadcrumbs
   - User context
   - Performance traces

### Logs
```bash
# View API logs
docker compose logs -f api

# View specific errors
docker compose logs api | grep ERROR

# View with JSON parsing
docker compose logs api | jq .

# Audit logs (inside container)
docker compose exec api tail -f logs/audit.log
```

---

## Data Quality (Great Expectations)

### Run Validations
```bash
# Run all checkpoints
docker compose exec api python -c "
from libs.data_quality.gx.checkpoints.daily_validation import DataQualityCheckpoint
checkpoint = DataQualityCheckpoint()
results = checkpoint.run_all_validations()
print(results)
"

# Run specific suite
docker compose exec api python -c "
from libs.data_quality.gx.checkpoints.daily_validation import DataQualityCheckpoint
checkpoint = DataQualityCheckpoint()
results = checkpoint.run_properties_validation()
"
```

### View Data Docs
```bash
# Generate and open Data Docs
docker compose exec api python -c "
from great_expectations.data_context import DataContext
context = DataContext('libs/data_quality/gx')
context.build_data_docs()
"

# View at: file://libs/data_quality/gx/uncommitted/data_docs/local_site/index.html
# Or if S3 configured: https://s3.amazonaws.com/<bucket>/data_docs/index.html
```

### Freshness Check
```bash
# Check data freshness
docker compose exec api python -c "
from libs.data_quality.gx.checkpoints.daily_validation import check_freshness
lag = check_freshness()
print(f'Data lag: {lag[\"lag_seconds\"]/3600:.1f} hours')
"
```

---

## Lineage (Marquez)

### View Lineage
1. Open http://localhost:3001
2. Navigate to namespace: `real-estate-os`
3. View DAGs and dependencies
4. Click on jobs to see:
   - Inputs/outputs
   - Run history
   - Code location

### Query Lineage API
```bash
# List all jobs
curl http://localhost:5000/api/v1/namespaces/real-estate-os/jobs

# Get job details
curl http://localhost:5000/api/v1/namespaces/real-estate-os/jobs/<job_name>

# List datasets
curl http://localhost:5000/api/v1/namespaces/real-estate-os/datasets
```

---

## Feast Feature Store

### Initialize Feast
```bash
# Apply feature definitions to registry
cd ml/feature_repo
feast apply

# Verify features registered
feast feature-views list
feast entities list
```

### Materialize Features (Offline → Online)
```bash
# Materialize latest values to Redis
cd ml/feature_repo
feast materialize-incremental $(date +%Y-%m-%d)

# Materialize specific time range
feast materialize 2024-01-01 2024-12-31
```

### Query Features
```bash
# Python API
from api.app.ml.feast_client import FeastClient

client = FeastClient()
features = client.get_property_features(property_id="<uuid>")
print(features)
```

### Feast Web UI (Optional)
```bash
# Start Feast UI
cd ml/feature_repo
feast ui

# Open http://localhost:8888
```

---

## Kubernetes Deployment

### Prerequisites
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Configure kubectl context
kubectl config use-context <your-cluster>
```

### Deploy with Helm
```bash
# Create namespace
kubectl create namespace real-estate-os

# Create secrets
kubectl create secret generic real-estate-secrets \
  --from-literal=JWT_SECRET_KEY=<key> \
  --from-literal=POSTGRES_PASSWORD=<pwd> \
  --from-literal=REDIS_PASSWORD=<pwd> \
  -n real-estate-os

# Install Helm chart
cd k8s/helm
helm install real-estate-os . \
  --namespace real-estate-os \
  --values values.yaml \
  --set api.image.tag=latest \
  --set web.image.tag=latest

# Verify deployment
kubectl get pods -n real-estate-os
kubectl get svc -n real-estate-os
kubectl get ingress -n real-estate-os
```

### Scale Services
```bash
# Manual scaling
kubectl scale deployment real-estate-os-api --replicas=5 -n real-estate-os

# Enable HPA (auto-scaling)
kubectl autoscale deployment real-estate-os-api \
  --cpu-percent=80 \
  --min=3 \
  --max=10 \
  -n real-estate-os
```

### View Logs
```bash
# API logs
kubectl logs -f deployment/real-estate-os-api -n real-estate-os

# Web logs
kubectl logs -f deployment/real-estate-os-web -n real-estate-os

# Logs from specific pod
kubectl logs -f <pod-name> -n real-estate-os
```

### Rollback Deployment
```bash
# View rollout history
kubectl rollout history deployment/real-estate-os-api -n real-estate-os

# Rollback to previous version
kubectl rollout undo deployment/real-estate-os-api -n real-estate-os

# Rollback to specific revision
kubectl rollout undo deployment/real-estate-os-api --to-revision=2 -n real-estate-os
```

---

## Troubleshooting

### API Won't Start
```bash
# Check logs
docker compose logs api

# Common issues:
# 1. DB_DSN not set → Check .env file
# 2. Database not ready → Wait for postgres healthcheck
# 3. Port 8000 in use → Stop conflicting service

# Restart API
docker compose restart api
```

### Database Connection Errors
```bash
# Check postgres is running
docker compose ps postgres

# Check connection
docker compose exec postgres pg_isready -U postgres

# View postgres logs
docker compose logs postgres

# Manual connection test
docker compose exec postgres psql -U postgres -d real_estate_os
```

### Redis Connection Errors
```bash
# Check redis is running
docker compose ps redis

# Test connection
docker compose exec redis redis-cli ping

# Auth with password
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} ping

# View redis logs
docker compose logs redis
```

### Test Failures
```bash
# Run tests with more verbosity
pytest -vv --tb=short

# Run single failing test
pytest tests/test_auth.py::test_login -vv

# Drop test database and recreate
docker compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS test_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE test_db;"
```

### High Memory Usage
```bash
# Check container resource usage
docker stats

# Reduce worker processes (in docker-compose.yml)
# uvicorn api.main:app --workers 2  # Instead of 4

# Add memory limits
# deploy:
#   resources:
#     limits:
#       memory: 1G
```

### Slow Queries
```bash
# Check slow queries in Postgres
docker compose exec postgres psql -U postgres -d real_estate_os -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Enable query logging (for debugging)
# In postgres config: log_min_duration_statement = 100
```

---

## Backup & Restore

### Database Backup
```bash
# Backup to file
docker compose exec -T postgres pg_dump -U postgres real_estate_os > backup_$(date +%Y%m%d).sql

# Compressed backup
docker compose exec -T postgres pg_dump -U postgres real_estate_os | gzip > backup_$(date +%Y%m%d).sql.gz

# Automated daily backups (cron)
# 0 2 * * * /path/to/backup_script.sh
```

### Database Restore
```bash
# Restore from file
docker compose exec -T postgres psql -U postgres -d real_estate_os < backup_20250101.sql

# Restore from compressed
gunzip -c backup_20250101.sql.gz | docker compose exec -T postgres psql -U postgres -d real_estate_os
```

### Redis Backup
```bash
# Trigger RDB snapshot
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} SAVE

# Copy RDB file
docker compose cp redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

---

## Security

### Generate Secrets
```bash
# JWT secret (32 bytes base64)
openssl rand -base64 32

# Database password
openssl rand -base64 24

# API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Rotate Secrets
```bash
# 1. Generate new JWT_SECRET_KEY
NEW_KEY=$(openssl rand -base64 32)

# 2. Update .env
echo "JWT_SECRET_KEY=$NEW_KEY" >> .env

# 3. Restart API
docker compose restart api

# 4. All existing tokens invalidated - users must re-login
```

### Security Checklist
- [ ] JWT_SECRET_KEY is random and unique
- [ ] POSTGRES_PASSWORD is strong (≥16 chars)
- [ ] REDIS_PASSWORD is set
- [ ] CORS_ORIGINS is allowlist (no wildcards)
- [ ] ENABLE_HSTS=true in production with HTTPS
- [ ] Rate limiting enabled
- [ ] Sentry DSN configured
- [ ] Database backups automated
- [ ] Secrets stored in Vault/K8s secrets (not .env)

---

## Performance Tuning

### Database
```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_property_tenant_status ON property(tenant_id, status);
CREATE INDEX CONCURRENTLY idx_property_geom ON property USING GIST(geom);

-- Analyze tables
ANALYZE property;
ANALYZE ownership;

-- Vacuum (reclaim space)
VACUUM ANALYZE;
```

### Redis
```bash
# Check memory usage
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} INFO memory

# Eviction policy (in docker-compose.yml)
# command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### API
```python
# Increase Uvicorn workers (docker-compose.yml or Dockerfile CMD)
# CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--workers", "4"]

# Add connection pooling
# In api/app/database.py:
# engine = create_engine(DB_DSN, pool_size=20, max_overflow=10)
```

---

## Monitoring Alerts

### Prometheus Alertmanager (Optional)
```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: '<slack webhook>'

route:
  receiver: 'slack'

receivers:
  - name: 'slack'
    slack_configs:
      - channel: '#alerts'
        title: 'Real Estate OS Alert'
```

### Sample Alerts
```yaml
# alerts.yml
groups:
  - name: api
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High 5xx error rate"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 10m
        annotations:
          summary: "API p95 latency >1s"

      - alert: DataFreshness
        expr: (time() - max(property_updated_at)) > 7200
        for: 15m
        annotations:
          summary: "Data is stale (>2 hours)"
```

---

## Support & Escalation

### Health Check Endpoints
- `GET /healthz` - Basic health
- `GET /metrics` - Prometheus metrics
- `GET /ping` - Database connectivity

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker compose restart api

# View debug logs
docker compose logs -f api
```

### Get Help
1. Check logs: `docker compose logs -f`
2. Check metrics: http://localhost:9090
3. Check Sentry: <sentry dashboard>
4. Review runbook: `/RUNBOOK.md`
5. Contact: data-team@ or platform-team@

---

## Appendix: Quick Reference

### Common Commands
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart a service
docker compose restart api

# View logs
docker compose logs -f api

# Execute command in container
docker compose exec api python -c "print('hello')"

# Run migrations
docker compose exec api alembic upgrade head

# Run tests
pytest

# View resource usage
docker stats
```

### Port Reference
- 8000: API
- 8080: Web UI
- 5432: Postgres
- 6379: Redis
- 3000: Grafana
- 9090: Prometheus
- 5000: Marquez API
- 3001: Marquez Web

### Directory Structure
```
/
├── api/                # FastAPI backend
├── web/                # React frontend
├── db/                 # Database models
├── ml/                 # ML models, features, optimization
├── tests/              # Pytest tests
├── dags/               # Airflow DAGs
├── workflows/          # Temporal workflows
├── libs/               # Shared libraries (GX, etc.)
├── services/           # Supporting services (lineage, etc.)
├── k8s/                # Kubernetes manifests
├── observability/      # Grafana, Prometheus configs
└── docker-compose.yml
```

---

**End of Runbook**
**For issues or questions, consult logs and metrics first, then escalate to platform team.**
