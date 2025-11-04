# Real Estate OS - System Architecture

## Overview
Full-featured real estate CRM and outreach platform with mock-first architecture for demo-ready deployment without external credentials.

**Target Metrics:**
- 118 API endpoints across 17 routers
- 35 database models
- 5 mock providers (data, email, SMS, webhook, storage)
- 254 test functions across 47 test files
- 11-12 Docker services

## System Components

### 1. Core Services (Docker Compose Stack)

```
┌─────────────────────────────────────────────────────────────┐
│                        NGINX (Reverse Proxy)                 │
│                    Port 80 → routing layer                   │
└────────────┬────────────────────────────────────────┬────────┘
             │                                        │
    ┌────────▼─────────┐                    ┌────────▼─────────┐
    │   Frontend       │                    │   API Server     │
    │   (Next.js)      │                    │   (FastAPI)      │
    │   Port 3000      │                    │   Port 8000      │
    └──────────────────┘                    └────────┬─────────┘
                                                     │
              ┌──────────────────────────────────────┼───────────────────┐
              │                                      │                   │
    ┌─────────▼──────────┐            ┌─────────────▼────┐    ┌────────▼─────────┐
    │   PostgreSQL       │            │   Redis          │    │   RabbitMQ       │
    │   (Primary DB)     │            │   (Cache + RL)   │    │   (Task Queue)   │
    │   Port 5432        │            │   Port 6379      │    │   Port 5672      │
    └────────────────────┘            └──────────────────┘    └──────────┬───────┘
                                                                         │
                                            ┌────────────────────────────┤
                                            │                            │
                                   ┌────────▼─────────┐      ┌──────────▼────────┐
                                   │  Celery Worker   │      │  Celery Beat      │
                                   │  (Background)    │      │  (Scheduler)      │
                                   └──────────────────┘      └───────────────────┘
                                            │
                                   ┌────────▼─────────┐
                                   │   Flower         │
                                   │   (Monitor)      │
                                   │   Port 5555      │
                                   └──────────────────┘

    ┌────────────────────┐            ┌──────────────────┐    ┌────────────────────┐
    │   MinIO            │            │   Prometheus     │    │   Grafana          │
    │   (S3 Storage)     │            │   (Metrics)      │    │   (Dashboards)     │
    │   Port 9000        │            │   Port 9090      │    │   Port 3001        │
    └────────────────────┘            └──────────────────┘    └────────────────────┘
```

### 2. Database Models (35 models)

**Core Entities:**
1. `User` - System users with role-based access
2. `Organization` - Multi-tenant support
3. `Team` - User grouping
4. `Role` - RBAC roles
5. `Permission` - Granular permissions

**Property & Listings:**
6. `Property` - Real estate properties
7. `PropertyImage` - Property photos
8. `PropertyDocument` - Documents/contracts
9. `PropertyValuation` - Automated valuations
10. `PropertyMetrics` - Analytics data
11. `PropertyHistory` - Ownership/transaction history
12. `Listing` - Active listings
13. `ListingSnapshot` - Historical listing states

**CRM & Leads:**
14. `Lead` - Potential customers
15. `LeadSource` - Acquisition channels
16. `LeadScore` - ML-based scoring
17. `Contact` - Contact information
18. `LeadActivity` - Interaction timeline
19. `LeadNote` - Manual notes

**Campaigns & Outreach:**
20. `Campaign` - Marketing campaigns
21. `CampaignTarget` - Targeted leads
22. `EmailTemplate` - Email templates
23. `SMSTemplate` - SMS templates
24. `OutreachAttempt` - Communication log
25. `DeliverabilityEvent` - Bounce/complaint tracking
26. `UnsubscribeList` - DNC registry

**Transactions & Portfolio:**
27. `Deal` - Real estate transactions
28. `DealStage` - Pipeline stages
29. `Portfolio` - Investment portfolios
30. `PortfolioHolding` - Portfolio positions
31. `Transaction` - Financial transactions
32. `Reconciliation` - Portfolio reconciliation records

**System & Operations:**
33. `IdempotencyKey` - Request deduplication
34. `WebhookLog` - Webhook delivery tracking
35. `AuditLog` - System audit trail

### 3. API Routers (17 routers, 118 endpoints)

#### 3.1 Authentication & Users (`/api/v1/auth`, `/api/v1/users`)
- `POST /auth/register` - User registration
- `POST /auth/login` - Login with lockout protection
- `POST /auth/logout` - Session termination
- `POST /auth/refresh` - Token refresh
- `GET /auth/me` - Current user info
- `GET /users` - List users (paginated)
- `GET /users/{id}` - Get user details
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Soft delete user

#### 3.2 Properties (`/api/v1/properties`)
- `GET /properties` - List properties (filters, pagination)
- `POST /properties` - Create property
- `GET /properties/{id}` - Get property details
- `PUT /properties/{id}` - Update property
- `DELETE /properties/{id}` - Archive property
- `POST /properties/{id}/images` - Upload images
- `POST /properties/{id}/valuations` - Trigger valuation
- `GET /properties/{id}/history` - Property timeline
- `GET /properties/search` - Advanced search
- `POST /properties/bulk-import` - CSV import

#### 3.3 Leads & CRM (`/api/v1/leads`)
- `GET /leads` - List leads
- `POST /leads` - Create lead
- `GET /leads/{id}` - Lead details
- `PUT /leads/{id}` - Update lead
- `DELETE /leads/{id}` - Archive lead
- `POST /leads/{id}/score` - Calculate lead score
- `POST /leads/{id}/activities` - Log activity
- `GET /leads/{id}/timeline` - Activity timeline
- `POST /leads/{id}/notes` - Add note
- `POST /leads/import` - Bulk import

#### 3.4 Campaigns (`/api/v1/campaigns`)
- `GET /campaigns` - List campaigns
- `POST /campaigns` - Create campaign
- `GET /campaigns/{id}` - Campaign details
- `PUT /campaigns/{id}` - Update campaign
- `DELETE /campaigns/{id}` - Cancel campaign
- `POST /campaigns/{id}/launch` - Launch campaign
- `POST /campaigns/{id}/pause` - Pause campaign
- `GET /campaigns/{id}/metrics` - Analytics
- `POST /campaigns/{id}/targets` - Set targets
- `GET /campaigns/{id}/deliverability` - Delivery stats

#### 3.5 Templates (`/api/v1/templates`)
- `GET /templates/email` - List email templates
- `POST /templates/email` - Create email template
- `GET /templates/email/{id}` - Template details
- `PUT /templates/email/{id}` - Update template
- `DELETE /templates/email/{id}` - Delete template
- `GET /templates/sms` - List SMS templates
- `POST /templates/sms` - Create SMS template
- `PUT /templates/sms/{id}` - Update SMS template

#### 3.6 Outreach (`/api/v1/outreach`)
- `POST /outreach/email` - Send email (idempotent)
- `POST /outreach/sms` - Send SMS (idempotent)
- `GET /outreach/attempts` - List attempts
- `GET /outreach/attempts/{id}` - Attempt details
- `POST /outreach/webhooks` - Webhook receiver
- `GET /outreach/deliverability` - Delivery reports

#### 3.7 Compliance (`/api/v1/compliance`)
- `POST /compliance/unsubscribe` - Unsubscribe handler
- `GET /compliance/dnc-list` - DNC registry
- `POST /compliance/dnc-add` - Add to DNC
- `DELETE /compliance/dnc-remove` - Remove from DNC
- `GET /compliance/consent-log` - Consent audit trail

#### 3.8 Portfolio (`/api/v1/portfolio`)
- `GET /portfolio` - List portfolios
- `POST /portfolio` - Create portfolio
- `GET /portfolio/{id}` - Portfolio details
- `PUT /portfolio/{id}` - Update portfolio
- `POST /portfolio/{id}/holdings` - Add holding
- `GET /portfolio/{id}/valuation` - Calculate value
- `POST /portfolio/{id}/reconcile` - Run reconciliation (±0.5%)
- `GET /portfolio/{id}/performance` - Performance metrics

#### 3.9 Deals (`/api/v1/deals`)
- `GET /deals` - List deals
- `POST /deals` - Create deal
- `GET /deals/{id}` - Deal details
- `PUT /deals/{id}` - Update deal
- `PATCH /deals/{id}/stage` - Move pipeline stage
- `POST /deals/{id}/documents` - Upload documents
- `GET /deals/{id}/timeline` - Deal history

#### 3.10 Search & Filters (`/api/v1/search`)
- `POST /search/properties` - Advanced property search
- `POST /search/leads` - Lead search
- `POST /search/campaigns` - Campaign search
- `GET /search/suggestions` - Autocomplete

#### 3.11 Analytics (`/api/v1/analytics`)
- `GET /analytics/dashboard` - Dashboard metrics
- `GET /analytics/properties` - Property analytics
- `GET /analytics/leads` - Lead funnel
- `GET /analytics/campaigns` - Campaign performance
- `GET /analytics/portfolio` - Portfolio analytics

#### 3.12 Tasks (`/api/v1/tasks`)
- `GET /tasks` - List background tasks
- `POST /tasks` - Create task
- `GET /tasks/{id}` - Task status
- `DELETE /tasks/{id}` - Cancel task
- `POST /tasks/retry` - Retry failed task

#### 3.13 Webhooks (`/api/v1/webhooks`)
- `GET /webhooks` - List webhook subscriptions
- `POST /webhooks` - Create subscription
- `PUT /webhooks/{id}` - Update subscription
- `DELETE /webhooks/{id}` - Delete subscription
- `GET /webhooks/{id}/logs` - Delivery logs
- `POST /webhooks/{id}/test` - Test delivery

#### 3.14 Events (SSE) (`/api/v1/events`)
- `GET /events/stream` - SSE stream (authenticated)
- `GET /events/history` - Event history
- `POST /events/publish` - Publish event (internal)

#### 3.15 Storage (`/api/v1/storage`)
- `POST /storage/upload` - Upload file
- `GET /storage/{key}` - Download file
- `DELETE /storage/{key}` - Delete file
- `GET /storage/presigned-url` - Generate presigned URL

#### 3.16 Admin (`/api/v1/admin`)
- `GET /admin/users` - User management
- `POST /admin/users/{id}/reset-password` - Password reset
- `GET /admin/audit-log` - System audit log
- `GET /admin/system-health` - Health metrics
- `POST /admin/cache-clear` - Clear cache
- `GET /admin/dlq` - View dead letter queue
- `POST /admin/dlq/{id}/replay` - Replay DLQ message

#### 3.17 Health & Meta (`/api/v1`)
- `GET /healthz` - Health check
- `GET /readyz` - Readiness probe
- `GET /metrics` - Prometheus metrics
- `GET /openapi.json` - OpenAPI spec
- `GET /docs` - Swagger UI

### 4. Mock Provider System

**Provider Interface:**
```python
class BaseProvider(ABC):
    @abstractmethod
    async def initialize(self): ...

    @abstractmethod
    async def shutdown(self): ...
```

**Providers:**

#### 4.1 DataProvider (`mock_data_provider.py`)
- Property data generation
- Lead generation
- Market data simulation
- Deterministic seeding

#### 4.2 EmailProvider (`mock_email_provider.py`)
- Email "sending" (logged only)
- Bounce/complaint simulation
- Delivery receipt generation
- Template rendering

#### 4.3 SMSProvider (`mock_sms_provider.py`)
- SMS "sending" (logged only)
- Delivery status simulation
- Rate limiting simulation

#### 4.4 WebhookProvider (`mock_webhook_provider.py`)
- Webhook delivery simulation
- Retry logic
- HMAC signature generation
- Status callbacks

#### 4.5 StorageProvider (`mock_storage_provider.py`)
- In-memory file storage
- MinIO mock
- Presigned URL generation

**Factory Pattern:**
```python
# config.py
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

# factory.py
def get_email_provider():
    if MOCK_MODE:
        return MockEmailProvider()
    return SendGridProvider()
```

### 5. Security & Middleware

#### 5.1 Rate Limiting
- Redis-backed sliding window
- Per-user and per-IP limits
- 429 responses with `Retry-After` header
- Endpoint-specific limits

#### 5.2 Authentication
- JWT with RS256 signing
- Access + refresh token pair
- Login lockout after 5 failures
- Progressive backoff (2^n minutes)

#### 5.3 Security Headers
- CORS configuration
- CSP headers
- HSTS
- X-Frame-Options
- X-Content-Type-Options

#### 5.4 Row-Level Security (RLS)
- Organization-level isolation
- Team-based permissions
- SQLAlchemy filter injection

#### 5.5 Idempotency Keys
- Hash-based deduplication
- 24-hour retention
- Automatic key generation
- Response caching

### 6. Background Jobs (Celery)

**Queues:**
- `high_priority` - Critical tasks
- `default` - Standard tasks
- `low_priority` - Bulk operations
- `dlq` - Dead letter queue

**Tasks:**
- Property valuation
- Lead scoring
- Campaign execution
- Email/SMS sending
- Portfolio reconciliation
- Data imports
- Report generation

**DLQ System:**
- Max retries: 3
- Exponential backoff
- Manual replay endpoint
- Single side-effect guarantee

### 7. Frontend (Next.js)

**Pages:**
- `/login` - Authentication
- `/register` - User registration
- `/dashboard` - Overview metrics
- `/properties` - Property list & search
- `/properties/[id]` - Property detail drawer
- `/leads` - Lead pipeline
- `/campaigns` - Campaign management
- `/portfolio` - Portfolio view
- `/analytics` - Reports & charts

**Features:**
- Server-side rendering (SSR)
- JWT token management
- Optimistic updates
- Real-time SSE integration
- Responsive design

### 8. Operational Scripts

#### 8.1 `DOCKER_RUNTIME_CHECKLIST.sh`
- Brings up Docker stack
- Waits for health checks
- Runs migrations
- Seeds demo data
- Validates all services

#### 8.2 `seed_demo_data.py`
- Creates 50 properties
- Creates 4 users (admin, sales, agent, viewer)
- Creates 20 leads
- Creates 3 campaigns
- Creates sample templates

#### 8.3 `run_proofs.sh`
- Rate limit proof (429 response)
- Idempotency proof (identical responses)
- DLQ replay proof
- SSE latency proof
- Memo determinism proof
- Unsubscribe/DNC proof
- Security headers proof

### 9. Testing Strategy

**Test Distribution (254 tests):**
- Unit tests: 150 (models, services, utilities)
- Integration tests: 80 (API endpoints, database)
- E2E tests: 24 (user flows, critical paths)

**Coverage Targets:**
- Overall: >85%
- Critical paths: 100%
- Security features: 100%

**Test Files (47 files):**
```
tests/
├── unit/
│   ├── test_models.py (35 tests)
│   ├── test_auth.py (18 tests)
│   ├── test_providers.py (25 tests)
│   ├── test_security.py (20 tests)
│   └── ...
├── integration/
│   ├── test_api_properties.py (15 tests)
│   ├── test_api_leads.py (12 tests)
│   ├── test_api_campaigns.py (10 tests)
│   └── ...
└── e2e/
    ├── test_user_journey.py (8 tests)
    ├── test_campaign_flow.py (6 tests)
    └── ...
```

### 10. CI/CD Pipeline (GitHub Actions)

**Workflow Stages:**
1. Lint & format check
2. Type checking (mypy)
3. Unit tests
4. Integration tests
5. Build Docker images
6. E2E tests (docker-compose)
7. Security scan (bandit, safety)
8. Coverage report

### 11. Deployment Configuration

**Environment Variables:**
```bash
# Core
MODE=mock  # or "production"
MOCK_MODE=true
DEBUG=false

# Database
DB_DSN=postgresql://user:pass@postgres:5432/realestate

# Redis
REDIS_URL=redis://redis:6379/0

# RabbitMQ
CELERY_BROKER_URL=amqp://rabbitmq:5672

# Auth
JWT_SECRET_KEY=<generated>
JWT_ALGORITHM=RS256

# External (when MODE=production)
SENDGRID_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

### 12. Evidence Pack Structure

```
audit_artifacts/YYYYMMDD_HHMMSS/
├── STATIC_SNAPSHOT.txt          # LOC, files, models, endpoints
├── DOCKER_SERVICES.txt          # Service inventory
├── MIGRATION_HISTORY.txt        # Alembic history
├── SEED_LOG.txt                 # Seed execution output
├── HEALTHZ_RESPONSE.json        # Health check results
├── OPENAPI_SPEC.json            # API documentation
├── RATE_LIMIT_PROOF.txt         # 429 response with headers
├── IDEMPOTENCY_PROOF.txt        # Identical response hashes
├── DLQ_REPLAY_PROOF.txt         # Replay behavior
├── SSE_LATENCY_PROOF.txt        # Event timestamps
├── MEMO_DETERMINISM_PROOF.txt   # Hash consistency
├── DNC_BLOCK_PROOF.txt          # Unsubscribe enforcement
├── SECURITY_HEADERS_PROOF.txt   # Header dump
├── LOGIN_PROOF.json             # JWT response
├── PORTFOLIO_RECONCILIATION.txt # ±0.5% validation
├── FRONTEND_SCREENSHOTS/        # UI evidence
│   ├── login.png
│   ├── dashboard.png
│   ├── property_drawer.png
│   └── campaign_view.png
└── TEST_RESULTS.xml             # Pytest JUnit XML
```

## Implementation Phases

**Phase 1: Foundation (Days 1-2)**
- Database models
- Authentication system
- Mock provider framework
- Basic API routers

**Phase 2: Core Features (Days 3-4)**
- Property management
- Lead/CRM system
- Campaign system
- Templates

**Phase 3: Advanced Features (Days 5-6)**
- Celery + DLQ
- SSE
- Portfolio reconciliation
- Compliance/deliverability

**Phase 4: Security & Ops (Day 7)**
- Rate limiting
- Idempotency
- Security headers
- Operational scripts

**Phase 5: Frontend (Day 8)**
- Next.js setup
- Auth pages
- Core UI components

**Phase 6: Testing & CI (Day 9)**
- Test suite
- GitHub Actions
- Coverage

**Phase 7: Runtime Validation (Day 10)**
- Docker stack execution
- Proof orchestration
- Evidence pack generation
- Final audit

## Success Criteria

- ✅ 118 endpoints functional
- ✅ 35 models with migrations
- ✅ Mock mode works without credentials
- ✅ All 11 services healthy
- ✅ 50 properties + 4 users seeded
- ✅ Login works (JWT issued)
- ✅ All security proofs pass
- ✅ Frontend accessible
- ✅ 254 tests passing
- ✅ CI workflow green
- ✅ Evidence pack complete
