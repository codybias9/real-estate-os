# 🎯 Mock Mode Implementation Guide

**Status:** Foundation Complete (Step 1-3 of 12)
**Goal:** Self-contained, credential-free "green" platform in dev/staging
**Approach:** Zero external dependencies via local mocks and emulators

---

## ✅ COMPLETED (Steps 1-3)

### 1. Mock Mode Foundation ✅

**Created:**
- ✅ `api/config.py` - Comprehensive configuration with APP_MODE flags
- ✅ `api/providers/__init__.py` - Provider registry with dependency injection
- ✅ `api/providers/email.py` - MockEmailProvider (MailHog) + SendGridProvider
- ✅ `api/providers/storage.py` - MinIOProvider + S3Provider
- ✅ Provider status endpoint: `GET /api/v1/status/providers`

**Feature Flags:**
```python
APP_MODE=mock  # Default for development
FEATURE_EXTERNAL_SENDS=false
FEATURE_USE_LLM=false
FEATURE_RATE_LIMIT=true
FEATURE_WEBHOOK_SIGNATURES=true
```

**Verify:**
```bash
curl http://localhost:8000/api/v1/status/providers
```

Expected response:
```json
{
  "app_mode": "mock",
  "email": "mailhog-smtp",
  "sms": "mock-twilio",
  "storage": "minio-local",
  "pdf": "gotenberg-local",
  "llm": "deterministic-templates",
  "features": {
    "external_sends": false,
    "use_llm": false,
    "rate_limit": true,
    "webhook_signatures": true,
    "cache_responses": true
  }
}
```

### 2. Local Infrastructure (Docker Compose) ✅

**Created:**
- ✅ `docker-compose.yml` - Full stack with 6 core services

**Services:**
1. **PostgreSQL** (5432) - Database with health checks
2. **Redis** (6379) - Cache, sessions, rate limiting
3. **RabbitMQ** (5672/15672) - Message queue with DLQ support
4. **MinIO** (9000/9001) - S3-compatible object storage
5. **Gotenberg** (3000) - PDF generation service
6. **MailHog** (1025 SMTP / 8025 UI) - Email capture

**Start Infrastructure:**
```bash
docker-compose up -d postgres redis rabbitmq minio gotenberg mailhog
```

**Verify Health:**
```bash
docker-compose ps
curl http://localhost:8025  # MailHog UI
curl http://localhost:9001  # MinIO Console (minioadmin/minioadmin)
```

### 3. Provider Integration ✅

**Dependencies Added:**
- `minio` - MinIO Python SDK for S3-compatible storage
- Email via Python `smtplib` (built-in, no extra dependency)

**Install:**
```bash
poetry add minio
poetry install
```

---

## 📋 REMAINING WORK (Steps 4-12)

### 4. Complete Mock Providers (Est: 2-3 hours)

**TODO:**
- [ ] Create `api/providers/sms.py` - MockSmsProvider + TwilioProvider
- [ ] Create `api/providers/pdf.py` - GotenbergProvider + WeasyPrintProvider
- [ ] Create `api/providers/llm.py` - DeterministicTemplateProvider + OpenAIProvider
- [ ] Create Mock Twilio service (`services/mock-twilio/`)
- [ ] Integrate providers into existing endpoints

**Files to Create:**
```
api/providers/sms.py
api/providers/pdf.py
api/providers/llm.py
services/mock-twilio/
  ├── Dockerfile
  ├── main.py (FastAPI)
  └── requirements.txt
```

**Mock Twilio Service:**
```python
# services/mock-twilio/main.py
from fastapi import FastAPI, Header
import json
from pathlib import Path

app = FastAPI()

@app.post("/Messages.json")
def send_message(To: str, From: str, Body: str):
    # Store message to volume
    data_dir = Path("/data")
    data_dir.mkdir(exist_ok=True)

    message_file = data_dir / f"sms_{timestamp}.json"
    with open(message_file, 'w') as f:
        json.dump({"to": To, "from": From, "body": Body}, f)

    return {"sid": f"SM{uuid.uuid4().hex}", "status": "queued"}

@app.get("/health")
def health():
    return {"status": "ok"}
```

### 5. Database Seeding (Est: 1 hour)

**TODO:**
- [ ] Update `scripts/seed_data.py` to create 50 properties
- [ ] Add stage-aware templates
- [ ] Add NBA rules and DNC samples
- [ ] Run migrations automatically on startup

**Command:**
```bash
# In api/main.py startup event
@app.on_event("startup")
async def startup():
    # Run migrations
    from alembic import command
    from alembic.config import Config
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    # Run seeds
    from scripts.seed_data import seed_database
    seed_database()
```

### 6. Rate Limiting & Caching (Est: 2 hours)

**TODO:**
- [ ] Create `api/rate_limiter.py` - Redis-backed rate limiting
- [ ] Add rate limit decorators to endpoints
- [ ] Implement ETag generation and If-None-Match handling
- [ ] Add cache invalidation on writes

**Implementation:**
```python
# api/rate_limiter.py
from fastapi import HTTPException, Request
from functools import wraps
import redis

def rate_limit(key_prefix: str, limit: str):
    """
    Rate limit decorator
    limit format: "10/minute" or "100/hour"
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request
            request = kwargs.get('request') or args[0]

            # Check rate limit in Redis
            # If exceeded, raise HTTPException(429, headers={"Retry-After": "60"})

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@app.post("/auth/login")
@rate_limit("auth:login", "10/minute")
async def login(request: Request, ...):
    pass
```

### 7. SSE Resilience (Est: 2 hours)

**TODO:**
- [ ] Update SSE to use signed query tokens (no headers needed)
- [ ] Add server-side heartbeat (ping every 20s)
- [ ] Add client reconnect logic with exponential backoff
- [ ] Update Nginx/proxy timeouts

**Client Code:**
```javascript
// frontend/lib/sse.ts
let eventSource: EventSource | null = null;
let reconnectAttempts = 0;

function connectSSE() {
  const token = getSSEToken();  // From /sse-events/token
  eventSource = new EventSource(`/api/v1/sse-events/stream?token=${token}`);

  eventSource.onopen = () => {
    reconnectAttempts = 0;
  };

  eventSource.onerror = () => {
    eventSource?.close();
    const backoff = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
    setTimeout(connectSSE, backoff);
    reconnectAttempts++;
  };

  eventSource.addEventListener('ping', () => {
    // Heartbeat received
  });
}
```

### 8. Webhook Signatures (Est: 2 hours)

**TODO:**
- [ ] Create `api/webhook_auth.py` - HMAC signature validation
- [ ] Add signature validation to webhook endpoints
- [ ] Implement timestamp skew checks (±5 minutes)
- [ ] Generate signatures in mock services

**Implementation:**
```python
# api/webhook_auth.py
import hmac
import hashlib
from fastapi import HTTPException, Header
from datetime import datetime, timedelta

def validate_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    timestamp: str = None
):
    """Validate webhook HMAC signature"""

    # Check timestamp skew
    if timestamp:
        ts = datetime.fromisoformat(timestamp)
        if abs((datetime.utcnow() - ts).total_seconds()) > 300:
            raise HTTPException(401, "Timestamp too old/new")

    # Compute expected signature
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(403, "Invalid signature")

    return True
```

### 9. E2E Tests (Est: 4-6 hours)

**TODO:**
- [ ] Set up Playwright test framework
- [ ] Create test fixtures and helpers
- [ ] Write 8 comprehensive E2E test suites
- [ ] Create API cURL test scripts
- [ ] Set up artifact collection

**Test Structure:**
```
tests/
├── e2e/
│   ├── conftest.py
│   ├── test_01_login_pipeline.py
│   ├── test_02_property_drawer.py
│   ├── test_03_memo_generation.py
│   ├── test_04_email_tracking.py
│   ├── test_05_sms_flow.py
│   ├── test_06_portfolio_export.py
│   ├── test_07_sse_realtime.py
│   └── test_08_api_features.py
└── scripts/
    ├── test_etag.sh
    ├── test_rate_limit.sh
    ├── test_idempotency.sh
    └── test_dlq.sh
```

**Sample Test:**
```python
# tests/e2e/test_03_memo_generation.py
async def test_memo_deterministic_hash(page, api_client):
    """Generate memo twice with same inputs, verify identical hash"""

    # Generate memo 1
    response1 = await api_client.post(
        "/jobs/memo/generate",
        json={"property_id": 30},
        headers={"Idempotency-Key": "test-memo-1"}
    )
    job_id_1 = response1.json()["job_id"]

    # Wait for completion
    memo_url_1 = await wait_for_job(job_id_1)
    pdf_1 = await download_file(memo_url_1)
    hash_1 = hashlib.sha256(pdf_1).hexdigest()

    # Generate memo 2 with same inputs
    response2 = await api_client.post(
        "/jobs/memo/generate",
        json={"property_id": 30},
        headers={"Idempotency-Key": "test-memo-2"}
    )
    job_id_2 = response2.json()["job_id"]

    memo_url_2 = await wait_for_job(job_id_2)
    pdf_2 = await download_file(memo_url_2)
    hash_2 = hashlib.sha256(pdf_2).hexdigest()

    # Verify deterministic
    assert hash_1 == hash_2, "PDFs should be deterministic"

    # Save to artifacts
    Path("audit_artifacts/memo_hashes.txt").write_text(
        f"{hash_1}\n{hash_2}\n"
    )
```

### 10. CI Pipeline (Est: 2 hours)

**TODO:**
- [ ] Create `.github/workflows/ci.yml`
- [ ] Configure Docker Compose in CI
- [ ] Run migrations and seeds
- [ ] Execute all tests
- [ ] Upload artifacts

**CI Configuration:**
```yaml
# .github/workflows/ci.yml
name: CI - Mock Mode

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Start infrastructure
        run: |
          docker-compose up -d
          sleep 30  # Wait for services

      - name: Run migrations
        run: |
          docker-compose exec -T api alembic upgrade head

      - name: Run seeds
        run: |
          docker-compose exec -T api python scripts/seed_data.py

      - name: Run API tests
        run: |
          docker-compose exec -T api pytest tests/

      - name: Run E2E tests
        run: |
          docker-compose exec -T api pytest tests/e2e/

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: audit-artifacts
          path: audit_artifacts/
```

### 11. Security Headers (Est: 1 hour)

**TODO:**
- [ ] Create `api/security_middleware.py`
- [ ] Add security headers in production mode
- [ ] Configure CORS properly
- [ ] Add Retry-After on 429 responses

**Implementation:**
```python
# api/security_middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if config.is_production_mode():
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
            response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response
```

### 12. Documentation & Evidence (Est: 2 hours)

**TODO:**
- [ ] Create `docs/ACCEPTANCE_MOCK_MODE.md`
- [ ] Generate evidence pack with screenshots
- [ ] Create hash reports
- [ ] Document 304/429 samples
- [ ] DLQ drill logs

**Structure:**
```
docs/ACCEPTANCE_MOCK_MODE.md
audit_artifacts/YYYYMMDD/
├── screenshots/
│   ├── pipeline_dual_tab.png
│   ├── property_drawer_reasons.png
│   ├── mailhog_email.png
│   └── memo_pdf_viewer.png
├── hashes/
│   ├── memo_deterministic.txt
│   └── pdf_checksums.sha256
├── api_tests/
│   ├── etag_304_sample.txt
│   ├── rate_limit_429_sample.txt
│   └── idempotency_test.json
├── emails/
│   └── mailhog_captures/
├── sms/
│   └── mock_twilio_messages/
└── dlq/
    └── drill_log.txt
```

---

## 🚀 QUICK START COMMANDS

### 1. Start Infrastructure
```bash
cd /home/user/real-estate-os

# Start all services
docker-compose up -d

# Wait for health checks
sleep 30

# Verify all healthy
docker-compose ps
```

### 2. Verify Mock Mode
```bash
# Check provider status
curl http://localhost:8000/api/v1/status/providers | jq

# Should show:
# {
#   "app_mode": "mock",
#   "email": "mailhog-smtp",
#   "sms": "mock-twilio",
#   ...
# }
```

### 3. Test Email Flow
```bash
# Send test email via API
curl -X POST http://localhost:8000/api/v1/communications/email-thread \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 30,
    "subject": "Test Email",
    "to_address": "owner@example.com",
    "body": "This is a test"
  }'

# Check MailHog UI
open http://localhost:8025
```

### 4. Test Storage
```bash
# MinIO Console
open http://localhost:9001
# Login: minioadmin / minioadmin

# Upload test file via API
curl -X POST http://localhost:8000/api/v1/jobs/memo/generate \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"property_id": 30}'

# Check MinIO bucket 'memos'
```

### 5. Run Tests
```bash
# API unit tests
docker-compose exec api pytest tests/

# E2E tests (when implemented)
docker-compose exec api pytest tests/e2e/ -v

# Generate evidence pack
docker-compose exec api python scripts/generate_evidence.py
```

---

## 📊 COMPLETION CHECKLIST

| Step | Component | Status | Time Est | Files Created |
|------|-----------|--------|----------|---------------|
| 1 | Config & Providers | ✅ DONE | 1h | 4 files |
| 2 | Docker Compose | ✅ DONE | 30m | 1 file |
| 3 | Provider Integration | ✅ DONE | 30m | Updates |
| 4 | Mock Services | ⏳ TODO | 2-3h | 3 providers + Mock Twilio |
| 5 | Database Seeding | ⏳ TODO | 1h | Seed updates |
| 6 | Rate Limit & Cache | ⏳ TODO | 2h | 2 modules |
| 7 | SSE Resilience | ⏳ TODO | 2h | API + Frontend |
| 8 | Webhook Signatures | ⏳ TODO | 2h | 1 module |
| 9 | E2E Tests | ⏳ TODO | 4-6h | 8 test files |
| 10 | CI Pipeline | ⏳ TODO | 2h | 1 workflow |
| 11 | Security Headers | ⏳ TODO | 1h | 1 middleware |
| 12 | Documentation | ⏳ TODO | 2h | Evidence pack |

**TOTAL:** 3 hours completed, 18-25 hours remaining

---

## 🎯 EXIT CRITERIA (Definition of "GREEN")

### Must Pass:
- [ ] `docker-compose up -d` shows all services healthy
- [ ] `GET /api/v1/status/providers` returns all mock providers
- [ ] `pytest tests/` all green
- [ ] `pytest tests/e2e/` all green
- [ ] Memo generation produces deterministic hash
- [ ] MailHog captures sent emails
- [ ] Mock Twilio captures SMS
- [ ] SSE updates between sessions ≤2s
- [ ] ETag returns 304 on cache hit
- [ ] Rate limit returns 429 with Retry-After
- [ ] Webhook signature validation rejects unsigned/expired
- [ ] Portfolio CSV export ±0.5% accuracy
- [ ] No external network calls during CI (fail if any detected)

### Artifacts Generated:
- [ ] `audit_artifacts/YYYYMMDD/` with all evidence
- [ ] Screenshots of all major flows
- [ ] Hash report for determinism
- [ ] API test samples (304, 429, idempotency)
- [ ] DLQ drill logs

---

## 💡 NEXT STEPS

1. **Continue Implementation (18-25 hours)**
   - Follow steps 4-12 in order
   - Test each component before moving forward
   - Generate artifacts as you go

2. **Integration Testing**
   - Run complete E2E test suite
   - Verify deterministic outputs
   - Check all mock services working

3. **Documentation**
   - Create ACCEPTANCE_MOCK_MODE.md
   - Generate evidence pack
   - Document any deviations

4. **Production Readiness**
   - When ready for production, flip `APP_MODE=production`
   - Set real provider credentials
   - Re-run same E2E tests with real services
   - Tests should pass identically (only providers change)

---

## 📝 NOTES

- **Provider Pattern:** Real provider code stays intact, just behind feature flags
- **Additive Work:** All changes are additive - existing code untouched
- **Test Equivalence:** E2E tests identical for mock and production modes
- **Determinism:** Fixed seeds + templates ensure reproducible results
- **No Secrets:** CI runs completely credential-free

**Foundation Complete. Ready to build remaining components systematically.**

---

**Created:** 2025-11-04
**Status:** Steps 1-3 Complete (25% done)
**Next:** Step 4 - Complete Mock Providers
