# PR2: API Core & Health - Evidence Pack

**PR**: `feat/api-core`
**Date**: 2025-11-02
**Branch**: `claude/realestate-audit-canvas-011CUjnrkmyeMSTozDmpy6xx`

## Summary

Implemented FastAPI v1 namespace with health check endpoints and Prometheus metrics.

## Endpoints Implemented

### 1. GET /v1/healthz
- **Purpose**: Process health check (no external dependencies)
- **Response**: `{"status": "ok"}`
- **Status Code**: 200
- **OpenAPI Tags**: Health

### 2. GET /v1/ping
- **Purpose**: Database connectivity check
- **Behavior**: Creates ping table if needed, inserts record, returns count
- **Response**: `{"ping_count": <int>}`
- **Status Codes**:
  - 200: Success
  - 500: DB_DSN not set or connection failed
- **OpenAPI Tags**: Health

### 3. GET /metrics
- **Purpose**: Prometheus metrics endpoint
- **Content-Type**: `text/plain; version=0.0.4; charset=utf-8`
- **Metrics Exported**:
  - Python runtime metrics (process_*, python_info)
  - HTTP request metrics (http_requests_total, http_request_duration_seconds)
  - Active requests gauge (active_requests)
  - Application metrics:
    - `properties_discovered_total{tenant_id}`
    - `properties_scored_total{tenant_id}`
    - `enrichment_plugin_calls_total{plugin_name,priority,status}`
    - `policy_decisions_total{decision_type,resource_type,result}`
    - `external_api_calls_total{provider,status}`
    - `external_api_cost_cents{provider}`

### 4. GET /
- **Purpose**: Root redirect to API documentation
- **Response**: 307 Redirect to `/docs`

### 5. GET /docs
- **Purpose**: Swagger UI for OpenAPI documentation
- **Status Code**: 200

### 6. GET /redoc
- **Purpose**: ReDoc UI for OpenAPI documentation
- **Status Code**: 200

## OpenAPI Documentation

- **Title**: Real Estate OS API
- **Version**: 0.1.0
- **Description**: Comprehensive API description with architecture overview
- **Tags**:
  - Health (implemented)
  - Discovery (placeholder)
  - Enrichment (placeholder)
  - Scoring (placeholder)
  - Outreach (placeholder)

## Test Coverage

```
Name                    Stmts   Miss  Cover
-----------------------------------------
api/main.py                12      0   100%
api/metrics.py             16      0   100%
api/v1/__init__.py          5      0   100%
api/v1/health.py           29      0   100%
-----------------------------------------
TOTAL                      62      0   100%
```

**Test Count**: 20 tests
**Test Duration**: 2.69s (< 5s requirement ✓)
**Coverage**: 100%

## Test Breakdown

### Health Endpoints (7 tests)
- ✓ Root redirects to /docs
- ✓ /v1/healthz returns 200 with status ok
- ✓ /v1/healthz matches response schema
- ✓ /v1/ping returns 500 without DB_DSN
- ✓ /v1/ping returns 200 with mocked database
- ✓ /v1/ping creates table and inserts records
- ✓ /v1/ping returns 500 on connection failure

### Metrics Endpoint (4 tests)
- ✓ /metrics endpoint exists (200)
- ✓ /metrics returns Prometheus content type
- ✓ /metrics contains Python runtime info
- ✓ /metrics returns valid Prometheus format

### OpenAPI Documentation (6 tests)
- ✓ OpenAPI schema accessible at /openapi.json
- ✓ API metadata (title, version, description)
- ✓ Health tag in OpenAPI tags
- ✓ v1 endpoints in OpenAPI paths
- ✓ /v1/healthz endpoint documentation
- ✓ /v1/ping endpoint documentation

### Integration (3 tests)
- ✓ /docs page accessible (Swagger UI)
- ✓ /redoc page accessible (ReDoc UI)
- ✓ CORS headers not present by default

## Dependencies Added

```toml
[tool.poetry.dependencies]
sqlalchemy = "^2.0.0"
prometheus-client = "^0.20.0"

[tool.poetry.group.dev.dependencies]
httpx = "^0.27.0"  # Required by FastAPI TestClient
```

## Files Created/Modified

**Created**:
- `api/v1/__init__.py` - v1 router
- `api/v1/health.py` - Health endpoints
- `api/metrics.py` - Prometheus metrics
- `api/tests/__init__.py` - Test package
- `api/tests/conftest.py` - Test configuration
- `api/tests/test_api.py` - API tests (20 tests)

**Modified**:
- `api/main.py` - Updated to use v1 router, add metrics, OpenAPI config
- `pyproject.toml` - Added dependencies
- `pytest.ini` - Added api/tests to testpaths, api to coverage sources

## Architectural Decisions

1. **v1 Namespace**: All API endpoints under `/v1/` prefix for versioning
2. **Tag-Based Organization**: Endpoints tagged by domain (Health, Discovery, etc.)
3. **Pydantic V2**: Using modern `ConfigDict` instead of deprecated `class Config`
4. **Mocked Database Tests**: Using unittest.mock for database tests to avoid SQLite/PostgreSQL differences
5. **Comprehensive Metrics**: Pre-defined application-specific metrics for future use
6. **Idempotent Ping Table**: CREATE TABLE IF NOT EXISTS for safe repeated calls

## Contracts Touched

- **None** - This is pure API infrastructure, no contract messages yet

## Configuration

Environment variables used:
- `DB_DSN`: PostgreSQL connection string (required for /v1/ping)

## Evidence Files

- Test results: `/tmp/pr2_test_results.txt`
- Coverage HTML: `htmlcov/`
- Coverage JSON: `coverage.json`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Ping table grows unbounded | Future: Add retention policy or use separate health DB |
| Metrics memory usage with high cardinality | Limited label values in metric definitions |
| No authentication on health endpoints | Intended for load balancers; auth comes in PR12 |
| No rate limiting | Future: Add rate limiting middleware |

## Follow-Ups

1. Add database migrations (PR3)
2. Add authentication/authorization (PR12)
3. Add middleware for request logging and metrics tracking
4. Add CORS configuration when frontend is ready (PR11)
5. Add rate limiting for production deployment
6. Add health check for other dependencies (RabbitMQ, Redis, MinIO, Qdrant)

## Acceptance Criteria

- [x] GET /v1/healthz returns 200
- [x] GET /v1/ping returns 200 (with valid DB_DSN)
- [x] GET /metrics endpoint present
- [x] OpenAPI documentation accessible at /docs
- [x] All endpoints properly tagged
- [x] 20 tests passing
- [x] 100% code coverage
- [x] Test duration < 5s (2.69s)
- [x] No breaking changes to existing code
