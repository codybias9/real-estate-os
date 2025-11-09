# Real Estate OS - System Architecture

## Overview

Real Estate OS is an event-driven, policy-first operating system for real estate investment workflows. The system orchestrates property discovery, enrichment, scoring, memo generation, outreach, and collaboration through a microservices architecture.

## Table of Contents

1. [Architecture Principles](#architecture-principles)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Event-Driven Architecture](#event-driven-architecture)
5. [Security Model](#security-model)
6. [Multi-Tenancy](#multi-tenancy)
7. [Performance & Caching](#performance--caching)
8. [External Integrations](#external-integrations)

---

## Architecture Principles

### 1. Event-Driven Microservices
- **Single-Producer Subjects**: Each domain agent publishes to its own subject
- **Async Processing**: Non-blocking operations with async/await
- **Loose Coupling**: Services communicate via events, not direct calls
- **Scalability**: Independent scaling of services

### 2. Policy-First Resource Access
- **Policy Kernel**: Centralized policy enforcement
- **Budget Management**: API cost tracking and limits
- **RBAC**: Role-based access control with fine-grained permissions
- **Audit Trails**: All policy decisions logged

### 3. Data Sovereignty
- **Per-Field Provenance**: Track source of every data field
- **Immutable History**: Append-only event log
- **Multi-Tenant RLS**: PostgreSQL Row-Level Security
- **Data Lineage**: Full traceability of data transformations

### 4. Deterministic & Explainable
- **Deterministic Scoring**: Same inputs → same outputs
- **Explainability**: Every score has reasons
- **Idempotency**: Retry-safe operations
- **Monotonic State**: State always moves forward

---

## System Components

### Core Services

#### 1. API Gateway (`api/`)
- **Framework**: FastAPI 0.104+
- **Purpose**: HTTP entry point, routing, middleware
- **Features**:
  - OpenAPI documentation
  - Health checks
  - Prometheus metrics endpoint
  - JWT authentication
  - Rate limiting
  - CORS handling
  - Request ID tracking

#### 2. Database (`database/`)
- **Engine**: PostgreSQL 14+ with RLS
- **Schema**: Property records, enrichment data, memos, timeline
- **Migrations**: Alembic-based
- **Features**:
  - Row-Level Security (RLS) for multi-tenancy
  - JSON provenance tracking
  - Indexed for performance
  - Backup and point-in-time recovery

#### 3. Discovery Service (`services/discovery/`)
- **Purpose**: Property intake and normalization
- **Features**:
  - APN hashing for deduplication
  - Address normalization
  - Idempotent ingestion
  - Event publishing on intake

#### 4. Enrichment Service (`services/enrichment/`)
- **Purpose**: Property data enrichment via plugins
- **Plugins**:
  - County Assessor
  - Zillow scraping
  - Census demographics
  - Flood zone mapping
- **Features**:
  - Per-field provenance
  - Plugin orchestration
  - Error handling with retries
  - Cost tracking

#### 5. Scoring Service (`services/scoring/`)
- **Purpose**: Deterministic property scoring
- **Algorithm**: Weighted scoring with thresholds
- **Features**:
  - Explainable scores (reason codes)
  - Monotonic score updates
  - Configurable weights
  - Score history tracking

#### 6. Memo Generator (`services/docgen/`)
- **Purpose**: PDF investment memo generation
- **Engine**: WeasyPrint
- **Features**:
  - Templated memos
  - Score visualization
  - Property images
  - Comparable analysis
  - Export to PDF

#### 7. Outreach Service (`services/outreach/`)
- **Purpose**: Multi-channel outreach orchestration
- **Channels**:
  - Email (SendGrid)
  - SMS (Twilio)
  - Direct mail (Lob.com)
- **Features**:
  - Campaign management
  - Template system
  - Deliverability tracking
  - Cost tracking

#### 8. Timeline Service (`services/timeline/`)
- **Purpose**: Collaboration and activity tracking
- **Features**:
  - Real-time SSE broadcasts
  - Comments and notes
  - Activity feed
  - Tagging and mentions
  - Search and filtering

### Infrastructure Services

#### 9. Authentication (`services/auth/`)
- **Method**: JWT with HS256
- **Features**:
  - Access tokens (30min TTL)
  - Refresh tokens (7 day TTL)
  - Password hashing with bcrypt
  - Role-based permissions
  - Mock users for development

#### 10. Security (`services/security/`)
- **Features**:
  - Rate limiting (Redis-backed)
  - CORS configuration
  - Security headers (CSP, HSTS, etc.)
  - Request ID tracking
  - Input validation and sanitization

#### 11. Observability (`services/observability/`)
- **Logging**: Structured logging with structlog
- **Metrics**: Prometheus metrics
  - HTTP request metrics
  - Business metrics (properties, scores, outreach)
  - Infrastructure metrics (DB, cache, SSE)
- **Error Tracking**: Centralized error logging with context
- **Dashboards**: Grafana dashboards for monitoring

#### 12. Cache (`services/cache/`)
- **Engine**: Redis 7+
- **Features**:
  - Function memoization decorators
  - Cache-aside pattern
  - Event-driven invalidation
  - TTL management
  - Graceful degradation
- **Performance**: 25x speedup for cached queries

#### 13. Data Connectors (`services/connectors/`)
- **Providers**:
  - ATTOM ($0.08/call) - Premium property data
  - Regrid ($0.02/call) - Parcel boundaries
  - OpenAddresses (Free) - Basic geocoding
- **Features**:
  - Automatic fallback
  - Cost tracking
  - Budget management
  - Health monitoring
  - Retry logic

#### 14. Vector Database (`services/vector/`)
- **Engine**: Qdrant
- **Purpose**: Semantic search and similarity
- **Use Cases**:
  - Property similarity search
  - Memo semantic search
  - Recommendation systems
- **Features**:
  - Vector storage (384-dim)
  - Cosine similarity
  - Metadata filtering

### Frontend

#### 15. Next.js Application (`frontend/`)
- **Framework**: Next.js 14 with App Router
- **Features**:
  - Server-side rendering
  - Real-time updates (SSE)
  - React Query for caching
  - Tailwind CSS styling
  - TypeScript
- **Pages**:
  - Property list with filtering
  - Property detail with drawer
  - Score visualization
  - Timeline with real-time updates

---

## Data Flow

### Property Lifecycle

```
1. DISCOVERY
   ├─> Intake API receives property (APN, address)
   ├─> Normalize and deduplicate
   ├─> Store in database
   └─> Publish event: property.discovered

2. ENRICHMENT
   ├─> Listen: property.discovered
   ├─> Fetch data from plugins (Assessor, Zillow, Census)
   ├─> Track provenance per field
   ├─> Store enriched data
   └─> Publish event: property.enriched

3. SCORING
   ├─> Listen: property.enriched
   ├─> Calculate weighted score
   ├─> Generate reason codes
   ├─> Store score + reasons
   └─> Publish event: property.scored

4. MEMO GENERATION
   ├─> Listen: property.scored
   ├─> Generate PDF memo
   ├─> Include score, comps, images
   ├─> Store PDF
   └─> Publish event: memo.generated

5. OUTREACH
   ├─> Listen: memo.generated
   ├─> Select channel (email/SMS/mail)
   ├─> Send via provider (SendGrid/Twilio/Lob)
   ├─> Track deliverability
   └─> Publish event: outreach.sent

6. COLLABORATION
   ├─> User adds comments/notes
   ├─> Broadcast via SSE
   ├─> Update timeline
   └─> Publish event: timeline.updated
```

### Event Flow

```
API Gateway
    ↓
  Router
    ↓
 Handler ─────→ Database
    ↓              ↓
 Publish      Subscribe
    ↓              ↓
Event Bus ←──────────
    ↓
Consumers (Discovery, Enrichment, Scoring, etc.)
```

---

## Event-Driven Architecture

### Event Subjects

| Subject | Producer | Consumers | Payload |
|---------|----------|-----------|---------|
| `event.discovery.intake` | Discovery | Enrichment | `{apn, address, tenant_id}` |
| `event.enrichment.features` | Enrichment | Scoring | `{property_id, features, provenance}` |
| `event.scoring.calculated` | Scoring | Docgen, Cache | `{property_id, score, reasons}` |
| `event.docgen.generated` | Docgen | Outreach | `{property_id, memo_url}` |
| `event.outreach.sent` | Outreach | Timeline | `{property_id, channel, status}` |
| `event.timeline.updated` | Timeline | Frontend (SSE) | `{property_id, event_type, data}` |

### Event Envelope

```json
{
  "event_id": "uuid",
  "event_type": "property.discovered",
  "timestamp": "2025-11-03T00:00:00Z",
  "tenant_id": "tenant-123",
  "correlation_id": "uuid",
  "payload": {
    "property_id": "prop-123",
    "apn": "123-456-789",
    "state": "CA"
  },
  "metadata": {
    "source": "api",
    "user_id": "user-456"
  }
}
```

---

## Security Model

### Authentication Flow

```
1. User Login
   ├─> POST /v1/auth/login (email, password)
   ├─> Verify bcrypt password
   ├─> Generate JWT access token (30min)
   ├─> Generate JWT refresh token (7d)
   └─> Return tokens

2. Authenticated Request
   ├─> Authorization: Bearer <access_token>
   ├─> Middleware validates JWT
   ├─> Extract user_id, tenant_id, role
   └─> Attach to request context

3. Token Refresh
   ├─> POST /v1/auth/refresh (refresh_token)
   ├─> Verify refresh token
   ├─> Generate new access token
   └─> Return new access token
```

### Authorization (RBAC)

**Roles**:
- **Admin**: Full access (users, settings, delete)
- **Analyst**: Properties CRUD, timeline, memos
- **Underwriter**: Read-only + timeline comments
- **Ops**: Properties update, outreach
- **Viewer**: Read-only access

**Permissions**:
```python
PERMISSIONS = {
    "Admin": ["*"],
    "Analyst": ["properties:*", "timeline:*", "memos:read"],
    "Underwriter": ["properties:read", "timeline:comment"],
    "Ops": ["properties:update", "outreach:*"],
    "Viewer": ["properties:read", "timeline:read"]
}
```

### Security Headers

```
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Referrer-Policy: strict-origin-when-cross-origin
```

---

## Multi-Tenancy

### Database Isolation (RLS)

```sql
-- Enable RLS on properties table
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

-- Policy: users can only see their tenant's properties
CREATE POLICY tenant_isolation ON properties
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Set tenant context in session
SET app.current_tenant_id = 'tenant-123';
```

### Application-Level Isolation

```python
# Middleware sets tenant context
@app.middleware("http")
async def tenant_context_middleware(request, call_next):
    user = get_current_user(request)
    set_tenant_context(user.tenant_id)
    response = await call_next(request)
    return response

# All queries automatically filtered by tenant
properties = session.query(Property).all()  # RLS filters by tenant
```

### Cache Isolation

```python
# Cache keys include tenant_id
cache_key = f"realestate:properties:list:{tenant_id}:{filters_hash}"
```

---

## Performance & Caching

### Cache Strategy

**Cache Layers**:
1. **Redis L1**: Hot data (properties, scores)
2. **Database**: Persistent storage
3. **External APIs**: Rate-limited, expensive

**Cache Policies**:

| Data Type | TTL | Invalidation |
|-----------|-----|--------------|
| Property detail | 10 min | On update |
| Property list | 5 min | On create/update/delete |
| Property score | 30 min | On recalculation |
| Timeline | 1 min | On new event |
| User session | 30 min | On logout |

### Cache Invalidation

**Event-Driven**:
```python
# Property updated → invalidate caches
handle_cache_event({
    "type": "property.updated",
    "property_id": "prop-123",
    "tenant_id": "tenant-456"
})
# Automatically invalidates: detail, score, lists
```

**Manual**:
```python
# Admin endpoint for troubleshooting
POST /v1/properties/{property_id}/cache/invalidate
```

### Performance Metrics

- **Cache Hit Rate**: 70-80% expected
- **API Response Time**: <100ms (cached), <500ms (uncached)
- **Database Queries**: <10ms average
- **External APIs**: 500-2000ms (varies by provider)
- **SSE Latency**: <50ms for broadcasts

---

## External Integrations

### Data Providers

| Provider | Purpose | Cost | SLA |
|----------|---------|------|-----|
| ATTOM | Property data | $0.08/call | 99.9% |
| Regrid | Parcel boundaries | $0.02/call | 99.9% |
| OpenAddresses | Geocoding | Free | 99% |
| County Assessor | Public records | Free | Varies |

### Communication Providers

| Provider | Channel | Cost | Features |
|----------|---------|------|----------|
| SendGrid | Email | $0.0001/email | Templates, tracking |
| Twilio | SMS | $0.0079/SMS | Delivery status |
| Lob.com | Direct mail | $0.60/letter | Print and mail |

### Infrastructure

| Service | Purpose | Pricing |
|---------|---------|---------|
| PostgreSQL | Database | Self-hosted or $25/mo+ |
| Redis | Cache | Self-hosted or $10/mo+ |
| Qdrant | Vector DB | Self-hosted or $25/mo+ |

---

## Deployment Architecture

### Production Stack

```
Load Balancer (nginx)
    ↓
API Gateway (FastAPI) × 3 instances
    ↓
    ├─> PostgreSQL (primary + replica)
    ├─> Redis (cluster)
    ├─> Qdrant (cluster)
    └─> External APIs
```

### Scaling Strategy

**Horizontal Scaling**:
- API Gateway: Add instances behind load balancer
- Background Workers: Add consumers to event queues
- Database: Read replicas for queries

**Vertical Scaling**:
- Database: Increase CPU/RAM for complex queries
- Redis: Increase memory for larger cache
- Qdrant: Increase memory for vector storage

### High Availability

- **Database**: Primary + replica with failover
- **Redis**: Cluster with sentinel
- **API**: Multiple instances behind LB
- **Monitoring**: Prometheus + Grafana + PagerDuty

---

## Technology Stack Summary

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 14+
- **Cache**: Redis 7+
- **Vector DB**: Qdrant 1.7+

### Frontend
- **Framework**: Next.js 14
- **Language**: TypeScript 5+
- **Styling**: Tailwind CSS
- **State**: React Query

### Infrastructure
- **Container**: Docker
- **Orchestration**: Docker Compose (dev), Kubernetes (prod)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structlog → Elasticsearch

### Testing
- **Unit Tests**: pytest
- **Integration Tests**: pytest + httpx
- **E2E Tests**: pytest + Playwright
- **Coverage**: pytest-cov (>80% required)

---

## License

MIT License - Real Estate OS
