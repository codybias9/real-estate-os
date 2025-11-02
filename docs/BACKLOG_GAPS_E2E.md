# Real Estate OS - Prioritized Gap Backlog

**Last Updated**: 2025-11-02
**Source**: End-to-End Platform Audit
**Total Work Items**: 34 (15 P0, 12 P1, 7 P2)

---

## P0: Production Blockers (MUST FIX)

These items **MUST** be completed before any production deployment. Without these, the platform is non-functional or critically insecure.

### P0-1: Deploy PostgreSQL Database

**Priority**: P0 (Critical)
**Effort**: 2 days
**Owner**: DevOps / DBA

**Problem**: No database exists to store data. Migrations are defined but not applied.

**Definition of Done**:
- [ ] PostgreSQL 13+ running and accessible
- [ ] All 3 migrations applied successfully:
  - `001_create_base_schema_with_rls.sql`
  - `002_create_property_hazards_table.sql`
  - `003_create_field_provenance_table.sql`
- [ ] PostGIS extension enabled and verified
- [ ] Connection string documented in `.env`
- [ ] Health check returns `SELECT 1` successfully
- [ ] Artifact created: `/artifacts/db/apply-log.txt` with migration output
- [ ] Artifact created: `/artifacts/db/schema-dump.sql` with `pg_dump --schema-only`

**Verification**:
```bash
psql $DATABASE_URL -c "\dt"  # List all tables
psql $DATABASE_URL -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"  # Should be 10+
```

**Blocked By**: None
**Blocks**: P0-2, P0-3, P0-4, P0-5

---

### P0-2: Deploy API Service

**Priority**: P0 (Critical)
**Effort**: 3 days
**Owner**: Backend Team

**Problem**: API code exists but is not running. Cannot test endpoints or authentication.

**Definition of Done**:
- [ ] API running with uvicorn/gunicorn in docker container
- [ ] Health endpoint `/health` returns 200
- [ ] OpenAPI docs served at `/docs`
- [ ] All 71 endpoints discoverable
- [ ] CORS configured (no wildcard `*`)
- [ ] Rate limiting active (Redis connected)
- [ ] Environment variables loaded from `.env`
- [ ] Artifact created: `/artifacts/api/openapi.json` (download from `/openapi.json`)
- [ ] Artifact created: `/artifacts/api/health-check.txt` (`curl http://localhost:8000/health`)
- [ ] Artifact created: `/artifacts/api/cors-config.txt` (CORS headers from response)

**Verification**:
```bash
curl http://localhost:8000/health | jq .
curl http://localhost:8000/docs  # Should show Swagger UI
curl http://localhost:8000/openapi.json > artifacts/api/openapi.json
```

**Blocked By**: P0-1 (needs database)
**Blocks**: P0-4, P0-6, P0-7

---

### P0-3: Deploy Keycloak Authentication

**Priority**: P0 (Critical)
**Effort**: 4 days
**Owner**: Security / DevOps

**Problem**: Authentication service not deployed. Cannot issue JWTs or validate tokens.

**Definition of Done**:
- [ ] Keycloak 24+ running in docker
- [ ] Realm `real-estate-os` created
- [ ] Client `api-client` configured with RS256
- [ ] JWKS endpoint accessible at `http://keycloak:8080/realms/real-estate-os/protocol/openid-connect/certs`
- [ ] Test user created: `test@example.com` / `TestPassword123!`
- [ ] Role `investor` assigned to test user
- [ ] API can fetch and cache JWKS
- [ ] Artifact created: `/artifacts/security/keycloak-realm-export.json`
- [ ] Artifact created: `/artifacts/security/test-token.txt` (valid JWT)
- [ ] Artifact created: `/artifacts/security/token-validation-log.txt` (API validates token)

**Verification**:
```bash
# Get token
curl -X POST http://localhost:8080/realms/real-estate-os/protocol/openid-connect/token \
  -d "client_id=api-client" \
  -d "username=test@example.com" \
  -d "password=TestPassword123!" \
  -d "grant_type=password" | jq .access_token

# Use token with API
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/properties | jq .
```

**Blocked By**: None
**Blocks**: P0-4, P0-6

---

### P0-4: Prove Row-Level Security Works

**Priority**: P0 (Critical - Security)
**Effort**: 2 days
**Owner**: Security Team

**Problem**: RLS policies are defined but never tested. Cross-tenant data leakage is possible.

**Definition of Done**:
- [ ] Create 2 test tenants in database:
  - Tenant A: `11111111-1111-1111-1111-111111111111`
  - Tenant B: `22222222-2222-2222-2222-222222222222`
- [ ] Insert 5 properties for Tenant A
- [ ] Insert 5 properties for Tenant B
- [ ] Execute negative test: `SET LOCAL app.tenant_id='11111111-...'` then `SELECT * FROM properties`
- [ ] Verify: Returns only Tenant A's 5 properties (not Tenant B's)
- [ ] Execute cross-tenant attack: Attempt to `UPDATE` Tenant B property while set to Tenant A
- [ ] Verify: Update fails or affects 0 rows
- [ ] Test all 10 tables with RLS
- [ ] Artifact created: `/artifacts/isolation/rls-explain.txt` (`SHOW POLICIES` output)
- [ ] Artifact created: `/artifacts/isolation/negative-tests-db.txt` (all test queries + results)
- [ ] Document: `/docs/SECURITY_RLS_PROOF.md` with attack scenarios

**Verification Script**:
```sql
-- artifacts/isolation/negative-tests-db.sql
SET LOCAL app.tenant_id='11111111-1111-1111-1111-111111111111';

SELECT count(*) FROM properties;  -- Should be 5, not 10

SET LOCAL app.tenant_id='22222222-2222-2222-2222-222222222222';
UPDATE properties SET list_price = 999999 WHERE tenant_id = '11111111-1111-1111-1111-111111111111';
-- Should affect 0 rows
```

**Blocked By**: P0-1 (needs database)
**Blocks**: None (but critical for production)

---

### P0-5: Prove Great Expectations Blocks Bad Data

**Priority**: P0 (Critical - Data Quality)
**Effort**: 3 days
**Owner**: Data Engineering

**Problem**: GX code exists but never proven to halt pipelines on validation failure.

**Definition of Done**:
- [ ] Initialize GX project: `great_expectations init`
- [ ] Create suite `properties_suite` with 10 expectations:
  - `expect_column_values_to_not_be_null` (property_id, tenant_id, address)
  - `expect_column_values_to_be_between` (list_price: 10k-50M)
  - `expect_column_values_to_be_between` (bedrooms: 0-100)
  - `expect_column_values_to_match_regex` (zip_code: `^\d{5}$`)
  - Plus 6 more relevant validations
- [ ] Create checkpoint `properties_checkpoint`
- [ ] Insert intentionally failing data:
  - Property with `list_price = NULL`
  - Property with `bedrooms = 999`
  - Property with `zip_code = 'INVALID'`
- [ ] Run checkpoint: `great_expectations checkpoint run properties_checkpoint`
- [ ] Verify: Checkpoint FAILS (non-zero exit code)
- [ ] Generate Data Docs: `great_expectations docs build`
- [ ] Screenshot Data Docs showing failures
- [ ] Integrate into Airflow DAG with `AirflowFailException` on validation failure
- [ ] Artifact created: `/artifacts/data-quality/data-docs-index.html` (copy from `uncommitted/data_docs/`)
- [ ] Artifact created: `/artifacts/data-quality/failing-checkpoint.log`
- [ ] Artifact created: `/artifacts/data-quality/checkpoint-config.yaml`
- [ ] Artifact created: `/artifacts/data-quality/data-docs-screenshot.png`

**Verification**:
```bash
great_expectations checkpoint run properties_checkpoint
# Exit code should be 1 (failure)

ls uncommitted/data_docs/local_site/index.html
# Should exist

# Open in browser and screenshot validation results
```

**Blocked By**: P0-1 (needs database), P0-11 (needs Airflow)
**Blocks**: None (but critical for production)

---

### P0-6: API Authentication Integration Test

**Priority**: P0 (Critical - Security)
**Effort**: 2 days
**Owner**: Backend + Security

**Problem**: Auth middleware exists but never tested with actual tokens.

**Definition of Done**:
- [ ] Test 1: Request without token → 401 Unauthorized
- [ ] Test 2: Request with invalid token → 401 Unauthorized
- [ ] Test 3: Request with expired token → 401 Unauthorized
- [ ] Test 4: Request with valid token but wrong role → 403 Forbidden
- [ ] Test 5: Request with valid token and correct role → 200 OK
- [ ] Artifact created: `/artifacts/security/authz-test-transcripts.txt` (all 5 test curl commands + responses)

**Verification Script**:
```bash
# Test 1: No token
curl -v http://localhost:8000/api/v1/properties 2>&1 | grep "401"

# Test 2: Invalid token
curl -v -H "Authorization: Bearer invalid_token_here" http://localhost:8000/api/v1/properties 2>&1 | grep "401"

# Test 3: Valid token
TOKEN=$(get_token_from_keycloak)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/properties | jq .
```

**Blocked By**: P0-2 (API), P0-3 (Keycloak)
**Blocks**: P0-7

---

### P0-7: API Cross-Tenant Isolation Test

**Priority**: P0 (Critical - Security)
**Effort**: 2 days
**Owner**: Security Team

**Problem**: API might not enforce tenant isolation even if DB RLS works.

**Definition of Done**:
- [ ] Create 2 test users in Keycloak:
  - User A: `alice@tenanta.com` → tenant_id `11111111-...`
  - User B: `bob@tenantb.com` → tenant_id `22222222-...`
- [ ] Insert properties for both tenants
- [ ] Get JWT for User A
- [ ] Call `GET /api/v1/properties` with User A token
- [ ] Verify: Returns only Tenant A properties
- [ ] Attempt `GET /api/v1/properties/{tenant_b_property_id}` with User A token
- [ ] Verify: Returns 404 or 403 (not the property)
- [ ] Attempt `DELETE /api/v1/properties/{tenant_b_property_id}` with User A token
- [ ] Verify: Returns 403 and property NOT deleted
- [ ] Artifact created: `/artifacts/isolation/negative-tests-api.txt` (all attack scenarios + responses)

**Verification**:
```bash
# Get tokens
TOKEN_A=$(get_token alice@tenanta.com)
TOKEN_B=$(get_token bob@tenantb.com)

# Create property as Tenant B
PROP_B_ID=$(curl -X POST -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"address":"123 B Street","city":"B-Town","state":"CA"}' \
  http://localhost:8000/api/v1/properties | jq -r .id)

# Try to access as Tenant A (should fail)
curl -H "Authorization: Bearer $TOKEN_A" \
  http://localhost:8000/api/v1/properties/$PROP_B_ID
# Should return 404 or 403
```

**Blocked By**: P0-2 (API), P0-3 (Keycloak), P0-4 (RLS)
**Blocks**: None (but critical for production)

---

### P0-8: Rate Limiting Functional Test

**Priority**: P0 (Critical - DoS Protection)
**Effort**: 1 day
**Owner**: Backend Team

**Problem**: Rate limiting code exists but never tested.

**Definition of Done**:
- [ ] Verify Redis is running and API connected
- [ ] Identify endpoint with 60 req/min limit (e.g., `POST /api/v1/properties`)
- [ ] Send 65 requests in 60 seconds
- [ ] Verify: Requests 1-60 succeed (200/201)
- [ ] Verify: Request 61 returns 429 Too Many Requests
- [ ] Verify: Response includes headers:
  - `X-RateLimit-Limit: 60`
  - `X-RateLimit-Remaining: 0`
  - `Retry-After: <seconds>`
- [ ] Wait for window to reset
- [ ] Verify: Next request succeeds
- [ ] Artifact created: `/artifacts/security/rate-limits-proof.txt` (request log with 429 response)

**Verification Script**:
```bash
# Send 65 requests rapidly
for i in {1..65}; do
  curl -s -w "\n%{http_code}\n" -H "Authorization: Bearer $TOKEN" \
    -X POST http://localhost:8000/api/v1/ml/dcf/calculate \
    -H "Content-Type: application/json" \
    -d '{"property_value": 1000000, ...}' >> rate_limit_test.log
  sleep 0.5  # 2 req/sec = 120/min, should hit limit
done

# Check for 429
grep "429" rate_limit_test.log | wc -l  # Should be 5+
```

**Blocked By**: P0-2 (API), P0-12 (Redis)
**Blocks**: None

---

### P0-9: Run All Tests with Coverage

**Priority**: P0 (Quality Gate)
**Effort**: 1 day
**Owner**: QA / Backend

**Problem**: 126 test methods exist but no proof they pass.

**Definition of Done**:
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] pytest runs successfully: `pytest tests/`
- [ ] All 126 tests pass (0 failures)
- [ ] Coverage measured: `pytest --cov=. --cov-report=html --cov-report=term`
- [ ] Coverage ≥40% (current baseline)
- [ ] Coverage report HTML generated: `htmlcov/index.html`
- [ ] Artifact created: `/artifacts/tests/test-summary.txt` (pytest output)
- [ ] Artifact created: `/artifacts/tests/coverage-report.txt` (coverage %)
- [ ] Artifact created: `/artifacts/tests/htmlcov/` (copy entire directory)

**Verification**:
```bash
pytest tests/ -v --cov=. --cov-report=term-missing > artifacts/tests/test-summary.txt
# Should end with "126 passed"

grep "TOTAL" artifacts/tests/test-summary.txt
# Should show coverage percentage
```

**Blocked By**: P0-1 (some tests need DB), P0-2 (some tests need API)
**Blocks**: P0-13 (CI setup)

---

### P0-10: Create GitHub Actions CI Workflow

**Priority**: P0 (Prevents Regressions)
**Effort**: 1 day
**Owner**: DevOps

**Problem**: No CI means code quality degrades over time.

**Definition of Done**:
- [ ] File created: `.github/workflows/ci.yml`
- [ ] Workflow triggers on: `push`, `pull_request`
- [ ] Workflow steps:
  1. Checkout code
  2. Set up Python 3.11
  3. Install dependencies
  4. Run pytest with coverage
  5. Fail if any test fails
  6. Fail if coverage < 40%
- [ ] Workflow runs on every PR
- [ ] Badge added to README: `![CI](https://github.com/.../workflows/ci.yml/badge.svg)`
- [ ] Artifact created: `/artifacts/ci/workflows-list.txt` (list of workflows)
- [ ] Artifact created: `/artifacts/ci/last-run-logs.txt` (latest CI run output)

**Verification**:
```bash
# Push commit and check GitHub Actions
git add .github/workflows/ci.yml
git commit -m "Add CI workflow"
git push

# Check run status
gh run list --limit 1
gh run view --log > artifacts/ci/last-run-logs.txt
```

**Blocked By**: P0-9 (tests must pass first)
**Blocks**: None

---

### P0-11: Deploy Airflow for Data Pipelines

**Priority**: P0 (Data Processing)
**Effort**: 2 days
**Owner**: Data Engineering / DevOps

**Problem**: 7 real pipelines exist but Airflow not running.

**Definition of Done**:
- [ ] Airflow running via docker-compose
- [ ] Webserver accessible at `http://localhost:8080`
- [ ] Scheduler running and processing DAGs
- [ ] All 17 DAGs visible in UI
- [ ] Test DAG executed successfully: `minimal_e2e_pipeline`
- [ ] DAG run logs captured
- [ ] Artifact created: `/artifacts/dags/e2e-run-log.txt` (DAG execution log)
- [ ] Artifact created: `/artifacts/dags/airflow-ui-screenshot.png` (DAG list)

**Verification**:
```bash
docker-compose up -d postgres redis airflow-webserver airflow-scheduler

# Wait for startup
sleep 30

# Trigger test DAG
airflow dags test minimal_e2e_pipeline 2025-11-02 > artifacts/dags/e2e-run-log.txt

# Check status
grep "SUCCESS" artifacts/dags/e2e-run-log.txt
```

**Blocked By**: P0-1 (needs DB), P0-12 (needs Redis)
**Blocks**: P0-5 (GX gates), P1-5 (lineage)

---

### P0-12: Deploy Redis for Caching & Rate Limiting

**Priority**: P0 (Infrastructure)
**Effort**: 0.5 days
**Owner**: DevOps

**Problem**: Redis required for rate limiting but not verified running.

**Definition of Done**:
- [ ] Redis 7.2 running in docker
- [ ] Accessible at `localhost:6379`
- [ ] Ping succeeds: `redis-cli PING` returns `PONG`
- [ ] API can connect and set/get keys
- [ ] Rate limit counters visible: `redis-cli KEYS "rate_limit:*"`
- [ ] Artifact created: `/artifacts/infra/redis-info.txt` (`redis-cli INFO`)

**Verification**:
```bash
docker-compose up -d redis
redis-cli PING  # Should return PONG
redis-cli INFO > artifacts/infra/redis-info.txt
```

**Blocked By**: None
**Blocks**: P0-2 (API rate limiting), P0-8 (rate limit tests)

---

### P0-13: SQL Injection Attack Test

**Priority**: P0 (Critical - Security)
**Effort**: 1 day
**Owner**: Security Team

**Problem**: No proof that API is safe from SQL injection.

**Definition of Done**:
- [ ] Test 10 injection attack scenarios:
  1. `GET /properties?city='; DROP TABLE properties; --`
  2. `POST /properties` with `{"address": "' OR '1'='1"}`
  3. UUID injection in path params
  4. JSON injection in body
  5. Plus 6 more OWASP patterns
- [ ] Verify: All attacks fail safely (no DB corruption)
- [ ] Verify: Logs show attempted attacks
- [ ] No tables dropped
- [ ] No unauthorized data access
- [ ] Artifact created: `/artifacts/security/sql-injection-tests.txt` (all attack attempts + responses)

**Verification**:
```bash
# Attempt SQL injection
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/properties?city='; DROP TABLE properties; --" \
  | tee -a artifacts/security/sql-injection-tests.txt

# Verify table still exists
psql $DATABASE_URL -c "\dt properties"
# Should still show table
```

**Blocked By**: P0-2 (API), P0-1 (DB)
**Blocks**: None (but critical for production)

---

### P0-14: Environment Variables Security Audit

**Priority**: P0 (Critical - Secrets)
**Effort**: 0.5 days
**Owner**: Security / DevOps

**Problem**: No verification that secrets are not committed to git.

**Definition of Done**:
- [ ] Scan entire repo for secrets: `git secrets --scan`
- [ ] Check for patterns:
  - API keys
  - Database passwords
  - JWT secrets
  - AWS keys
- [ ] Verify `.env` is in `.gitignore`
- [ ] Verify no `.env` files in git history
- [ ] Create `.env.example` with placeholders
- [ ] Document required env vars in README
- [ ] Artifact created: `/artifacts/security/secrets-scan.txt` (scan results, should be clean)

**Verification**:
```bash
# Install git-secrets
git secrets --scan --recursive > artifacts/security/secrets-scan.txt

# Should show no matches
cat artifacts/security/secrets-scan.txt  # Should be empty or say "no secrets found"

# Verify .env not committed
git log --all --full-history --source -- .env
# Should return nothing
```

**Blocked By**: None
**Blocks**: None (but critical for production)

---

### P0-15: Database Backup & Restore Test

**Priority**: P0 (DR)
**Effort**: 1 day
**Owner**: DBA / DevOps

**Problem**: No disaster recovery plan or tested backups.

**Definition of Done**:
- [ ] Create full database backup: `pg_dump`
- [ ] Create backup of 1000 properties
- [ ] Simulate disaster: DROP 1 table
- [ ] Restore from backup
- [ ] Verify: All 1000 properties restored
- [ ] Document backup procedure in `/docs/BACKUP_RESTORE.md`
- [ ] Automate daily backups (cron or k8s CronJob)
- [ ] Artifact created: `/artifacts/dr/backup-test.txt` (backup + restore logs)
- [ ] Artifact created: `/artifacts/dr/sample-backup.sql.gz` (sample backup file)

**Verification**:
```bash
# Backup
pg_dump $DATABASE_URL -Fc -f backup_$(date +%Y%m%d).dump

# Simulate disaster
psql $DATABASE_URL -c "DROP TABLE properties CASCADE"

# Restore
pg_restore -d $DATABASE_URL backup_20251102.dump

# Verify
psql $DATABASE_URL -c "SELECT count(*) FROM properties"  # Should be 1000
```

**Blocked By**: P0-1 (DB)
**Blocks**: None (but critical for production)

---

## P1: Pre-Production Requirements (SHOULD FIX)

These items should be completed before production but aren't immediate blockers. They enable operations, monitoring, and reliability.

### P1-1: Deploy Prometheus for Metrics

**Priority**: P1 (Observability)
**Effort**: 2 days
**Owner**: SRE / DevOps

**Problem**: No metrics collection means blind operations.

**Definition of Done**:
- [ ] Prometheus running in docker
- [ ] Scraping API `/metrics` endpoint every 15s
- [ ] 10+ metrics collected:
  - `http_requests_total`
  - `http_request_duration_seconds`
  - `db_query_duration_seconds`
  - `redis_connection_pool_size`
  - Plus 6 more
- [ ] PromQL queries work
- [ ] Artifact created: `/artifacts/observability/prom-targets.png` (screenshot of targets page)
- [ ] Artifact created: `/artifacts/observability/prom-queries.txt` (sample PromQL queries + results)

**Verification**:
```bash
curl http://localhost:9090/targets  # Should show API target UP
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=rate(http_requests_total[5m])' | jq .
```

**Blocked By**: P0-2 (API must expose /metrics)
**Blocks**: P1-2 (Grafana)

---

### P1-2: Deploy Grafana with Dashboards

**Priority**: P1 (Observability)
**Effort**: 2 days
**Owner**: SRE

**Problem**: Metrics exist but no visualization.

**Definition of Done**:
- [ ] Grafana running in docker
- [ ] Prometheus configured as datasource
- [ ] 3 dashboards created:
  1. **API Performance**: Request rate, latency p50/p95/p99, error rate
  2. **Database**: Connection pool, query duration, slow queries
  3. **Business Metrics**: Properties created, valuations run, offers generated
- [ ] Dashboards accessible at `http://localhost:3000`
- [ ] Artifact created: `/artifacts/observability/grafana-dashboards.json` (export all dashboards)
- [ ] Artifact created: `/artifacts/observability/dashboard-screenshots/` (PNG of each dashboard)

**Verification**:
```bash
# Export dashboards
curl -u admin:admin http://localhost:3000/api/dashboards/db/api-performance | jq . > \
  artifacts/observability/grafana-dashboards.json

# Screenshot manually or with headless browser
```

**Blocked By**: P1-1 (Prometheus)
**Blocks**: None

---

### P1-3: Deploy Sentry for Error Tracking

**Priority**: P1 (Observability)
**Effort**: 1 day
**Owner**: Backend + SRE

**Problem**: No error tracking means debugging production issues is difficult.

**Definition of Done**:
- [ ] Sentry account created (free tier OK)
- [ ] DSN configured in `.env`: `SENTRY_DSN=https://...@sentry.io/...`
- [ ] API initializes Sentry on startup
- [ ] Test event sent: `sentry_sdk.capture_message("Test event")`
- [ ] Verify event appears in Sentry dashboard
- [ ] Error context includes:
  - User ID
  - Tenant ID
  - Request ID
  - Stack trace
- [ ] Artifact created: `/artifacts/observability/sentry-test-event.txt` (screenshot or event JSON)

**Verification**:
```bash
# Trigger test error
curl -X POST http://localhost:8000/api/v1/debug/error

# Check Sentry dashboard
# Event should appear with full context
```

**Blocked By**: P0-2 (API)
**Blocks**: None

---

### P1-4: Load Test Critical Endpoints

**Priority**: P1 (Performance)
**Effort**: 2 days
**Owner**: QA + Backend

**Problem**: Performance under load is unknown.

**Definition of Done**:
- [ ] Locust load test script created: `tests/load/locustfile.py`
- [ ] Test scenarios for 5 endpoints:
  1. `GET /api/v1/properties` (list)
  2. `GET /api/v1/properties/{id}` (get)
  3. `POST /api/v1/properties` (create)
  4. `POST /api/v1/ml/dcf/calculate` (valuation)
  5. `POST /api/v1/twins/search` (vector search)
- [ ] Run test: 100 users, 10 req/s/user, 5 minutes
- [ ] Measure p50, p95, p99 latencies
- [ ] Measure throughput (req/s)
- [ ] Identify bottlenecks
- [ ] Artifact created: `/artifacts/perf/load-scenarios.md` (test scenarios)
- [ ] Artifact created: `/artifacts/perf/latency-snapshots.csv` (p50/p95/p99 for each endpoint)
- [ ] Artifact created: `/artifacts/perf/locust-report.html` (Locust HTML report)

**Verification**:
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
  --users=100 --spawn-rate=10 --run-time=5m --html=artifacts/perf/locust-report.html

# Extract latencies
grep "p95" artifacts/perf/locust-report.html > artifacts/perf/latency-snapshots.csv
```

**Blocked By**: P0-2 (API), P0-1 (DB)
**Blocks**: P1-6 (set SLOs)

---

### P1-5: Deploy Marquez for Lineage Visualization

**Priority**: P1 (Data Lineage)
**Effort**: 2 days
**Owner**: Data Engineering

**Problem**: OpenLineage events emitted but no visualization.

**Definition of Done**:
- [ ] Marquez running in docker
- [ ] OpenLineage events sent to Marquez from Airflow DAG
- [ ] Run `property_pipeline_with_lineage` DAG
- [ ] Verify lineage graph appears in Marquez UI
- [ ] Screenshot DAG lineage showing:
  - Input datasets
  - Transformations
  - Output datasets
  - Data quality gates
- [ ] Artifact created: `/artifacts/lineage/marquez-dag-run-20251102.png` (screenshot)
- [ ] Artifact created: `/artifacts/lineage/lineage-event-sample.json` (one OpenLineage event payload)

**Verification**:
```bash
# Run DAG
airflow dags test property_pipeline_with_lineage 2025-11-02

# Check Marquez
curl http://localhost:5000/api/v1/namespaces/default/jobs | jq .

# Screenshot UI manually
```

**Blocked By**: P0-11 (Airflow)
**Blocks**: None

---

### P1-6: Set SLOs and Alerting

**Priority**: P1 (Reliability)
**Effort**: 2 days
**Owner**: SRE

**Problem**: No SLOs means no reliability targets.

**Definition of Done**:
- [ ] SLOs defined for 5 critical user journeys:
  1. Property valuation (p95 < 2s)
  2. Property search (p95 < 500ms)
  3. Offer generation (p95 < 5s)
  4. Lease parsing (p95 < 3s)
  5. Twin search (p95 < 1s)
- [ ] Prometheus recording rules created for SLIs
- [ ] Alertmanager configured
- [ ] Alerts fire when SLO violated:
  - Slack notification
  - Email to on-call
- [ ] Test alert: Intentionally break API to violate SLO
- [ ] Artifact created: `/artifacts/observability/slo-definitions.yaml`
- [ ] Artifact created: `/artifacts/observability/alert-rules.yaml`
- [ ] Artifact created: `/artifacts/observability/test-alert-screenshot.png`

**Verification**:
```bash
# Check recording rules
curl http://localhost:9090/api/v1/rules | jq .

# Trigger alert (simulate high latency)
# Then check Slack for notification
```

**Blocked By**: P1-1 (Prometheus), P1-4 (know baseline latencies)
**Blocks**: None

---

### P1-7: Deploy Qdrant Vector Database

**Priority**: P1 (Features)
**Effort**: 2 days
**Owner**: Backend + ML

**Problem**: Property twin search code exists but no vector DB.

**Definition of Done**:
- [ ] Qdrant running in docker
- [ ] Collection `property_embeddings` created with 128-dimensional vectors
- [ ] Tenant isolation via filters: `must=[{"key": "tenant_id", "match": {"value": "..."}}]`
- [ ] Index 10 test properties
- [ ] Execute twin search for 1 property
- [ ] Verify: Returns 5 similar properties with scores
- [ ] Test cross-tenant isolation: Search with wrong tenant_id filter returns 0 results
- [ ] Artifact created: `/artifacts/isolation/qdrant-filter-proof.json` (search request + response)
- [ ] Artifact created: `/artifacts/ml/twin-search-results.json` (sample search output)

**Verification**:
```bash
# Create collection
curl -X PUT http://localhost:6333/collections/property_embeddings \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 128, "distance": "Cosine"}}'

# Insert property
curl -X PUT http://localhost:6333/collections/property_embeddings/points \
  -d '{"points": [{"id": 1, "vector": [...128 dims...], "payload": {"tenant_id": "..."}}]}'

# Search with tenant filter
curl -X POST http://localhost:6333/collections/property_embeddings/points/search \
  -d '{"vector": [...], "filter": {"must": [{"key": "tenant_id", "match": {"value": "..."}}]}, "limit": 5}' \
  > artifacts/isolation/qdrant-filter-proof.json
```

**Blocked By**: None (can run standalone)
**Blocks**: P2-2 (twin search integration)

---

### P1-8: Deploy Neo4j Graph Database

**Priority**: P1 (Features)
**Effort**: 2 days
**Owner**: Backend

**Problem**: Relationship graph code exists but no graph DB.

**Definition of Done**:
- [ ] Neo4j running in docker
- [ ] Node types created: Owner, Property, Tenant, Lender
- [ ] Relationship types created: OWNS, RENTS, FINANCED_BY
- [ ] Insert test data: 5 owners, 10 properties, 3 tenants
- [ ] Execute Cypher query: Find all properties owned by owner X
- [ ] Execute PageRank to find influential owners
- [ ] Test tenant isolation: Queries filtered by tenant_id property
- [ ] Artifact created: `/artifacts/graph/sample-queries.cypher` (5 example queries)
- [ ] Artifact created: `/artifacts/graph/query-results.json` (results from each query)
- [ ] Artifact created: `/artifacts/graph/graph-screenshot.png` (Neo4j Browser visualization)

**Verification**:
```bash
# Connect to Neo4j
docker exec -it neo4j cypher-shell

# Create nodes
CREATE (o:Owner {id: '...', tenant_id: '...', name: 'Alice'})
CREATE (p:Property {id: '...', tenant_id: '...', address: '123 Main St'})
CREATE (o)-[:OWNS {percentage: 100}]->(p)

# Query
MATCH (o:Owner {tenant_id: '11111111-...'})-[:OWNS]->(p:Property)
RETURN o.name, p.address
```

**Blocked By**: None
**Blocks**: P2-3 (graph integration)

---

### P1-9: Deploy MinIO Object Storage

**Priority**: P1 (Features)
**Effort**: 1 day
**Owner**: Backend + DevOps

**Problem**: Document management code exists but no object storage.

**Definition of Done**:
- [ ] MinIO running in docker
- [ ] Bucket created: `real-estate-os`
- [ ] Prefix strategy: `{tenant_id}/documents/{document_id}`
- [ ] Test: Upload document for Tenant A
- [ ] Test: List documents with prefix `{tenant_a_id}/`
- [ ] Test cross-tenant: Attempt to list `{tenant_b_id}/` with Tenant A credentials
- [ ] Verify: Access denied or 0 results
- [ ] Artifact created: `/artifacts/isolation/minio-prefix-proof.txt` (upload + list + cross-tenant test)

**Verification**:
```bash
# Configure mc (MinIO client)
mc alias set local http://localhost:9000 minioadmin minioadmin

# Upload file
mc cp test.pdf local/real-estate-os/11111111-1111-1111-1111-111111111111/documents/test.pdf

# List (should succeed)
mc ls local/real-estate-os/11111111-1111-1111-1111-111111111111/

# Try to list other tenant (should fail or be empty)
mc ls local/real-estate-os/22222222-2222-2222-2222-222222222222/
```

**Blocked By**: None
**Blocks**: P2-4 (document upload integration)

---

### P1-10: Negative Security Test Suite

**Priority**: P1 (Security)
**Effort**: 3 days
**Owner**: Security Team

**Problem**: Only basic auth tested; need comprehensive attack scenarios.

**Definition of Done**:
- [ ] 20 attack scenarios tested:
  1. SQL injection (5 variants)
  2. XSS (3 variants)
  3. CSRF (if applicable)
  4. JWT tampering (3 variants)
  5. Role escalation (3 variants)
  6. Cross-tenant access (3 variants)
  7. Rate limit bypass
  8. Path traversal
- [ ] All attacks fail safely
- [ ] Attacks logged to audit trail
- [ ] Artifact created: `/artifacts/security/attack-scenarios.md` (full test plan)
- [ ] Artifact created: `/artifacts/security/attack-results.txt` (all attack attempts + outcomes)

**Verification**: Run all 20 scenarios, verify all fail

**Blocked By**: P0-2 (API), P0-3 (Keycloak)
**Blocks**: None

---

### P1-11: Increase Test Coverage to 70%

**Priority**: P1 (Quality)
**Effort**: 5 days
**Owner**: Backend Team

**Problem**: 126 tests exist but coverage unknown (likely <50%).

**Definition of Done**:
- [ ] Run coverage: `pytest --cov=. --cov-report=html`
- [ ] Identify uncovered modules
- [ ] Write tests to reach 70% total coverage
- [ ] All new tests pass
- [ ] Coverage report shows ≥70%
- [ ] Artifact created: `/artifacts/tests/coverage-before.txt` (baseline)
- [ ] Artifact created: `/artifacts/tests/coverage-after.txt` (after new tests)
- [ ] Artifact created: `/artifacts/tests/coverage-diff.txt` (diff showing improvement)

**Verification**:
```bash
pytest --cov=. --cov-report=term > artifacts/tests/coverage-after.txt
grep "TOTAL" artifacts/tests/coverage-after.txt
# Should show ≥70%
```

**Blocked By**: P0-9 (baseline coverage)
**Blocks**: None

---

### P1-12: Chaos Testing - Kill Vector DB

**Priority**: P1 (Resilience)
**Effort**: 1 day
**Owner**: SRE

**Problem**: Don't know how system behaves when dependencies fail.

**Definition of Done**:
- [ ] Qdrant running
- [ ] API using Qdrant for twin search
- [ ] Execute twin search (succeeds)
- [ ] Kill Qdrant: `docker stop qdrant`
- [ ] Execute twin search again
- [ ] Verify: API returns graceful error (500 or 503, not crash)
- [ ] Verify: Error logged to Sentry
- [ ] Verify: Prometheus alert fires
- [ ] Restart Qdrant
- [ ] Verify: API recovers (next request succeeds)
- [ ] Artifact created: `/artifacts/perf/vector-chaos-log.txt` (error logs + recovery)

**Verification**:
```bash
# Before
curl -X POST http://localhost:8000/api/v1/twins/search -d '...'  # Succeeds

# Kill
docker stop qdrant

# During
curl -X POST http://localhost:8000/api/v1/twins/search -d '...'  # Fails gracefully

# Restart
docker start qdrant
sleep 10

# After
curl -X POST http://localhost:8000/api/v1/twins/search -d '...'  # Succeeds
```

**Blocked By**: P1-7 (Qdrant)
**Blocks**: None

---

## P2: Nice-to-Have Improvements

These items improve the platform but aren't critical for production deployment.

### P2-1: Train Actual ML Models

**Priority**: P2 (Features)
**Effort**: 10 days
**Owner**: ML Team

**Problem**: All ML is rules-based; no learned models.

**Decision Required**: Determine if ML is needed or if rules-based is sufficient.

**If ML is needed**:
- [ ] Gather training data (1000+ properties with sale prices)
- [ ] Train Comp-Critic hedonic model
- [ ] Evaluate on hold-out set (MAE, RMSE)
- [ ] Save model artifact: `models/comp_critic_v1.pkl`
- [ ] Set up MLflow model registry
- [ ] Deploy model to API
- [ ] Artifact created: `/artifacts/ml/training-metrics.json` (loss curves, MAE, RMSE)
- [ ] Artifact created: `/artifacts/ml/model-card.md` (model documentation)

**If rules-based is sufficient**:
- [ ] Document decision in `/docs/ARCHITECTURE.md`
- [ ] Remove ML infrastructure (Feast, etc.)
- [ ] Simplify code to remove ML abstractions

**Verification**: TBD based on decision

**Blocked By**: Product decision
**Blocks**: P2-5 (model registry)

---

### P2-2: Integrate Property Twin Search End-to-End

**Priority**: P2 (Features)
**Effort**: 3 days
**Owner**: Backend + ML

**Problem**: Code exists but not integrated with live data.

**Definition of Done**:
- [ ] All properties auto-indexed to Qdrant on creation
- [ ] API endpoint `POST /api/v1/twins/search` works end-to-end
- [ ] Search returns real similar properties from database
- [ ] Similarity scores make sense (high for actual similar properties)
- [ ] Performance meets SLO (p95 < 1s for search)
- [ ] Artifact created: `/artifacts/ml/twin-search-demo.json` (search for 1 property, results with scores)

**Verification**:
```bash
# Create property
curl -X POST http://localhost:8000/api/v1/properties -d '{"address": "456 Oak St", ...}'

# Search for twins (should auto-index)
curl -X POST http://localhost:8000/api/v1/twins/search \
  -d '{"property_type": "Residential", "building_sqft": 2000, ...}' \
  > artifacts/ml/twin-search-demo.json

# Verify results are relevant
jq '.twins[] | {address, similarity_score}' artifacts/ml/twin-search-demo.json
```

**Blocked By**: P1-7 (Qdrant), P0-2 (API), P0-1 (DB)
**Blocks**: None

---

### P2-3: Integrate Graph Analytics End-to-End

**Priority**: P2 (Features)
**Effort**: 3 days
**Owner**: Backend

**Problem**: Code exists but not integrated with live data.

**Definition of Done**:
- [ ] Ownership changes auto-sync to Neo4j
- [ ] API endpoint `GET /api/v1/graph/owner/{id}/properties` works
- [ ] PageRank runs monthly to find influential owners
- [ ] Relationship visualization available
- [ ] Artifact created: `/artifacts/graph/owner-network-demo.json` (owner's property network)

**Verification**:
```bash
curl http://localhost:8000/api/v1/graph/owner/12345/properties | jq .
# Should return properties owned by this owner
```

**Blocked By**: P1-8 (Neo4j), P0-2 (API)
**Blocks**: None

---

### P2-4: Integrate Document Upload End-to-End

**Priority**: P2 (Features)
**Effort**: 2 days
**Owner**: Backend

**Problem**: Code exists but not integrated with live storage.

**Definition of Done**:
- [ ] API endpoint `POST /api/v1/documents/upload` works
- [ ] Files stored in MinIO with correct tenant prefix
- [ ] Metadata stored in PostgreSQL
- [ ] Download endpoint works: `GET /api/v1/documents/{id}/download`
- [ ] Lease parsing triggered on PDF upload
- [ ] Artifact created: `/artifacts/documents/upload-demo.txt` (upload + download + parse flow)

**Verification**:
```bash
curl -X POST -F "file=@lease.pdf" http://localhost:8000/api/v1/documents/upload
# Returns document_id

curl http://localhost:8000/api/v1/documents/{document_id}/download --output downloaded.pdf
# File matches original
```

**Blocked By**: P1-9 (MinIO), P0-2 (API)
**Blocks**: None

---

### P2-5: Set Up MLflow Model Registry

**Priority**: P2 (ML Ops)
**Effort**: 2 days
**Owner**: ML Team

**Problem**: If ML models are trained, need versioning and deployment.

**Definition of Done**:
- [ ] MLflow server running
- [ ] Model registered: `comp_critic` v1
- [ ] Model deployed to production stage
- [ ] API loads model from registry (not local file)
- [ ] Model versioning works (can deploy v2)
- [ ] Artifact created: `/artifacts/ml/mlflow-screenshot.png` (model registry UI)

**Verification**:
```bash
mlflow models serve -m models:/comp_critic/Production -p 5001

curl http://localhost:5001/invocations -d '{"data": [...]}'
```

**Blocked By**: P2-1 (train models)
**Blocks**: None

---

### P2-6: Add Explainability (SHAP) to Valuations

**Priority**: P2 (ML Explainability)
**Effort**: 3 days
**Owner**: ML Team

**Problem**: Valuations are black boxes; users don't know why.

**Definition of Done**:
- [ ] SHAP explainer integrated for Comp-Critic
- [ ] API endpoint `GET /api/v1/ml/explain/{valuation_id}` returns SHAP values
- [ ] Response includes feature contributions (e.g., `{"sqft": +15000, "bedrooms": +5000, ...}`)
- [ ] Artifact created: `/artifacts/ml/shap-sample.json` (SHAP explanation for 1 property)
- [ ] Artifact created: `/artifacts/ml/shap-waterfall.png` (SHAP waterfall plot)

**Verification**:
```bash
curl http://localhost:8000/api/v1/ml/explain/valuation-123 | jq .
# Should show feature contributions
```

**Blocked By**: P2-1 (if ML-based) or mark N/A if rules-based
**Blocks**: None

---

### P2-7: Deploy Feast Feature Store

**Priority**: P2 (ML Infrastructure)
**Effort**: 4 days
**Owner**: ML Team

**Problem**: Feature store referenced but not deployed.

**Decision Required**: Needed only if ML models are trained.

**If needed**:
- [ ] Feast repo initialized
- [ ] Offline store (PostgreSQL) configured
- [ ] Online store (Redis) configured
- [ ] Features defined: `property_features`, `market_features`
- [ ] Features materialized
- [ ] API fetches features from online store
- [ ] p95 latency < 50ms
- [ ] Artifact created: `/artifacts/feast/feature-definitions.yaml`
- [ ] Artifact created: `/artifacts/feast/online-trace-DEMO123.json` (feature fetch)

**Verification**:
```bash
feast apply  # Deploy features
feast materialize-incremental $(date +%Y-%m-%d)  # Materialize to online store

# Fetch features
time feast feature-server get-online-features \
  --entity property_id=123 \
  --features property_features:sqft property_features:bedrooms
# Should be <50ms
```

**Blocked By**: P2-1 (ML decision)
**Blocks**: None

---

## Summary Statistics

**Total Work Items**: 34
- **P0 (Production Blockers)**: 15 items, ~23 days effort
- **P1 (Pre-Production)**: 12 items, ~25 days effort
- **P2 (Nice-to-Have)**: 7 items, ~27 days effort

**Critical Path**: P0 items must complete first (4-6 weeks)

**Artifact Count**:
- **Created**: 7 artifacts (baseline)
- **Required**: 28 more artifacts across P0/P1
- **Total**: 35 artifacts when complete

**Next Steps**:
1. Triage P0 items with team
2. Assign owners for each item
3. Create Jira/GitHub issues from this backlog
4. Track completion via artifacts (not just code commits)
5. Update [`docs/EVIDENCE_INDEX_E2E.md`](./EVIDENCE_INDEX_E2E.md) as artifacts created
