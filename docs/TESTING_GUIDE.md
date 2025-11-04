# Real Estate OS - Testing Guide

**Phase 3: Test Execution & Coverage**

This guide provides comprehensive instructions for running the Real Estate OS test suite, understanding test structure, and achieving the 70%+ coverage target.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Test Suite Structure](#test-suite-structure)
- [Running Tests](#running-tests)
- [Coverage Analysis](#coverage-analysis)
- [Writing Tests](#writing-tests)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)

---

## Overview

The Real Estate OS test suite consists of **three test passes**:

| Pass | Type | Services Required | Test Count | Purpose |
|------|------|-------------------|------------|---------|
| **A** | Backend | None (SQLite in-memory) | ~80 | Unit tests, business logic, models |
| **B** | Integration | Docker services (mock mode) | ~150 | API endpoints, SSE, webhooks, DLQ |
| **C** | E2E | Full stack + frontend | ~24 | End-to-end user workflows |

**Coverage Target**: 70%+ (backend + integration tests)

**Test Framework**: pytest with pytest-cov for coverage

---

## Prerequisites

### Required

1. **Python 3.9+** with virtual environment
2. **pytest and dependencies**:
   ```bash
   pip install pytest pytest-cov pytest-html pytest-xdist
   ```

### For Pass B & C (Integration/E2E)

3. **Docker Engine 20.10+** and **Docker Compose v2.x**
4. **Running Docker stack** (see [DOCKER_QUICK_START.md](./DOCKER_QUICK_START.md)):
   ```bash
   ./scripts/start_docker_stack.sh
   ```

5. **Validated stack health**:
   ```bash
   ./scripts/validate_docker_stack.sh
   ```

---

## Quick Start

### Run All Tests (3 Passes)

```bash
# Start Docker stack first (for Pass B & C)
./scripts/start_docker_stack.sh

# Run all tests with coverage
./scripts/run_tests.sh
```

**Output**: Test artifacts in `audit_artifacts/<timestamp>/tests/`

### Run Individual Pass

```bash
# Pass A: Backend only (no Docker required)
./scripts/run_tests.sh --pass A

# Pass B: Integration (requires Docker)
./scripts/run_tests.sh --pass B

# Pass C: E2E (requires full stack)
./scripts/run_tests.sh --pass C
```

### Run Specific Tests

```bash
# Run specific test file
pytest tests/backend/test_auth.py -v

# Run specific test class
pytest tests/integration/test_sse.py::TestSSEAuthentication -v

# Run specific test function
pytest tests/backend/test_auth.py::TestPublicEndpoints::test_healthz_no_auth_required -v

# Run tests matching pattern
pytest -k "auth" -v

# Run tests with specific marker
pytest -m "integration" -v
```

---

## Test Suite Structure

### Directory Layout

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── backend/                       # Pass A: Backend tests
│   ├── test_auth.py               # Authentication & authorization
│   ├── test_api.py                # API endpoint logic
│   ├── test_ml_models.py          # ML model inference
│   └── test_tenant_isolation.py  # Multi-tenancy
├── integration/                   # Pass B: Integration tests
│   ├── test_sse.py                # Server-sent events
│   ├── test_webhooks.py           # Webhook delivery
│   ├── test_idempotency.py        # Idempotency keys
│   ├── test_reconciliation.py     # Event reconciliation
│   ├── test_dlq_flow.py           # Dead letter queue
│   ├── test_auth_and_ratelimiting.py  # Rate limiting
│   └── test_deliverability_compliance.py  # Email compliance
├── e2e/                           # Pass C: E2E tests
│   ├── test_auth_flow.py          # User authentication flow
│   ├── test_property_lifecycle.py # Property CRUD workflow
│   ├── test_memo_workflow.py      # Memo generation workflow
│   └── test_pipeline.py           # Full pipeline (skip trace → memo)
└── data_quality/                  # Data quality tests
    └── test_gx_failures.py        # Great Expectations validation
```

### Test Markers

Tests are organized using pytest markers defined in `pytest.ini`:

```python
@pytest.mark.integration  # Integration test (requires services)
@pytest.mark.e2e          # E2E test (requires full stack)
@pytest.mark.slow         # Slow test (>5s)
@pytest.mark.requires_redis  # Requires Redis
@pytest.mark.requires_celery  # Requires Celery
```

**Usage**:

```bash
# Run only integration tests
pytest -m "integration" -v

# Skip integration tests
pytest -m "not integration" -v

# Run only tests that don't require services
pytest -m "not integration and not e2e" -v
```

---

## Running Tests

### Pass A: Backend Tests

**Prerequisites**: None (uses SQLite in-memory)

**What's Tested**:
- API business logic
- Authentication & authorization
- Model validation
- Tenant isolation
- ML model inference

**Command**:

```bash
./scripts/run_tests.sh --pass A
```

**Manual Run**:

```bash
pytest tests/backend/ -v \
  --junitxml=audit_artifacts/tests/backend/junit.xml \
  --html=audit_artifacts/tests/backend/report.html \
  --self-contained-html
```

**Output**:
- `audit_artifacts/<timestamp>/tests/backend/junit.xml` - JUnit XML report
- `audit_artifacts/<timestamp>/tests/backend/report.html` - HTML report
- `audit_artifacts/<timestamp>/tests/backend/output.log` - Test log

---

### Pass B: Integration Tests

**Prerequisites**:
- Docker stack running (`./scripts/start_docker_stack.sh`)
- Services healthy: postgres, redis, rabbitmq, api, celery

**What's Tested**:
- API endpoints (118 endpoints)
- Server-sent events (SSE)
- Webhook delivery
- Idempotency keys
- Event reconciliation
- Dead letter queue (DLQ)
- Rate limiting
- Email deliverability compliance

**Command**:

```bash
./scripts/run_tests.sh --pass B
```

**Manual Run**:

```bash
pytest tests/integration/ -v \
  --cov=api --cov=db \
  --cov-report=html:audit_artifacts/tests/coverage/html \
  --cov-report=xml:audit_artifacts/tests/coverage/coverage.xml \
  --cov-report=term-missing \
  --junitxml=audit_artifacts/tests/integration/junit.xml
```

**Output**:
- `audit_artifacts/<timestamp>/tests/integration/junit.xml` - JUnit XML
- `audit_artifacts/<timestamp>/tests/integration/report.html` - HTML report
- `audit_artifacts/<timestamp>/tests/coverage/coverage.xml` - Coverage XML
- `audit_artifacts/<timestamp>/tests/coverage/html/` - Coverage HTML

---

### Pass C: E2E Tests

**Prerequisites**:
- Full Docker stack running (15 services)
- Frontend accessible at http://localhost:3000
- API accessible at http://localhost:8000

**What's Tested**:
- User authentication flow
- Property CRUD workflow
- Memo generation workflow
- Full pipeline (skip trace → enrichment → memo)

**Command**:

```bash
./scripts/run_tests.sh --pass C
```

**Manual Run**:

```bash
pytest tests/e2e/ -v \
  --junitxml=audit_artifacts/tests/e2e/junit.xml \
  --html=audit_artifacts/tests/e2e/report.html
```

**Output**:
- `audit_artifacts/<timestamp>/tests/e2e/junit.xml` - JUnit XML
- `audit_artifacts/<timestamp>/tests/e2e/report.html` - HTML report

---

## Coverage Analysis

### Target

**70%+ coverage** (backend + integration tests)

Configured in `pytest.ini`:
```ini
[pytest]
addopts =
    --cov=api
    --cov=db
    --cov-report=html:htmlcov
    --cov-report=term-missing
    --cov-fail-under=70
```

### Generating Coverage Report

Coverage is automatically generated during **Pass B (Integration Tests)**:

```bash
./scripts/run_tests.sh --pass B
```

### Viewing Coverage

**HTML Report** (recommended):

```bash
# Open in browser
open audit_artifacts/<timestamp>/tests/coverage/html/index.html
```

**Terminal Report**:

```bash
# Coverage summary in terminal (generated during test run)
```

**XML Report** (for CI):

```bash
# Used by CI tools (Jenkins, GitLab CI, etc.)
cat audit_artifacts/<timestamp>/tests/coverage/coverage.xml
```

### Validating Coverage

Use the validation script to check coverage against threshold:

```bash
python scripts/validate_coverage.py \
  audit_artifacts/<timestamp>/tests/coverage/coverage.xml \
  --threshold 70 \
  --output audit_artifacts/<timestamp>/tests/coverage_report.json
```

**Output**:
- Coverage summary (line coverage, branch coverage)
- Validation status (PASSED/FAILED)
- Top 10 files below threshold
- Per-package coverage breakdown

**Exit Codes**:
- `0`: Coverage meets threshold
- `1`: Coverage below threshold
- `2`: Error parsing coverage file

---

## Writing Tests

### Test Structure

All tests follow the **Arrange-Act-Assert (AAA)** pattern:

```python
def test_example(client: TestClient, auth_headers: dict):
    """Test description"""

    # Arrange: Set up test data
    payload = {"key": "value"}

    # Act: Perform action
    response = client.post("/api/v1/endpoint", json=payload, headers=auth_headers)

    # Assert: Verify results
    assert response.status_code == 200
    assert response.json()["key"] == "value"
```

### Using Fixtures

Common fixtures are defined in `tests/conftest.py`:

```python
def test_with_fixtures(
    client: TestClient,        # FastAPI test client
    test_db: Session,          # SQLAlchemy session (SQLite in-memory)
    test_user: User,           # Test user (admin role)
    test_agent_user: User,     # Test agent user (agent role)
    auth_headers: dict,        # Auth headers for test_user
    agent_auth_headers: dict,  # Auth headers for agent user
    test_property: Property,   # Single test property
    test_properties: list[Property],  # 5 properties (different stages)
    mock_redis: MockRedis,     # Mock Redis client
    mock_celery: MockTask      # Mock Celery task
):
    """Test using fixtures"""
    # Use fixtures here
```

### Backend Test Example

```python
# tests/backend/test_example.py

import pytest
from fastapi.testclient import TestClient

def test_create_property(client: TestClient, auth_headers: dict, test_team):
    """Test creating a new property"""

    # Arrange
    property_data = {
        "address": "456 New St",
        "city": "New City",
        "state": "CA",
        "zip_code": "54321",
        "owner_name": "New Owner"
    }

    # Act
    response = client.post(
        "/api/v1/properties",
        json=property_data,
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["address"] == "456 New St"
    assert data["current_stage"] == "NEW"
```

### Integration Test Example

```python
# tests/integration/test_example.py

import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_sse_stream(client: TestClient, auth_headers: dict):
    """Test SSE stream connection"""

    # Get SSE token
    token_response = client.get("/api/v1/sse/token", headers=auth_headers)
    assert token_response.status_code == 200
    sse_token = token_response.json()["sse_token"]

    # Connect to SSE stream
    response = client.get(
        f"/api/v1/sse/stream?token={sse_token}",
        headers={"Accept": "text/event-stream"}
    )

    assert response.status_code == 200
```

### E2E Test Example

```python
# tests/e2e/test_example.py

import pytest
from fastapi.testclient import TestClient

@pytest.mark.e2e
def test_property_workflow(client: TestClient, auth_headers: dict):
    """Test complete property workflow"""

    # 1. Create property
    create_response = client.post(
        "/api/v1/properties",
        json={"address": "789 E2E St", "city": "E2E City", "state": "CA", "zip_code": "99999"},
        headers=auth_headers
    )
    assert create_response.status_code == 201
    property_id = create_response.json()["id"]

    # 2. Update stage
    update_response = client.patch(
        f"/api/v1/properties/{property_id}",
        json={"current_stage": "OUTREACH"},
        headers=auth_headers
    )
    assert update_response.status_code == 200

    # 3. Generate memo
    memo_response = client.post(
        f"/api/v1/properties/{property_id}/memos",
        json={"template_id": "default"},
        headers=auth_headers
    )
    assert memo_response.status_code == 201

    # 4. Verify memo created
    get_response = client.get(
        f"/api/v1/properties/{property_id}/memos",
        headers=auth_headers
    )
    assert get_response.status_code == 200
    assert len(get_response.json()) == 1
```

---

## Troubleshooting

### Backend Tests Failing

**Symptom**: Backend tests fail with database errors

**Solution**:
```bash
# Backend tests use SQLite in-memory - should not require Docker
# Check for missing dependencies
pip install -r requirements.txt
pip install pytest pytest-cov
```

### Integration Tests Failing

**Symptom**: `Connection refused` or `Service not found`

**Solution**:
```bash
# Check Docker services are running
docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps

# Restart services
./scripts/start_docker_stack.sh

# Validate health
./scripts/validate_docker_stack.sh
```

### E2E Tests Failing

**Symptom**: Frontend not accessible

**Solution**:
```bash
# Check frontend is running
curl http://localhost:3000

# Check logs
docker compose logs frontend

# Restart frontend
docker compose restart frontend
```

### Coverage Below 70%

**Symptom**: Coverage validation fails

**Solution**:
```bash
# 1. Identify low-coverage files
python scripts/validate_coverage.py \
  audit_artifacts/<timestamp>/tests/coverage/coverage.xml \
  --threshold 70

# 2. View detailed coverage report
open audit_artifacts/<timestamp>/tests/coverage/html/index.html

# 3. Add tests for uncovered code paths
# Focus on files shown in "Top 10 Files Below Threshold"

# 4. Re-run tests
./scripts/run_tests.sh --pass B
```

### Test Timeout

**Symptom**: Tests hang or timeout

**Solution**:
```bash
# Run with timeout
pytest tests/integration/ -v --timeout=30

# Run with fail-fast (stop on first failure)
./scripts/run_tests.sh --fail-fast
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/ci.yml

name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-html

      - name: Start Docker stack
        run: ./scripts/start_docker_stack.sh

      - name: Validate Docker stack
        run: ./scripts/validate_docker_stack.sh

      - name: Run tests
        run: ./scripts/run_tests.sh

      - name: Validate coverage
        run: |
          python scripts/validate_coverage.py \
            audit_artifacts/*/tests/coverage/coverage.xml \
            --threshold 70 \
            --output coverage_report.json

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: audit_artifacts/*/tests/coverage/coverage.xml
          fail_ci_if_error: true

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: audit_artifacts/
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml

test:
  stage: test
  image: python:3.9
  services:
    - docker:dind
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - ./scripts/start_docker_stack.sh
    - ./scripts/run_tests.sh
  coverage: '/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'
  artifacts:
    when: always
    paths:
      - audit_artifacts/
    reports:
      junit: audit_artifacts/*/tests/*/junit.xml
      coverage_report:
        coverage_format: cobertura
        path: audit_artifacts/*/tests/coverage/coverage.xml
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `./scripts/run_tests.sh` | Run all tests (3 passes) |
| `./scripts/run_tests.sh --pass A` | Run backend tests only |
| `./scripts/run_tests.sh --pass B` | Run integration tests only |
| `./scripts/run_tests.sh --pass C` | Run E2E tests only |
| `./scripts/run_tests.sh --no-coverage` | Skip coverage reporting |
| `./scripts/run_tests.sh --fail-fast` | Stop on first failure |
| `pytest tests/backend/ -v` | Run backend tests (manual) |
| `pytest tests/integration/ -v` | Run integration tests (manual) |
| `pytest -m "integration"` | Run tests with marker |
| `pytest -k "auth"` | Run tests matching pattern |
| `python scripts/validate_coverage.py <xml>` | Validate coverage threshold |

---

## Next Steps

After completing Phase 3 (Test Execution):

1. **Review Coverage Report**:
   ```bash
   open audit_artifacts/<timestamp>/tests/coverage/html/index.html
   ```

2. **Proceed to Phase 4** - Runtime Proofs:
   ```bash
   ./scripts/generate_proofs.sh
   ```

3. **Generate Evidence Pack** (all test artifacts + proofs):
   ```bash
   zip -r evidence_pack.zip audit_artifacts/
   ```

---

## Resources

- **pytest Documentation**: https://docs.pytest.org/
- **pytest-cov Documentation**: https://pytest-cov.readthedocs.io/
- **Docker Quick Start**: [DOCKER_QUICK_START.md](./DOCKER_QUICK_START.md)
- **Work Journal**: [WORK_JOURNAL.md](./WORK_JOURNAL.md)
- **Progress Report**: [PROGRESS_REPORT.md](./PROGRESS_REPORT.md)

---

**Last Updated**: 2025-11-04
**Phase**: 3 - Test Execution & Coverage
**Status**: Ready for Execution
