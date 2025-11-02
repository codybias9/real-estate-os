# Real Estate OS - Deployment Runbook

**Last Updated**: 2025-11-02
**Version**: 1.0
**Owner**: Platform Team

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Deployment Procedures](#deployment-procedures)
5. [Health Checks](#health-checks)
6. [Rollback Procedures](#rollback-procedures)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Troubleshooting](#troubleshooting)
9. [Emergency Contacts](#emergency-contacts)

---

## Overview

This runbook provides step-by-step procedures for deploying Real Estate OS to staging and production environments.

### Architecture Overview

- **API**: FastAPI application (Port 8000)
- **Database**: PostgreSQL 13 + PostGIS (Port 5432)
- **Cache**: Redis 7 (Port 6379)
- **Auth**: Keycloak OIDC (Port 8080)
- **Vector DB**: Qdrant (Port 6333)
- **Object Storage**: MinIO (Port 9000)
- **Graph DB**: Neo4j (Port 7474, 7687)
- **Orchestration**: Apache Airflow (Port 8081)
- **Monitoring**: Prometheus (9090) + Grafana (3000)
- **Error Tracking**: Sentry

### Deployment Strategy

- **Strategy**: Blue-Green deployment with canary rollout
- **Zero Downtime**: Required
- **Database Migrations**: Applied before code deployment
- **Rollback Window**: 15 minutes

---

## Prerequisites

### Required Access

- [ ] SSH access to deployment servers
- [ ] Docker registry credentials
- [ ] Database admin credentials
- [ ] AWS/Cloud provider credentials (for infrastructure)
- [ ] Sentry project access
- [ ] Grafana dashboard access

### Required Tools

```bash
# Verify tools are installed
docker --version          # Docker 20.10+
docker-compose --version  # Docker Compose 2.0+
git --version            # Git 2.30+
python --version         # Python 3.11+
psql --version           # PostgreSQL client 13+
```

### Environment Variables

Ensure `.env.staging` or `.env.production` is configured with:

```bash
# Core
ENVIRONMENT=staging|production
DEBUG=false

# Database
POSTGRES_HOST=<host>
POSTGRES_PORT=5432
POSTGRES_DB=realestate
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>

# Redis
REDIS_URL=redis://<host>:6379
REDIS_PASSWORD=<password>

# Keycloak
KEYCLOAK_URL=https://<host>:8080
KEYCLOAK_REALM=real-estate-os
KEYCLOAK_CLIENT_ID=api-client

# Monitoring
SENTRY_DSN=<dsn>
PROMETHEUS_URL=http://prometheus:9090
```

---

## Pre-Deployment Checklist

### Code Preparation

- [ ] All tests passing (pytest with >70% coverage)
- [ ] Code reviewed and approved
- [ ] Git tag created (e.g., `v1.2.3`)
- [ ] Changelog updated
- [ ] Database migrations tested in staging

### Infrastructure Checks

- [ ] Staging environment healthy
- [ ] Database backups completed (last 24h)
- [ ] Disk space sufficient (>20% free)
- [ ] Rate limits reviewed for expected traffic
- [ ] SSL certificates valid (>30 days remaining)

### Communication

- [ ] Deployment scheduled in team calendar
- [ ] Stakeholders notified
- [ ] Rollback plan reviewed
- [ ] On-call engineer assigned

---

## Deployment Procedures

### 1. Database Migrations (Pre-Deployment)

**CRITICAL**: Always apply migrations before deploying new code.

```bash
# 1. Backup database
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Test migrations in dry-run mode
python scripts/db/apply_migrations.py --dry-run

# 3. Apply migrations
python scripts/db/apply_migrations.py --apply

# 4. Verify migration success
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "\dt"
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version FROM alembic_version;"

# 5. Verify RLS policies still active
bash scripts/ops/verify_rls.sh
```

**Expected Output**: All tables present, RLS policies active, no errors.

### 2. Build and Push Docker Images

```bash
# 1. Set version tag
export VERSION=v1.2.3

# 2. Build API image
docker build -t real-estate-os-api:$VERSION -f Dockerfile.api .

# 3. Tag image for registry
docker tag real-estate-os-api:$VERSION registry.example.com/real-estate-os-api:$VERSION
docker tag real-estate-os-api:$VERSION registry.example.com/real-estate-os-api:latest

# 4. Push to registry
docker push registry.example.com/real-estate-os-api:$VERSION
docker push registry.example.com/real-estate-os-api:latest

# 5. Verify image in registry
docker pull registry.example.com/real-estate-os-api:$VERSION
```

### 3. Deploy to Staging

```bash
# 1. SSH to staging server
ssh deploy@staging.example.com

# 2. Pull latest configuration
cd /opt/real-estate-os
git pull origin main
git checkout $VERSION

# 3. Update environment variables
cp .env.staging.example .env.staging
nano .env.staging  # Update secrets

# 4. Pull new images
docker-compose -f docker-compose.staging.yml pull

# 5. Stop old containers (blue)
docker-compose -f docker-compose.staging.yml stop api

# 6. Start new containers (green)
docker-compose -f docker-compose.staging.yml up -d api

# 7. Wait for healthcheck
sleep 30
curl -f http://localhost:8000/health || echo "Health check failed!"

# 8. Verify API is responding
curl http://localhost:8000/api/v1/health | jq .

# 9. Check logs for errors
docker-compose -f docker-compose.staging.yml logs --tail=100 api | grep ERROR
```

### 4. Deploy to Production (Blue-Green)

**Blue**: Current running version
**Green**: New version being deployed

```bash
# 1. SSH to production server
ssh deploy@production.example.com

# 2. Pull latest configuration
cd /opt/real-estate-os
git pull origin main
git checkout $VERSION

# 3. Update environment variables
cp .env.production.example .env.production
nano .env.production  # Update secrets

# 4. Start green (new version) containers
docker-compose -f docker-compose.production.yml -p green up -d api

# 5. Wait for green to be healthy
sleep 60
curl -f http://localhost:8001/health || echo "Green health check failed!"

# 6. Run smoke tests on green
bash scripts/ops/smoke_tests.sh http://localhost:8001

# 7. Switch load balancer to green (zero-downtime cutover)
# Example for nginx:
sudo cp /etc/nginx/sites-available/green /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# 8. Monitor traffic on green for 5 minutes
# Check Grafana dashboard: https://grafana.example.com/d/real-estate-os-overview

# 9. If healthy, stop blue (old version)
docker-compose -f docker-compose.production.yml -p blue stop api

# 10. Clean up old images (keep last 3)
docker image prune -a --filter "until=72h"
```

### 5. Restart Dependent Services

```bash
# Restart Airflow to pick up new DAGs
docker-compose -f docker-compose.production.yml restart airflow-scheduler
docker-compose -f docker-compose.production.yml restart airflow-webserver

# Verify Airflow is healthy
curl http://localhost:8081/health | jq .

# Check DAG statuses
docker-compose -f docker-compose.production.yml exec airflow-webserver airflow dags list
```

---

## Health Checks

### Automated Health Checks

```bash
# Run comprehensive health check script
bash scripts/ops/health_check.sh

# Expected checks:
# ✓ PostgreSQL connection
# ✓ Redis connection
# ✓ API /health endpoint (200 OK)
# ✓ API /api/v1/health endpoint (detailed status)
# ✓ Keycloak JWKS endpoint
# ✓ Qdrant collections exist
# ✓ MinIO buckets accessible
# ✓ Neo4j connection
# ✓ Prometheus targets UP
# ✓ Grafana datasources healthy
```

### Manual Verification

```bash
# 1. API health
curl -s http://api.example.com/health | jq .
# Expected: {"status": "healthy", "timestamp": "..."}

# 2. Database health
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"
# Expected: 1

# 3. Redis health
redis-cli -h $REDIS_HOST -a $REDIS_PASSWORD PING
# Expected: PONG

# 4. Authentication
curl -X POST https://api.example.com/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123"
# Expected: {"access_token": "...", "token_type": "Bearer"}

# 5. Rate limiting
for i in {1..105}; do curl -s -o /dev/null -w "%{http_code}\n" http://api.example.com/api/v1/properties; done | sort | uniq -c
# Expected: Some 429 responses (rate limit)

# 6. Vector search
curl -X POST http://qdrant:6333/collections/properties/points/search \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.1, 0.2, 0.3, ...], "limit": 5}'
# Expected: Search results
```

### Key Metrics to Monitor

**Grafana Dashboard**: https://grafana.example.com/d/real-estate-os-overview

- **API Request Rate**: Should match baseline (~50-100 RPS)
- **API P95 Latency**: <500ms
- **Error Rate**: <1%
- **Database Connections**: <80% of max
- **Redis Memory Usage**: <75%
- **Vector Search Latency**: <100ms

---

## Rollback Procedures

### When to Rollback

Trigger rollback if:

- [ ] Error rate >5% for 5 minutes
- [ ] P95 latency >1000ms for 5 minutes
- [ ] Critical functionality broken (auth, payments, core API)
- [ ] Database corruption detected
- [ ] Security vulnerability discovered

### Quick Rollback (Blue-Green)

```bash
# 1. Switch load balancer back to blue (old version)
sudo cp /etc/nginx/sites-available/blue /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# 2. Verify blue is serving traffic
curl -s http://api.example.com/health | jq .version
# Expected: Previous version number

# 3. Stop green (failed deployment)
docker-compose -f docker-compose.production.yml -p green stop api

# 4. Investigate issue
docker-compose -f docker-compose.production.yml -p green logs api > rollback_logs.txt
```

**Rollback Time**: ~2 minutes

### Database Rollback

**WARNING**: Database rollbacks are risky. Prefer forward fixes.

```bash
# 1. Identify migration to rollback to
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version FROM alembic_version;"

# 2. Restore from backup (if necessary)
pg_restore -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB backup_20251102_120000.sql

# 3. Verify data integrity
python scripts/db/verify_data_integrity.py

# 4. Downgrade migration (if safe)
alembic downgrade -1
```

---

## Post-Deployment Verification

### Immediate Checks (T+0 to T+15 minutes)

- [ ] All health checks passing
- [ ] No error spikes in Sentry
- [ ] API response times normal
- [ ] Database connection pool stable
- [ ] No alerts firing in Prometheus

### Extended Monitoring (T+15 to T+60 minutes)

- [ ] Monitor user activity (no dropoff)
- [ ] Check background jobs (Airflow DAGs running)
- [ ] Verify scheduled tasks executing
- [ ] Review Grafana dashboards for anomalies

### Validation Tests

```bash
# Run smoke tests
bash scripts/ops/smoke_tests.sh https://api.example.com

# Run E2E pipeline
python scripts/ops/run_minimal_e2e.py

# Verify isolation
bash scripts/ops/verify_api_isolation.sh

# Check auth
bash scripts/ops/verify_api_auth.sh
```

### Documentation Updates

- [ ] Update version number in docs
- [ ] Update changelog
- [ ] Record deployment in ops log
- [ ] Update runbook if new issues discovered

---

## Troubleshooting

### Common Issues

#### Issue: API Returns 500 Errors

**Symptoms**: 5xx status codes, errors in Sentry

**Diagnosis**:
```bash
# Check API logs
docker-compose logs --tail=100 api | grep ERROR

# Check Sentry for stack traces
# Visit: https://sentry.io/organizations/.../issues/

# Check database connectivity
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"
```

**Resolution**:
1. Check environment variables are correct
2. Verify database migrations applied
3. Restart API container: `docker-compose restart api`
4. If persistent, rollback deployment

---

#### Issue: Database Connection Pool Exhausted

**Symptoms**: "No more connections available", slow queries

**Diagnosis**:
```bash
# Check active connections
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c \
  "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Check long-running queries
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c \
  "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC LIMIT 10;"
```

**Resolution**:
1. Increase pool size in config: `SQLALCHEMY_POOL_SIZE=20`
2. Kill long-running queries: `SELECT pg_terminate_backend(<pid>);`
3. Restart database connection: `docker-compose restart postgres`

---

#### Issue: Rate Limiting Too Aggressive

**Symptoms**: Many 429 responses, user complaints

**Diagnosis**:
```bash
# Check rate limit metrics
curl http://api.example.com/metrics | grep rate_limit_exceeded

# Check Redis for rate limit keys
redis-cli -h $REDIS_HOST KEYS "*rate_limit*" | wc -l
```

**Resolution**:
1. Temporarily increase limits: Update `rate_limit` decorators
2. Review traffic patterns in Grafana
3. Add IP whitelisting for known good actors
4. Scale horizontally if traffic is legitimate

---

#### Issue: Vector Search Slow

**Symptoms**: `/ml/score` endpoint >500ms, timeouts

**Diagnosis**:
```bash
# Check Qdrant metrics
curl http://qdrant:6333/metrics | grep search_duration

# Check collection size
curl http://qdrant:6333/collections/properties | jq .result.points_count
```

**Resolution**:
1. Check if indexes need rebuilding
2. Verify HNSW parameters are tuned
3. Increase Qdrant memory allocation
4. Consider collection partitioning

---

### Emergency Procedures

#### Complete System Failure

```bash
# 1. Activate disaster recovery
ssh deploy@dr.example.com

# 2. Restore from backups
bash scripts/ops/restore_from_backup.sh

# 3. Verify data integrity
python scripts/ops/verify_data_integrity.py

# 4. Bring up services one by one
docker-compose up -d postgres
docker-compose up -d redis
docker-compose up -d api

# 5. Run smoke tests
bash scripts/ops/smoke_tests.sh
```

#### Data Corruption

```bash
# 1. Immediately stop writes
docker-compose stop api

# 2. Restore from last known good backup
pg_restore -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB backup_<timestamp>.sql

# 3. Verify data integrity
python scripts/ops/verify_data_integrity.py

# 4. Review audit logs
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c \
  "SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 100;"
```

---

## Emergency Contacts

### On-Call Rotation

| Role | Primary | Secondary |
|------|---------|-----------|
| Platform Lead | +1-555-0001 | +1-555-0002 |
| Database Admin | +1-555-0003 | +1-555-0004 |
| DevOps Engineer | +1-555-0005 | +1-555-0006 |

### Escalation Path

1. **Level 1**: On-call engineer (respond within 15 min)
2. **Level 2**: Platform lead (respond within 30 min)
3. **Level 3**: CTO (respond within 1 hour)

### External Contacts

- **AWS Support**: +1-866-947-2277 (Enterprise Support)
- **Sentry Support**: support@sentry.io
- **Database Vendor**: support@postgresql.org

---

## Appendix

### Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-02 | Initial runbook | Platform Team |

### Related Documents

- [Architecture Overview](./ARCHITECTURE.md)
- [Security Policies](./SECURITY.md)
- [Disaster Recovery Plan](./DISASTER_RECOVERY.md)
- [Monitoring Guide](./MONITORING.md)

---

**Document Status**: ✅ Approved
**Next Review**: 2025-12-01
