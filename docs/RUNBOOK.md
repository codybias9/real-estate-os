# Real Estate OS - Operational Runbook

**Last Updated**: 2024-11-02
**Version**: 1.0

---

## Table of Contents
1. [Zero-to-Green Setup](#zero-to-green-setup)
2. [Health Checks](#health-checks)
3. [Expected Metrics](#expected-metrics)
4. [Common Operations](#common-operations)
5. [Troubleshooting](#troubleshooting)
6. [Rollback Procedures](#rollback-procedures)
7. [On-Call Procedures](#on-call-procedures)

---

## Zero-to-Green Setup

### Prerequisites
- Docker Desktop installed
- Python 3.10+ installed
- Poetry installed
- kubectl configured (for K8s deployment)
- 16GB+ RAM, 50GB+ disk space

### Local Development (Docker Compose)

```bash
# 1. Clone repository
git clone https://github.com/codybias9/real-estate-os.git
cd real-estate-os

# 2. Install Python dependencies
poetry install

# 3. Start infrastructure services
docker-compose up -d postgres redis qdrant minio rabbitmq

# 4. Wait for services to be healthy
./scripts/wait-for-services.sh

# 5. Run database migrations
poetry run alembic upgrade head

# 6. Start API
poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000

# 7. Start Airflow (in separate terminal)
docker-compose up airflow-webserver airflow-scheduler

# 8. Verify health
curl http://localhost:8000/healthz
# Expected: {"status": "ok"}
```

**Time to Green**: ~10 minutes

### Kubernetes Deployment

```bash
# 1. Create namespace
kubectl create namespace real-estate-os

# 2. Apply secrets
kubectl apply -f infra/k8s/db-secret.yaml

# 3. Deploy infrastructure
helm install postgres bitnami/postgresql -f infra/charts/overrides/values-postgres.yaml
helm install redis bitnami/redis
helm install qdrant qdrant/qdrant -f infra/charts/overrides/values-qdrant.yaml
helm install minio bitnami/minio -f infra/charts/overrides/values-minio.yaml
helm install rabbitmq bitnami/rabbitmq -f infra/charts/overrides/values-rabbitmq.yaml

# 4. Deploy Airflow
helm install airflow apache-airflow/airflow -f infra/charts/overrides/values-airflow.yaml

# 5. Deploy API
kubectl apply -f infra/k8s/api.yaml
kubectl apply -f infra/k8s/api-service.yaml

# 6. Deploy observability stack
kubectl apply -f infra/observability/

# 7. Verify all pods running
kubectl get pods -n real-estate-os
# All pods should be Running or Completed

# 8. Port-forward and test
kubectl port-forward svc/api 8000:8000
curl http://localhost:8000/healthz
```

**Time to Green**: ~20-30 minutes

---

## Health Checks

### API Health
```bash
# Basic health
curl http://localhost:8000/healthz
# Expected: {"status": "ok"}

# Database connectivity
curl http://localhost:8000/ping
# Expected: {"ping_count": <number>}
```

### Component Health Matrix

| Component | Endpoint | Expected Response | Timeout |
|-----------|----------|-------------------|---------|
| API | `GET /healthz` | `{"status": "ok"}` | 5s |
| PostgreSQL | `pg_isready -h localhost` | "accepting connections" | 5s |
| Redis | `redis-cli ping` | "PONG" | 2s |
| Qdrant | `GET :6333/collections` | JSON list | 5s |
| MinIO | `GET :9000/minio/health/live` | 200 OK | 5s |
| RabbitMQ | `GET :15672/api/health/checks/alarms` | JSON | 5s |
| Airflow | `GET :8080/health` | `{"status": "healthy"}` | 10s |

### Automated Health Check Script

```bash
#!/bin/bash
# scripts/health-check.sh

set -e

echo "=== Health Check ==="

# API
echo -n "API: "
curl -f -s http://localhost:8000/healthz > /dev/null && echo "✅ OK" || echo "❌ FAIL"

# PostgreSQL
echo -n "PostgreSQL: "
pg_isready -h localhost -p 5432 > /dev/null && echo "✅ OK" || echo "❌ FAIL"

# Redis
echo -n "Redis: "
redis-cli ping > /dev/null && echo "✅ OK" || echo "❌ FAIL"

# Qdrant
echo -n "Qdrant: "
curl -f -s http://localhost:6333/collections > /dev/null && echo "✅ OK" || echo "❌ FAIL"

# MinIO
echo -n "MinIO: "
curl -f -s http://localhost:9000/minio/health/live > /dev/null && echo "✅ OK" || echo "❌ FAIL"

# RabbitMQ
echo -n "RabbitMQ: "
curl -f -s http://localhost:15672/api/health/checks/alarms > /dev/null && echo "✅ OK" || echo "❌ FAIL"

# Airflow
echo -n "Airflow: "
curl -f -s http://localhost:8080/health > /dev/null && echo "✅ OK" || echo "❌ FAIL"

echo "=== Health Check Complete ==="
```

---

## Expected Metrics

### SLIs (Service Level Indicators)

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| API Availability | ≥99.9% | <99.5% | <99.0% |
| API p95 Latency | <500ms | >750ms | >1000ms |
| API Error Rate | <0.1% | >0.5% | >1.0% |
| DAG Success Rate | ≥95% | <90% | <80% |
| Pipeline Freshness | <2h | >4h | >8h |

### Key Dashboards

1. **Real Estate OS - Overview** (Grafana)
   - API request rate, latency, errors
   - Vector search performance
   - Pipeline freshness
   - URL: `http://grafana:3000/d/real-estate-os-overview`

2. **ML Performance** (Grafana)
   - Model inference latencies
   - Feature store cache hit rate
   - SHAP computation times
   - URL: `http://grafana:3000/d/ml-performance`

3. **Airflow Dashboard**
   - DAG run history
   - Task success/failure rates
   - URL: `http://airflow:8080/home`

### Alerts

Configure alerts in Prometheus Alertmanager for:
- API error rate > 1% for 5 minutes
- API p95 latency > 1s for 5 minutes
- DAG failure for critical pipelines
- Pipeline freshness > 4 hours
- Database connection pool exhaustion
- Qdrant index degradation

---

## Common Operations

### Restarting Services

```bash
# Restart API only
docker-compose restart api

# Restart Airflow scheduler
docker-compose restart airflow-scheduler

# Restart all services
docker-compose restart
```

### Viewing Logs

```bash
# API logs
docker-compose logs -f api

# Airflow scheduler logs
docker-compose logs -f airflow-scheduler

# All logs
docker-compose logs -f

# Kubernetes logs
kubectl logs -f deployment/api -n real-estate-os
kubectl logs -f deployment/airflow-scheduler -n real-estate-os
```

### Database Operations

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d real_estate

# Run migration
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1

# Create new migration
poetry run alembic revision --autogenerate -m "description"
```

### Triggering DAGs Manually

```bash
# Via Airflow CLI
docker-compose exec airflow-scheduler airflow dags trigger property_processing_pipeline

# Via REST API
curl -X POST \
  http://localhost:8080/api/v1/dags/property_processing_pipeline/dagRuns \
  -H 'Content-Type: application/json' \
  -d '{"conf": {}}'
```

### Clearing Cache

```bash
# Clear Redis cache
docker-compose exec redis redis-cli FLUSHDB

# Clear Feast cache (if using Redis)
docker-compose exec redis redis-cli KEYS "feast:*" | xargs docker-compose exec redis redis-cli DEL
```

---

## Troubleshooting

### API Returns 500 Errors

**Symptoms**: API endpoints returning 500, logs show database connection errors

**Diagnosis**:
```bash
# Check database connectivity
docker-compose exec postgres pg_isready

# Check connection pool
docker-compose logs api | grep "connection pool"
```

**Resolution**:
1. Restart PostgreSQL: `docker-compose restart postgres`
2. If pool exhausted, increase `SQLALCHEMY_POOL_SIZE` in env
3. Check for long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active';`

---

### DAG Failures

**Symptoms**: Airflow DAG tasks failing, data pipeline stale

**Diagnosis**:
```bash
# Check DAG logs
docker-compose logs airflow-scheduler | grep "property_processing_pipeline"

# Check task logs in Airflow UI
# http://localhost:8080 → DAGs → property_processing_pipeline → Failed task → Logs
```

**Common causes**:
1. **Data quality failure**: Check Great Expectations logs
2. **External API timeout**: Check network connectivity, API rate limits
3. **Resource exhaustion**: Check worker memory/CPU

**Resolution**:
1. Review task logs for specific error
2. Fix data quality issues or external API problems
3. Retry failed tasks in Airflow UI: Task → Clear → Retry

---

### Qdrant Vector Search Slow

**Symptoms**: Vector search p95 > 100ms, scoring slow

**Diagnosis**:
```bash
# Check Qdrant metrics
curl http://localhost:6333/metrics

# Check collection size and segments
curl http://localhost:6333/collections/properties_v2
```

**Resolution**:
1. **Too many segments**: Optimize collection
   ```bash
   curl -X POST http://localhost:6333/collections/properties_v2/index
   ```
2. **Index not in memory**: Increase Qdrant memory allocation
3. **Large result sets**: Reduce `limit` in search queries

---

### High Memory Usage

**Symptoms**: OOM kills, slow response times

**Diagnosis**:
```bash
# Check memory usage
docker stats

# Check for memory leaks
docker-compose logs api | grep "memory"
```

**Resolution**:
1. Restart service with memory leak
2. Review code for unclosed connections, large in-memory structures
3. Increase memory allocation if needed
4. Enable memory profiling with `memory_profiler`

---

## Rollback Procedures

### API Rollback

**Scenario**: New API version causing errors

```bash
# Docker Compose
docker-compose down
git checkout <previous-commit>
docker-compose build api
docker-compose up -d

# Kubernetes
kubectl rollout undo deployment/api -n real-estate-os
kubectl rollout status deployment/api -n real-estate-os
```

**Verification**:
1. Check health: `curl http://localhost:8000/healthz`
2. Check metrics: Verify error rate decreased in Grafana
3. Monitor for 15 minutes

---

### Database Migration Rollback

**Scenario**: Migration caused data issues

```bash
# Rollback one migration
poetry run alembic downgrade -1

# Rollback to specific version
poetry run alembic downgrade <revision_id>

# Verify
docker-compose exec postgres psql -U postgres -d real_estate -c "\d"
```

**Important**: Always backup database before migrations in production!

```bash
pg_dump -U postgres -d real_estate > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

### DAG Rollback

**Scenario**: New DAG version causing failures

```bash
# Pause DAG
docker-compose exec airflow-scheduler airflow dags pause property_processing_pipeline

# Revert code
git checkout <previous-commit>

# Unpause DAG
docker-compose exec airflow-scheduler airflow dags unpause property_processing_pipeline
```

---

### Model Rollback (Canary)

See [docs/release/canary-runbook.md](./release/canary-runbook.md) for detailed canary rollback procedures.

**Quick rollback**:
1. Update feature flag to route 100% traffic to old model
2. Monitor metrics for 5 minutes
3. If stable, investigate and fix new model offline

---

## On-Call Procedures

### Incident Response Process

1. **Acknowledge** (within 5 min)
   - Acknowledge page in PagerDuty
   - Post in #incidents Slack channel

2. **Assess** (within 10 min)
   - Check dashboards (Grafana, Airflow)
   - Check recent deploys (git log, K8s events)
   - Determine severity (P0/P1/P2)

3. **Mitigate** (within 30 min for P0)
   - Rollback if recent deploy
   - Scale up resources if needed
   - Disable problematic feature flag

4. **Resolve**
   - Fix root cause
   - Verify metrics returned to normal
   - Post mortem for P0/P1 incidents

5. **Communicate**
   - Update #incidents channel every 30 min
   - Notify stakeholders
   - Post resolution

---

### Escalation

| Issue Type | Escalate To | Contact |
|------------|-------------|---------|
| API/Backend | Backend Team Lead | Slack: @backend-lead |
| ML Models | ML Team Lead | Slack: @ml-lead |
| Data Pipeline | Data Engineering Lead | Slack: @data-eng-lead |
| Infrastructure | DevOps/SRE Lead | Slack: @devops-lead |
| Security | Security Team | Slack: @security-team |

---

### Post-Incident Review

Within 48 hours of P0/P1 incident:
1. Write post-mortem document
2. Identify root cause
3. List action items with owners
4. Schedule review meeting
5. Update runbook with learnings

---

## Maintenance Windows

### Scheduled Maintenance

Maintenance windows: Sundays 2:00-4:00 AM UTC

**Pre-maintenance checklist**:
- [ ] Notify users 48 hours in advance
- [ ] Backup all databases
- [ ] Prepare rollback plan
- [ ] Test changes in staging
- [ ] Verify monitoring and alerts active

**During maintenance**:
- [ ] Update status page
- [ ] Follow maintenance runbook
- [ ] Monitor health checks continuously
- [ ] Log all actions

**Post-maintenance**:
- [ ] Verify all systems operational
- [ ] Check metrics for anomalies
- [ ] Update status page
- [ ] Send completion notification

---

## Contact Information

- **On-Call Rotation**: See PagerDuty schedule
- **Slack Channels**:
  - #real-estate-os-alerts (automated alerts)
  - #real-estate-os-ops (operations discussion)
  - #incidents (active incidents)
- **Grafana**: http://grafana.internal/
- **Airflow**: http://airflow.internal/
- **Sentry**: http://sentry.io/real-estate-os

---

**Document Owner**: SRE Team
**Review Frequency**: Quarterly
