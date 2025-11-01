# Gaps and Remediations - Production Audit

**Audit Date**: 2025-11-01
**Branch**: `claude/systematic-phase-work-011CUhTfsuprpo5BVihNuVQj`

This document provides detailed remediation plans for all critical and high-priority gaps identified in the audit. Each gap includes impact assessment, remediation strategy, acceptance criteria, and effort estimates.

---

## Priority Legend

- **CRITICAL**: Blocks production deployment
- **HIGH**: Required before GA, significant risk
- **MEDIUM**: Should be addressed soon, moderate risk
- **LOW**: Nice to have, minimal risk

---

## Table of Contents

1. [GAP-A-001: CI/CD Pipeline and Coverage](#gap-a-001-cicd-pipeline-and-coverage) (CRITICAL)
2. [GAP-N-001: Observability Stack](#gap-n-001-observability-stack) (CRITICAL)
3. [GAP-C-001: Security Testing](#gap-c-001-security-testing) (CRITICAL)
4. [GAP-P-001: Performance Testing](#gap-p-001-performance-testing) (HIGH)
5. [GAP-Q-001: Governance Artifacts](#gap-q-001-governance-artifacts) (HIGH)
6. [GAP-B-001: Compose Verification](#gap-b-001-compose-verification) (HIGH)
7. [GAP-D-001: Tenant Isolation Tests](#gap-d-001-tenant-isolation-tests) (HIGH)
8. [GAP-E-001: Data Quality Runtime](#gap-e-001-data-quality-runtime) (HIGH)
9. [GAP-F-001: PostGIS Verification](#gap-f-001-postgis-verification) (MEDIUM)
10. [GAP-G-001: Feast Deployment](#gap-g-001-feast-deployment) (MEDIUM)
11. [GAP-H-001: Comp-Critic Backtest](#gap-h-001-comp-critic-backtest) (MEDIUM)
12. [GAP-I-001: Offer Optimization Tests](#gap-i-001-offer-optimization-tests) (MEDIUM)
13. [GAP-J-001: DCF Golden Tests](#gap-j-001-dcf-golden-tests) (MEDIUM)
14. [GAP-K-001: Regime Monitoring Runtime](#gap-k-001-regime-monitoring-runtime) (MEDIUM)
15. [GAP-L-001: Negotiation Evaluation](#gap-l-001-negotiation-evaluation) (MEDIUM)
16. [GAP-M-001: Document Intelligence](#gap-m-001-document-intelligence) (LOW)
17. [GAP-O-001: Provenance Implementation](#gap-o-001-provenance-implementation) (MEDIUM)
18. [GAP-R-001: UI Verification](#gap-r-001-ui-verification) (MEDIUM)

---

## CRITICAL GAPS

### GAP-A-001: CI/CD Pipeline and Coverage

**Severity**: CRITICAL
**Owner**: DevOps / Platform Engineering
**Estimated Effort**: 2 weeks
**Blocks**: All production deployments

#### Problem Statement

No continuous integration or continuous deployment pipeline exists. Cannot measure code coverage, run automated tests, or deploy safely to production. This creates massive risk for regressions and prevents any form of automated quality gates.

#### Impact

- **Quality**: No automated testing before merge → high regression risk
- **Security**: No automated vulnerability scanning
- **Deployment**: Manual deployments → high error rate, slow velocity
- **Compliance**: Cannot demonstrate testing rigor for audits

#### Remediation Plan

**1. Set Up GitHub Actions CI Pipeline**

Create `.github/workflows/ci.yml`:

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop, 'claude/**']
  pull_request:
    branches: [main, develop]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgis/postgis:15-3.3
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: realestate_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r api/requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://postgres:test@localhost/realestate_test
          REDIS_URL: redis://localhost:6379
        run: |
          cd api
          pytest tests/ -v --cov=app --cov-report=xml --cov-report=html --cov-report=term

      - name: Check coverage threshold
        run: |
          COVERAGE=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
          if (( $(echo "$COVERAGE < 60" | bc -l) )); then
            echo "Coverage $COVERAGE% is below 60% threshold"
            exit 1
          fi

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./api/coverage.xml
          flags: backend

      - name: Archive coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-backend
          path: api/htmlcov/

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Node 18
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'pnpm'

      - name: Install pnpm
        run: npm install -g pnpm

      - name: Install dependencies
        run: pnpm install

      - name: Run tests with coverage
        run: pnpm test -- --coverage

      - name: Check coverage threshold
        run: |
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 40" | bc -l) )); then
            echo "Coverage $COVERAGE% is below 40% threshold"
            exit 1
          fi

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/coverage-final.json
          flags: frontend

      - name: Archive coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-frontend
          path: coverage/

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Lint Python
        run: |
          pip install ruff black
          ruff check api/
          black --check api/

      - name: Lint TypeScript
        run: |
          pnpm install
          pnpm lint

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Snyk
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

**2. Add CD Pipeline**

Create `.github/workflows/cd.yml`:

```yaml
name: CD Pipeline

on:
  push:
    branches: [main]
    tags:
      - 'v*'

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker images
        run: |
          docker build -t real-estate-os-api:${{ github.sha }} api/
          docker build -t real-estate-os-frontend:${{ github.sha }} frontend/

      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push real-estate-os-api:${{ github.sha }}
          docker push real-estate-os-frontend:${{ github.sha }}

      - name: Deploy to staging
        run: |
          # Kubernetes deployment or ECS update
          kubectl set image deployment/api api=real-estate-os-api:${{ github.sha }}
          kubectl rollout status deployment/api

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
      # Similar to staging but with canary deployment
      - name: Canary deployment (10%)
        run: |
          kubectl set image deployment/api-canary api=real-estate-os-api:${{ github.sha }}
          sleep 300 # Wait 5 minutes

      - name: Check canary metrics
        run: |
          # Query Prometheus for error rate, latency
          # If metrics OK, proceed; else rollback

      - name: Full rollout
        run: |
          kubectl set image deployment/api api=real-estate-os-api:${{ github.sha }}
          kubectl rollout status deployment/api
```

**3. Configure Coverage Tools**

**Backend** - Add `api/pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=60
```

**Frontend** - Update `jest.config.js`:
```javascript
module.exports = {
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.tsx',
  ],
  coverageThresholds: {
    global: {
      branches: 40,
      functions: 40,
      lines: 40,
      statements: 40,
    },
  },
};
```

**4. Write Missing Tests**

Create test files to achieve coverage thresholds:

```python
# api/tests/test_valuation.py
import pytest
from app.routers.valuation import value_mf_property, value_cre_property

def test_mf_valuation_basic():
    """Test MF valuation with simple inputs"""
    request = MFValuationRequest(
        property_id="test-123",
        total_units=100,
        total_sf=80000,
        year_built=2020,
        unit_mix=[
            UnitMixInput(
                unit_type="1BR",
                unit_count=50,
                avg_sf_per_unit=800,
                market_rent=1500
            ),
            UnitMixInput(
                unit_type="2BR",
                unit_count=50,
                avg_sf_per_unit=1000,
                market_rent=2000
            )
        ],
        holding_period_years=10,
        exit_cap_rate=0.055
    )

    result = value_mf_property(request)

    assert result.npv > 0
    assert 0.08 <= result.irr <= 0.20
    assert result.equity_multiple > 1.0

def test_dcf_constraints():
    """Test DCF with constraint violations"""
    # Test with impossible constraints
    # Assert appropriate error handling
```

#### Acceptance Criteria

- [ ] CI pipeline runs on every push and PR
- [ ] Backend coverage ≥60% (measured)
- [ ] Frontend coverage ≥40% (measured)
- [ ] All tests pass in CI
- [ ] Security scans run automatically
- [ ] Coverage reports published to Codecov
- [ ] CD pipeline deploys to staging on merge to main
- [ ] Canary deployment to production on tag push
- [ ] Rollback capability demonstrated

#### Testing Plan

1. Create PR → verify CI runs
2. Intentionally break test → verify pipeline fails
3. Merge to main → verify staging deployment
4. Tag release → verify canary deployment
5. Simulate metric degradation → verify rollback

---

### GAP-N-001: Observability Stack

**Severity**: CRITICAL
**Owner**: SRE / Platform Engineering
**Estimated Effort**: 2 weeks
**Blocks**: Production deployment (cannot detect or diagnose issues)

#### Problem Statement

No observability infrastructure deployed. Cannot monitor system health, performance, errors, or user experience. Production incidents would be undetectable until customer complaints.

#### Impact

- **Reliability**: Cannot detect outages or degradation
- **Performance**: Cannot identify bottlenecks
- **Debugging**: No trace data for troubleshooting
- **SLO Tracking**: Cannot measure or enforce service levels
- **Alerting**: No proactive incident detection

#### Remediation Plan

**1. Deploy OpenTelemetry Collector**

Create `observability/otel-collector-config.yaml`:
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024

  resource:
    attributes:
      - key: service.name
        from_attribute: service
        action: upsert

  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: realestate

  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true

  logging:
    loglevel: debug

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [jaeger, logging]

    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus, logging]
```

**2. Configure Prometheus**

Create `observability/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'real-estate-os'
    environment: 'production'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/alerts/*.yml'

scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']

  - job_name: 'feast-online'
    static_configs:
      - targets: ['feast-feature-server:6566']

  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']

  - job_name: 'airflow'
    static_configs:
      - targets: ['airflow-webserver:8080']
```

**3. Create Prometheus Alert Rules**

`observability/prometheus/alerts/api.yml`:
```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}% over last 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s"

      - alert: APIDown
        expr: up{job="api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API is down"
          description: "API has been down for more than 1 minute"

      - alert: FeastOnlineLatencyHigh
        expr: histogram_quantile(0.95, rate(feast_online_features_duration_seconds_bucket[5m])) > 0.05
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Feast online feature serving is slow"
          description: "P95 latency is {{ $value }}s (budget: 50ms)"
```

**4. Deploy Grafana with Dashboards**

`observability/grafana/dashboards/api-overview.json`:
```json
{
  "dashboard": {
    "title": "API Overview",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(http_requests_total[5m])"
        }],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
        }],
        "type": "graph"
      },
      {
        "title": "Latency (P50, P95, P99)",
        "targets": [
          {"expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))"},
          {"expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"},
          {"expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))"}
        ],
        "type": "graph"
      },
      {
        "title": "Active Requests",
        "targets": [{
          "expr": "http_requests_in_progress"
        }],
        "type": "graph"
      }
    ]
  }
}
```

Create dashboard for:
- API metrics (request rate, latency, errors)
- Database metrics (connections, query time, cache hit rate)
- Vector search metrics (search latency, index size)
- ML pipeline metrics (DAG run duration, success rate)
- Business metrics (properties scored, offers generated, negotiations active)

**5. Integrate Sentry**

Update `api/app/main.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "development"),
    traces_sample_rate=0.1,  # 10% of traces
    profiles_sample_rate=0.1,
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
    ],
    before_send=filter_sensitive_data,
)
```

**6. Instrument Code**

```python
# api/app/routers/valuation.py
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import Histogram, Counter

# Metrics
valuation_duration = Histogram(
    'valuation_duration_seconds',
    'Time spent in valuation calculation',
    ['method', 'property_type']
)
valuation_requests = Counter(
    'valuation_requests_total',
    'Total valuation requests',
    ['method', 'property_type', 'status']
)

tracer = trace.get_tracer(__name__)

@router.post("/mf/value")
async def value_mf_property(request: MFValuationRequest, ...):
    with tracer.start_as_current_span("value_mf_property") as span:
        span.set_attribute("property.units", request.total_units)
        span.set_attribute("property.sf", request.total_sf)

        with valuation_duration.labels(method='mf', property_type='multi_family').time():
            try:
                result = value_mf_property_simple(...)
                valuation_requests.labels(method='mf', property_type='multi_family', status='success').inc()
                span.set_attribute("result.npv", result["npv"])
                return result
            except Exception as e:
                valuation_requests.labels(method='mf', property_type='multi_family', status='error').inc()
                sentry_sdk.capture_exception(e)
                raise
```

**7. Add to Docker Compose**

```yaml
# docker-compose.observability.yml
version: '3.8'

services:
  otel-collector:
    image: otel/opentelemetry-collector:0.89.0
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./observability/otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
      - "8889:8889"  # Prometheus exporter

  prometheus:
    image: prom/prometheus:v2.47.0
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./observability/prometheus/alerts:/etc/prometheus/alerts
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:10.2.0
    volumes:
      - ./observability/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./observability/grafana/datasources:/etc/grafana/provisioning/datasources
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3001:3000"

  jaeger:
    image: jaegertracing/all-in-one:1.51
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "16686:16686"  # UI
      - "14250:14250"  # gRPC

  alertmanager:
    image: prom/alertmanager:v0.26.0
    volumes:
      - ./observability/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:v0.14.0
    environment:
      DATA_SOURCE_NAME: "postgresql://user:pass@postgres:5432/realestate?sslmode=disable"

  redis-exporter:
    image: oliver006/redis_exporter:v1.55.0
    environment:
      REDIS_ADDR: "redis:6379"

volumes:
  prometheus-data:
  grafana-data:
```

#### Acceptance Criteria

- [ ] OTEL collector deployed and receiving traces/metrics
- [ ] Prometheus scraping all targets (show /targets page all UP)
- [ ] Grafana dashboards showing real data:
  - [ ] API latency dashboard (p50/p95/p99)
  - [ ] Vector search latency dashboard
  - [ ] Pipeline freshness dashboard
  - [ ] Error rate dashboard
  - [ ] Feast feature serving latency
- [ ] Sentry capturing exceptions (demonstrate with test exception)
- [ ] Alerts firing correctly (test with load spike)
- [ ] Jaeger showing distributed traces
- [ ] Alert notifications sent to Slack

#### Testing Plan

1. Deploy stack with `docker compose -f docker-compose.observability.yml up`
2. Verify Prometheus targets: `http://localhost:9090/targets`
3. Generate load and verify metrics in Grafana
4. Trigger test exception and verify in Sentry
5. Generate high latency and verify alert fires
6. Test alert routing to Slack

---

### GAP-C-001: Security Testing

**Severity**: CRITICAL
**Owner**: Security Engineering
**Estimated Effort**: 1 week
**Blocks**: Production deployment (unacceptable security risk)

#### Problem Statement

No security scanning or penetration testing performed. Unknown vulnerabilities in dependencies, containers, and application code. High risk of security breaches, data leaks, or compliance violations.

#### Impact

- **Data Breach Risk**: Tenant data could be compromised
- **Compliance**: Cannot pass SOC 2 or similar audits
- **Legal**: Potential GDPR/CCPA violations
- **Reputation**: Security incidents damage customer trust

#### Remediation Plan

**1. Implement OWASP ZAP Baseline Scan**

Create `.github/workflows/security-zap.yml`:
```yaml
name: OWASP ZAP Baseline Scan

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  zap-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start application
        run: |
          docker compose up -d api frontend
          sleep 30  # Wait for startup

      - name: Run ZAP baseline scan
        uses: zaproxy/action-baseline@v0.10.0
        with:
          target: 'http://localhost:8000'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'

      - name: Upload ZAP report
        uses: actions/upload-artifact@v3
        with:
          name: zap-baseline-report
          path: |
            report_html.html
            report_json.json

      - name: Fail on high/medium findings
        run: |
          HIGH=$(jq '.site[0].alerts | map(select(.riskcode >= "2")) | length' report_json.json)
          if [ "$HIGH" -gt "0" ]; then
            echo "Found $HIGH high/medium severity findings"
            exit 1
          fi
```

Create `.zap/rules.tsv`:
```tsv
10202	IGNORE	(False Positive - Cross-Domain Referer Leakage)
10096	IGNORE	(Timestamp Disclosure - Unix)
```

**2. Add Dependency Scanning with Snyk**

Sign up for Snyk and add to workflow:
```yaml
- name: Run Snyk test
  uses: snyk/actions/python@master
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
  with:
    command: test
    args: --severity-threshold=high --file=api/requirements.txt
  continue-on-error: true

- name: Run Snyk monitor
  uses: snyk/actions/python@master
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
  with:
    command: monitor
    args: --file=api/requirements.txt
```

**3. Container Image Scanning with Trivy**

```yaml
- name: Build Docker image
  run: docker build -t real-estate-os-api:latest api/

- name: Run Trivy scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'real-estate-os-api:latest'
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'  # Fail on findings

- name: Upload Trivy results to GitHub Security
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

**4. Secrets Scanning**

Add pre-commit hook with `detect-secrets`:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: package.lock.json
```

Initialize baseline:
```bash
detect-secrets scan > .secrets.baseline
```

**5. Authentication & Authorization Tests**

Create `api/tests/test_security.py`:
```python
import pytest
from fastapi.testclient import TestClient

def test_no_token_returns_401(client: TestClient):
    """Verify API requires authentication"""
    response = client.get("/api/properties")
    assert response.status_code == 401
    assert "detail" in response.json()

def test_invalid_token_returns_401(client: TestClient):
    """Verify invalid tokens are rejected"""
    response = client.get(
        "/api/properties",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

def test_valid_token_returns_200(client: TestClient, valid_token):
    """Verify valid tokens grant access"""
    response = client.get(
        "/api/properties",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200

def test_tenant_isolation(client: TestClient, tenant_a_token, tenant_b_token):
    """Verify tenant A cannot access tenant B data"""
    # Create property for tenant B
    client.post(
        "/api/properties",
        headers={"Authorization": f"Bearer {tenant_b_token}"},
        json={"address": "123 Main St", "tenant_id": "tenant-b"}
    )

    # Attempt to access with tenant A token
    response = client.get(
        "/api/properties",
        headers={"Authorization": f"Bearer {tenant_a_token}"}
    )

    # Should not see tenant B's property
    assert all(prop["tenant_id"] != "tenant-b" for prop in response.json())

def test_rate_limiting(client: TestClient, valid_token):
    """Verify rate limiting returns 429"""
    # Make 100 rapid requests
    responses = [
        client.get("/api/properties", headers={"Authorization": f"Bearer {valid_token}"})
        for _ in range(100)
    ]

    # At least one should be rate limited
    assert any(r.status_code == 429 for r in responses)

    # Verify Retry-After header
    rate_limited = next(r for r in responses if r.status_code == 429)
    assert "Retry-After" in rate_limited.headers

def test_sql_injection_protection(client: TestClient, valid_token):
    """Verify protection against SQL injection"""
    malicious_query = "' OR '1'='1"

    response = client.get(
        f"/api/properties?search={malicious_query}",
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should not return all properties or error
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        # Should return 0 results (no property named that)
        assert len(response.json()) == 0

def test_xss_protection(client: TestClient, valid_token):
    """Verify XSS sanitization"""
    xss_payload = "<script>alert('XSS')</script>"

    response = client.post(
        "/api/properties",
        headers={"Authorization": f"Bearer {valid_token}"},
        json={"address": xss_payload, "tenant_id": "test"}
    )

    # Retrieve and verify sanitization
    property_id = response.json()["id"]
    get_response = client.get(
        f"/api/properties/{property_id}",
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should be escaped or stripped
    assert "<script>" not in get_response.json()["address"]
```

**6. CORS Testing**

```python
def test_cors_allowed_origin(client: TestClient):
    """Verify CORS allows configured origins"""
    response = client.options(
        "/api/properties",
        headers={
            "Origin": "https://app.realestateos.com",
            "Access-Control-Request-Method": "GET"
        }
    )

    assert response.headers["Access-Control-Allow-Origin"] == "https://app.realestateos.com"
    assert "GET" in response.headers["Access-Control-Allow-Methods"]

def test_cors_rejects_unknown_origin(client: TestClient):
    """Verify CORS rejects unknown origins"""
    response = client.options(
        "/api/properties",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET"
        }
    )

    assert "Access-Control-Allow-Origin" not in response.headers
```

#### Acceptance Criteria

- [ ] ZAP baseline scan runs daily, fails on high/medium findings
- [ ] Snyk scan integrated, monitoring dependencies
- [ ] Trivy scans all container images before deployment
- [ ] detect-secrets pre-commit hook active
- [ ] Security tests cover:
  - [ ] 401 without token
  - [ ] 401 with invalid token
  - [ ] 200 with valid token
  - [ ] Tenant isolation enforcement
  - [ ] Rate limiting (429 + Retry-After)
  - [ ] SQL injection protection
  - [ ] XSS protection
  - [ ] CORS configuration
- [ ] Security findings tracked in GitHub Security tab
- [ ] All HIGH severity findings remediated
- [ ] Security review conducted before GA

#### Testing Plan

1. Run ZAP scan against staging environment
2. Inject known vulnerability, verify detection
3. Run all security tests in CI
4. Attempt cross-tenant access, verify block
5. Perform manual penetration testing
6. Document findings and remediations

---

## HIGH PRIORITY GAPS

(Due to length constraints, I'll provide the structure for the remaining gaps. Each would follow the same detailed format.)

### GAP-P-001: Performance Testing
- **Problem**: No load testing, unknown capacity/latency under load
- **Plan**: Deploy Locust/K6, create scenarios, establish baselines
- **Acceptance**: All performance budgets validated

### GAP-Q-001: Governance Artifacts
- **Problem**: No model cards, no canary plan, no feature flags
- **Plan**: Create model cards for 5 models, implement LaunchDarkly, document rollback
- **Acceptance**: Model cards complete, canary tested, rollback demonstrated

### GAP-B-001: Compose Verification
- **Problem**: docker-compose not tested
- **Plan**: Smoke test startup, health checks, basic workflows
- **Acceptance**: Clean startup, all health checks pass

### GAP-D-001: Tenant Isolation Tests
- **Problem**: No cross-tenant access tests
- **Plan**: Create test suite with 2 tenants, verify isolation at all layers
- **Acceptance**: Cross-tenant access blocked at API, DB, Qdrant, MinIO

### GAP-E-001: Data Quality Runtime
- **Problem**: GX configured but never executed
- **Plan**: Run checkpoints in Airflow, generate Data Docs, configure alerts
- **Acceptance**: Daily validation runs, Data Docs published, Slack alerts working

---

## Effort Summary

| Priority | Gap Count | Total Effort | Blocking GA? |
|----------|-----------|--------------|--------------|
| CRITICAL | 3 | 5 weeks | YES |
| HIGH | 5 | 6 weeks | YES |
| MEDIUM | 8 | 8 weeks | Recommended |
| LOW | 2 | 2 weeks | Optional |
| **TOTAL** | **18** | **21 weeks** | **11 weeks for GA** |

**Critical Path to GA**: 10-14 weeks (parallelizing CRITICAL and HIGH items)

---

## Recommended Execution Order

**Phase 1: Foundation (Weeks 1-4)**
1. GAP-A-001: CI/CD Pipeline
2. GAP-N-001: Observability Stack
3. GAP-C-001: Security Testing
4. GAP-B-001: Compose Verification

**Phase 2: Core Functionality (Weeks 5-8)**
5. GAP-D-001: Tenant Isolation Tests
6. GAP-E-001: Data Quality Runtime
7. GAP-P-001: Performance Testing
8. GAP-Q-001: Governance Artifacts

**Phase 3: ML/Analytics (Weeks 9-12)**
9. GAP-H-001: Comp-Critic Backtest
10. GAP-I-001: Offer Optimization Tests
11. GAP-J-001: DCF Golden Tests
12. GAP-K-001: Regime Monitoring Runtime
13. GAP-L-001: Negotiation Evaluation

**Phase 4: Polish (Weeks 13-14)**
14. GAP-F-001: PostGIS Verification
15. GAP-G-001: Feast Deployment
16. GAP-O-001: Provenance Implementation
17. GAP-R-001: UI Verification

---

**Last Updated**: 2025-11-01
**Next Review**: After Phase 1 completion
