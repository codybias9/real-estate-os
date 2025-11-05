# Real Estate OS API

A comprehensive Real Estate Operating System API built with FastAPI, providing complete property management, CRM, campaign management, deal tracking, and analytics capabilities.

## 🌟 Features

### Core Functionality
- **🏠 Property Management** (13 endpoints)
  - Full CRUD operations for properties
  - Property images, valuations, notes, and activity tracking
  - Advanced filtering and search
  - Soft deletion support

- **👥 Lead & CRM** (13 endpoints)
  - Lead management with status tracking
  - Activities, notes, and document attachments
  - Lead assignment and scoring
  - Analytics and conversion tracking

- **📧 Campaign Management** (12+ endpoints)
  - Email and SMS campaigns
  - Campaign templates
  - Recipient tracking and analytics
  - Background task processing

- **💼 Deal & Portfolio Management** (15+ endpoints)
  - Deal pipeline management
  - Transaction tracking
  - Portfolio grouping
  - Revenue analytics

- **👤 User Management** (10+ endpoints)
  - Role-based access control (RBAC)
  - User and role management
  - Permission system

- **📊 Analytics & Reporting** (6 endpoints)
  - Dashboard metrics
  - Property, lead, deal, and campaign analytics
  - Revenue reporting
  - Real-time statistics

### Security & Authentication
- **🔐 JWT Authentication** (9 endpoints)
  - User registration and login
  - Email verification
  - Password reset flow
  - Progressive login delays (0→1→2→5→10 sec)
  - Account lockout after 5 failed attempts
  - Configurable password policies

### Advanced Features
- **Multi-tenancy** - Organization-level data isolation
- **Soft Deletes** - Recoverable data deletion
- **Activity Tracking** - Comprehensive audit trails
- **CORS Support** - Cross-origin resource sharing
- **Auto-generated API Docs** - OpenAPI/Swagger
- **Real-time Updates** - Server-Sent Events (SSE) for live updates
- **Background Tasks** - Celery-based async processing
- **Advanced Middleware** - Idempotency, ETags, Rate Limiting, Audit Logging
- **Database Migrations** - Alembic for version-controlled schema changes
- **Comprehensive Testing** - pytest with fixtures and integration tests
- **Production-Ready** - Error handling, logging, health checks, monitoring
- **Easy Deployment** - Docker Compose, startup scripts, demo workflows

## 📋 API Endpoints Summary

### Authentication (9 endpoints)
```
POST   /api/v1/auth/register              - Register new user
POST   /api/v1/auth/login                 - Login user
POST   /api/v1/auth/refresh               - Refresh access token
GET    /api/v1/auth/me                    - Get current user
POST   /api/v1/auth/change-password       - Change password
POST   /api/v1/auth/password-reset-request - Request password reset
POST   /api/v1/auth/password-reset-confirm - Confirm password reset
POST   /api/v1/auth/verify-email          - Verify email address
```

### Properties (13 endpoints)
```
POST   /api/v1/properties                 - Create property
GET    /api/v1/properties                 - List properties
GET    /api/v1/properties/{id}            - Get property
PUT    /api/v1/properties/{id}            - Update property
DELETE /api/v1/properties/{id}            - Delete property
POST   /api/v1/properties/{id}/images     - Add image
GET    /api/v1/properties/{id}/images     - List images
DELETE /api/v1/properties/{id}/images/{image_id} - Delete image
POST   /api/v1/properties/{id}/valuations - Add valuation
GET    /api/v1/properties/{id}/valuations - List valuations
POST   /api/v1/properties/{id}/notes      - Add note
GET    /api/v1/properties/{id}/notes      - List notes
POST   /api/v1/properties/{id}/activities - Add activity
GET    /api/v1/properties/{id}/activities - List activities
```

### Leads (13 endpoints)
```
POST   /api/v1/leads                      - Create lead
GET    /api/v1/leads                      - List leads
GET    /api/v1/leads/stats                - Get lead statistics
GET    /api/v1/leads/{id}                 - Get lead
PUT    /api/v1/leads/{id}                 - Update lead
DELETE /api/v1/leads/{id}                 - Delete lead
POST   /api/v1/leads/{id}/assign          - Assign lead
POST   /api/v1/leads/{id}/activities      - Add activity
GET    /api/v1/leads/{id}/activities      - List activities
POST   /api/v1/leads/{id}/notes           - Add note
GET    /api/v1/leads/{id}/notes           - List notes
POST   /api/v1/leads/{id}/documents       - Add document
GET    /api/v1/leads/{id}/documents       - List documents
```

### Campaigns (12 endpoints)
```
POST   /api/v1/campaigns                  - Create campaign
GET    /api/v1/campaigns                  - List campaigns
GET    /api/v1/campaigns/stats            - Get campaign statistics
GET    /api/v1/campaigns/{id}             - Get campaign
PUT    /api/v1/campaigns/{id}             - Update campaign
DELETE /api/v1/campaigns/{id}             - Delete campaign
POST   /api/v1/campaigns/{id}/send        - Send campaign
POST   /api/v1/campaigns/templates        - Create template
GET    /api/v1/campaigns/templates        - List templates
GET    /api/v1/campaigns/templates/{id}   - Get template
PUT    /api/v1/campaigns/templates/{id}   - Update template
DELETE /api/v1/campaigns/templates/{id}   - Delete template
```

### Deals & Portfolios (15 endpoints)
```
POST   /api/v1/deals                      - Create deal
GET    /api/v1/deals                      - List deals
GET    /api/v1/deals/stats                - Get deal statistics
GET    /api/v1/deals/{id}                 - Get deal
PUT    /api/v1/deals/{id}                 - Update deal
DELETE /api/v1/deals/{id}                 - Delete deal
POST   /api/v1/deals/{id}/transactions    - Create transaction
GET    /api/v1/deals/{id}/transactions    - List transactions
POST   /api/v1/portfolios                 - Create portfolio
GET    /api/v1/portfolios                 - List portfolios
GET    /api/v1/portfolios/stats           - Get portfolio statistics
GET    /api/v1/portfolios/{id}            - Get portfolio
PUT    /api/v1/portfolios/{id}            - Update portfolio
DELETE /api/v1/portfolios/{id}            - Delete portfolio
POST   /api/v1/portfolios/{id}/properties/{property_id} - Add property
DELETE /api/v1/portfolios/{id}/properties/{property_id} - Remove property
```

### User Management (10+ endpoints)
```
POST   /api/v1/users                      - Create user
GET    /api/v1/users                      - List users
GET    /api/v1/users/{id}                 - Get user
PUT    /api/v1/users/{id}                 - Update user
DELETE /api/v1/users/{id}                 - Deactivate user
POST   /api/v1/roles                      - Create role
GET    /api/v1/roles                      - List roles
GET    /api/v1/roles/{id}                 - Get role
PUT    /api/v1/roles/{id}                 - Update role
DELETE /api/v1/roles/{id}                 - Delete role
GET    /api/v1/permissions                - List permissions
GET    /api/v1/permissions/{id}           - Get permission
```

### Analytics (6 endpoints)
```
GET    /api/v1/analytics/dashboard        - Get dashboard metrics
GET    /api/v1/analytics/properties       - Get property analytics
GET    /api/v1/analytics/leads            - Get lead analytics
GET    /api/v1/analytics/deals            - Get deal analytics
GET    /api/v1/analytics/campaigns        - Get campaign analytics
GET    /api/v1/analytics/revenue          - Get revenue analytics
```

### Real-time Updates (2 endpoints)
```
GET    /api/v1/sse/stream                 - SSE event stream for real-time updates
GET    /api/v1/sse/status                 - Get SSE connection status
```

**Total: 73 API Endpoints**

## 🗄️ Database Models (26 Models)

### Organization & Teams (3 models)
- Organization
- Team
- TeamMember

### User & Auth (5 models)
- User
- Role
- Permission
- UserRole
- RolePermission

### Property Management (5 models)
- Property
- PropertyImage
- PropertyValuation
- PropertyNote
- PropertyActivity

### Lead & CRM (4 models)
- Lead
- LeadActivity
- LeadNote
- LeadDocument

### Campaign Management (3 models)
- Campaign
- CampaignTemplate
- CampaignRecipient

### Deal & Portfolio (3 models)
- Deal
- Transaction
- Portfolio

### System Models (3 models)
- IdempotencyKey
- WebhookLog
- AuditLog

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd real-estate-os
```

2. Create environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start all services:
```bash
docker-compose -f docker-compose-api.yaml up -d
```

4. Access the API:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- MinIO Console: http://localhost:9001
- RabbitMQ Management: http://localhost:15672
- MailHog (Email Testing): http://localhost:8025

5. Create your first user:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePass123!",
    "first_name": "Admin",
    "last_name": "User",
    "organization_name": "My Real Estate Company"
  }'
```

### Local Development

1. Install dependencies:
```bash
cd api
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export DB_DSN="postgresql://postgres:postgres@localhost:5432/real_estate_os"
export JWT_SECRET_KEY="your-secret-key"
```

3. Run database migrations:
```bash
# The app will auto-create tables on startup
```

4. Start the API:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📊 Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Real Estate OS API                      │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Application (Python 3.11)                          │
│  ├── Middleware Stack                                        │
│  │   ├── Idempotency (duplicate prevention)                │
│  │   ├── ETag (HTTP caching)                               │
│  │   ├── Rate Limiting (abuse protection)                  │
│  │   └── Audit Logging (activity tracking)                 │
│  ├── Authentication & Authorization (JWT + RBAC)            │
│  ├── Property Management                                     │
│  ├── Lead & CRM                                             │
│  ├── Campaign Management                                     │
│  ├── Deal & Portfolio Tracking                              │
│  ├── User Management                                         │
│  ├── Analytics & Reporting                                   │
│  └── Real-time Updates (SSE)                                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Services                    │
├─────────────────────────────────────────────────────────────┤
│  ├── PostgreSQL - Primary Database                          │
│  ├── Redis - Caching, Rate Limiting, SSE Pub/Sub           │
│  ├── RabbitMQ - Message Broker (Celery)                    │
│  ├── MinIO - Object Storage (S3-compatible)                 │
│  ├── Celery Worker - Background Task Processing             │
│  ├── Celery Beat - Task Scheduler                           │
│  └── MailHog - Email Testing                                │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Key configurations:
- **Database**: `DB_DSN`
- **JWT**: `JWT_SECRET_KEY`, `JWT_ALGORITHM`
- **Email**: `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM_EMAIL`
- **SMS**: `SMS_PROVIDER`, `SMS_API_KEY`
- **Storage**: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- **Celery**: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

### Password Policy (Configurable)
- Minimum length: 8 characters (default)
- Requires uppercase: Yes
- Requires lowercase: Yes
- Requires digits: Yes
- Requires special characters: Yes

### Security Features
- Progressive login delays
- Account lockout after 5 failed attempts (15 min)
- JWT token expiration (30 min access, 7 days refresh)
- Email verification
- Password reset flow

## 🔌 Middleware Stack

The API includes several middleware layers for enhanced functionality:

### 1. Idempotency Middleware
Prevents duplicate request processing using `Idempotency-Key` header:
```bash
curl -X POST "http://localhost:8000/api/v1/properties" \
  -H "Idempotency-Key: unique-request-id-123" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main St", ...}'
```
- Caches responses for 24 hours
- Applies to POST, PUT, PATCH, DELETE methods
- Returns cached response for duplicate requests

### 2. ETag Middleware
HTTP caching using ETags:
```bash
curl -H "If-None-Match: \"abc123\"" \
  http://localhost:8000/api/v1/properties/1
```
- Returns `304 Not Modified` for unchanged resources
- Reduces bandwidth and improves performance

### 3. Rate Limiting Middleware
Protects API from abuse:
- **60 requests per minute** per IP
- **1,000 requests per hour** per IP
- **10,000 requests per day** per IP
- Returns `429 Too Many Requests` when exceeded
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### 4. Audit Log Middleware
Comprehensive activity tracking:
- Logs all successful operations (2xx status codes)
- Captures: user, action, resource, changes, IP, user agent
- Stored in `audit_logs` table
- Queryable for compliance and security

## 🔄 Real-time Updates (Server-Sent Events)

Connect to SSE stream for live updates:

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/sse/stream',
  { headers: { 'Authorization': 'Bearer <token>' } }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data.data);
};

// Available event types:
// - property.created, property.updated, property.deleted
// - lead.created, lead.updated, lead.assigned
// - deal.created, deal.stage_changed
// - campaign.completed
// - notification
```

Benefits:
- Real-time collaboration across teams
- Instant notifications for important events
- Reduced polling and server load
- Organization-level event broadcasting

## ⚙️ Background Tasks (Celery)

Async processing for long-running operations:

### Campaign Tasks
- **send_campaign** - Send email/SMS campaigns to recipients
- Processes recipients in batches
- Updates campaign metrics in real-time

### Email Tasks
- **send_welcome_email** - Welcome new users
- **send_lead_assigned_email** - Notify agents of lead assignments
- **send_deal_stage_changed_email** - Alert on deal stage changes
- **send_daily_analytics_report** - Daily summary emails

### Webhook Tasks
- **send_webhook** - Deliver webhooks with retry logic
- **retry_failed_webhooks** - Retry failed webhooks (max 3 attempts)

### Cleanup Tasks (Scheduled)
- **cleanup_idempotency_keys** - Remove expired keys (hourly)
- **cleanup_audit_logs** - Archive old logs (daily)
- **cleanup_soft_deleted_records** - Purge old deleted records (weekly)

### Start Celery Worker
```bash
celery -A tasks.celery_app worker --loglevel=info
```

### Start Celery Beat (Scheduler)
```bash
celery -A tasks.celery_app beat --loglevel=info
```

## 📖 API Documentation

### Interactive API Docs
Once the API is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication Flow

1. **Register**:
```bash
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "organization_name": "ABC Realty"
}
```

2. **Login**:
```bash
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    ...
  }
}
```

3. **Use Token**:
```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/v1/properties
```

## 🧪 Testing

The API includes comprehensive test coverage with pytest.

### Test Structure
```
api/tests/
├── conftest.py              # Fixtures and test configuration
├── test_auth.py             # Authentication tests (15+ tests)
├── test_properties.py       # Property CRUD and features tests
├── test_leads.py            # Lead management tests
├── test_campaigns.py        # Campaign tests
├── test_deals.py            # Deal and portfolio tests
└── test_integration.py      # End-to-end workflow tests
```

### Run Tests
```bash
cd api
pytest                       # Run all tests
pytest -v                    # Verbose output
pytest -k "test_auth"        # Run specific test file pattern
pytest -m unit               # Run only unit tests
pytest -m integration        # Run only integration tests
pytest --maxfail=1           # Stop after first failure
```

### Test Coverage
```bash
pytest --cov=. --cov-report=html
# View coverage report at htmlcov/index.html
```

### Test Markers
Tests are organized with pytest markers:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.property` - Property-related tests
- `@pytest.mark.auth` - Authentication tests

### Available Fixtures
The test suite includes comprehensive fixtures:
- `db_session` - Database session
- `client` - FastAPI test client
- `organization` - Test organization
- `test_user` - Test user with admin role
- `auth_headers` - Authentication headers
- `test_property` - Sample property
- `test_lead` - Sample lead
- `test_deal` - Sample deal
- `sample_*_data` - Sample data for creation

### Integration Tests
End-to-end workflow tests:
```bash
pytest api/tests/test_integration.py -v
```
Tests include:
- Complete user registration → property → lead → deal workflow
- Property lifecycle (create → images → valuation → update → delete)
- Multi-tenancy isolation
- Lead conversion to deal workflow
- Campaign creation and sending

### Email Testing
All emails are captured by MailHog:
- Web UI: http://localhost:8025

## 🗄️ Database Migrations (Alembic)

The API uses Alembic for version-controlled database schema changes.

### Migration Structure
```
api/migrations/
├── alembic.ini              # Alembic configuration
├── env.py                   # Migration environment
├── script.py.mako           # Migration template
└── versions/                # Migration files
    └── f4c7c458b274_initial_migration_with_all_models.py
```

### Run Migrations
```bash
cd api

# Run all pending migrations
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

### Create New Migration
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column to properties"

# Create blank migration
alembic revision -m "Custom migration"
```

### Migration Best Practices
- Always review auto-generated migrations before applying
- Test migrations on a copy of production data
- Include both upgrade and downgrade paths
- Use `alembic stamp head` to mark existing database as current

## 🌱 Seed Data

Populate the database with sample data for development and testing.

### Full Seed (All Data)
```bash
cd api
python scripts/seed_data.py
```

This creates:
- 2 organizations (Acme Real Estate, Premium Properties LLC)
- 3 roles (Admin, Manager, Agent) with permissions
- 6 users across different roles
- 5 properties with images and valuations
- 5 leads with activities
- 3 deals with transactions
- 1 portfolio
- 1 campaign with template

### Test Credentials (After Seeding)
```
Admin:   admin@acme-realestate.com    / Admin123!
Manager: manager@acme-realestate.com  / Manager123!
Agent:   mike@acme-realestate.com     / Agent123!
```

### Create Admin User Only
```bash
cd api
python scripts/create_admin.py \
  admin@example.com \
  "SecurePass123!" \
  "My Company Name"
```

### Custom Seed Data
Modify `api/scripts/seed_data.py` to customize:
- Organization names and settings
- User roles and permissions
- Sample properties and leads
- Default campaign templates

## 🐳 Docker Services

### Start all services:
```bash
docker-compose -f docker-compose-api.yaml up -d
```

### Start with monitoring (Prometheus + Grafana):
```bash
docker-compose -f docker-compose-api.yaml --profile monitoring up -d
```

### View logs:
```bash
docker-compose -f docker-compose-api.yaml logs -f api
```

### Stop services:
```bash
docker-compose -f docker-compose-api.yaml down
```

### Reset everything (including data):
```bash
docker-compose -f docker-compose-api.yaml down -v
```

## 📦 Dependencies

### Core
- FastAPI 0.104.1
- SQLAlchemy 2.0.23
- Pydantic 2.5.0
- python-jose 3.3.0
- passlib 1.7.4

### Infrastructure
- PostgreSQL 15
- Redis 7.2
- RabbitMQ 3.12
- MinIO (latest)

### Services
- Celery 5.3.4
- aiosmtplib 3.0.1
- boto3/minio 7.2.0
- httpx 0.25.2

See `api/requirements.txt` for complete list.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

[Your License Here]

## 🆘 Support

For issues and questions:
- GitHub Issues: [Your Repository]
- Documentation: http://localhost:8000/docs

## 🎯 Roadmap

- [x] Real-time updates (SSE implemented)
- [x] Background task processing (Celery)
- [x] Advanced middleware (Idempotency, ETag, Rate Limiting, Audit Logging)
- [x] Comprehensive testing suite
- [x] Database migrations (Alembic)
- [x] Seed data scripts
- [ ] Advanced reporting and custom dashboards
- [ ] Integration with external MLS systems
- [ ] Mobile app API enhancements
- [ ] AI-powered lead scoring
- [ ] Automated property valuation
- [ ] WebSocket support for bidirectional real-time communication

## 📈 Performance

- Sub-100ms response times for most endpoints
- Horizontal scaling support
- Redis caching for frequently accessed data
- Background task processing via Celery
- Database connection pooling

## 🛡️ Error Handling & Logging

### Custom Exception Hierarchy
The API implements a comprehensive exception system with specific error types:

```python
# Authentication Errors
AuthenticationError, InvalidCredentialsError, TokenExpiredError, AccountLockedError

# Authorization Errors
AuthorizationError, InsufficientPermissionsError, OrganizationMismatchError

# Resource Errors
ResourceNotFoundError, ResourceAlreadyExistsError, ResourceDeletionError

# Validation Errors
ValidationError, InvalidInputError, MissingRequiredFieldError

# Business Logic Errors
BusinessLogicError, PropertyNotAvailableError, LeadAlreadyConvertedError

# External Service Errors
ExternalServiceError, EmailServiceError, SMSServiceError, StorageServiceError
```

### Consistent Error Response Format
```json
{
  "error": {
    "type": "ValidationError",
    "message": "Request validation failed",
    "details": {
      "errors": [
        {
          "field": "email",
          "message": "invalid email format",
          "type": "value_error.email"
        }
      ]
    }
  }
}
```

### Structured Logging with Loguru
- JSON logging in production for log aggregation
- Colored console output in development
- Contextual logging with request ID, user ID, organization ID
- Automatic log rotation and compression
- Separate error log files

**Log Example:**
```
2024-01-20 10:30:15.123 | INFO     | api.routers.properties:create_property:45 | request_id=abc-123 | user_id=1 | org_id=5 | Creating property
```

### Request Logging Middleware
Every request is logged with:
- Request ID (also in `X-Request-ID` response header)
- HTTP method and path
- Query parameters
- Client IP
- Response status code
- Processing time

## 🏥 Health Checks & Monitoring

### Health Check Endpoints

**Basic Health Check** (`/healthz`):
```bash
curl http://localhost:8000/healthz
```

**Detailed Health Check** (`/health`):
```bash
curl http://localhost:8000/health
```

Returns comprehensive health status:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "service": "Real Estate OS API",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2,
      "details": {"connection": "ok", "query_test": "passed"}
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 1.8,
      "details": {"connected_clients": 5, "used_memory_human": "2.5M"}
    },
    "celery": {
      "status": "healthy",
      "details": {"workers": 2}
    },
    "storage": {
      "status": "healthy",
      "response_time_ms": 12.5,
      "details": {"connection": "ok", "buckets": 1}
    }
  },
  "response_time_ms": 25.3
}
```

**Kubernetes Probes:**
- **Liveness**: `/live` - Checks if the service is alive
- **Readiness**: `/ready` - Checks if the service is ready to accept traffic

## 🚀 Quick Start (Production-Ready)

### Option 1: Using Startup Script (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd real-estate-os

# Run the startup script
./start.sh
```

The startup script will:
1. Check Docker prerequisites
2. Create `.env` from `.env.example` if needed
3. Start all services with Docker Compose
4. Wait for services to be healthy
5. Run database migrations
6. Optionally seed the database
7. Display service URLs and next steps

### Option 2: Manual Docker Compose

```bash
# Start all services
docker-compose -f docker-compose-api.yaml up -d

# With monitoring (Prometheus + Grafana)
docker-compose -f docker-compose-api.yaml --profile monitoring up -d

# View logs
docker-compose -f docker-compose-api.yaml logs -f api

# Stop services
./stop.sh
# or
docker-compose -f docker-compose-api.yaml down
```

### Running the Demo

After starting services, run the interactive demo:

```bash
./demo_api.sh
```

The demo showcases:
- User registration and authentication
- Property creation and management
- Lead tracking and activities
- Deal pipeline workflow
- Analytics dashboard
- Campaign creation

### Access Points

After startup, access:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **RabbitMQ**: http://localhost:15672 (admin/admin)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **MailHog**: http://localhost:8025
- **Prometheus**: http://localhost:9090 (if using monitoring profile)
- **Grafana**: http://localhost:3001 (admin/admin, if using monitoring profile)

## 📚 API Documentation & Examples

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Example Collections
Comprehensive API examples available in:
- `API_EXAMPLES.md` - Complete cURL examples for all endpoints
- Includes authentication, CRUD operations, filters, pagination
- Real-time updates and advanced features

### Quick Example

```bash
# Register user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "organization_name": "Acme Real Estate"
  }'

# Create property (with auth token)
curl -X POST "http://localhost:8000/api/v1/properties" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St",
    "city": "Los Angeles",
    "state": "CA",
    "zip_code": "90001",
    "property_type": "single_family",
    "price": 750000,
    "bedrooms": 3,
    "bathrooms": 2.5
  }'
```

## 🔧 Development

### Local Development Setup

```bash
cd api

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DB_DSN="postgresql://postgres:postgres@localhost:5432/real_estate_os"
export JWT_SECRET_KEY="your-secret-key"
export REDIS_URL="redis://localhost:6379/0"

# Run migrations
alembic upgrade head

# Seed database (optional)
python scripts/seed_data.py

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
cd api

# Run all tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m property
pytest -m auth

# Verbose output
pytest -v

# Stop after first failure
pytest --maxfail=1
```

## 📦 Production Deployment

### Environment Variables

Key production settings in `.env`:

```bash
# Security
JWT_SECRET_KEY=<strong-random-secret>
DEBUG=false

# Database
DB_DSN=postgresql://user:password@host:5432/dbname

# Redis & Celery
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/0

# Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=<password>

# Storage
MINIO_ENDPOINT=storage.example.com:9000
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>
MINIO_SECURE=true
```

### Deployment Checklist

- [ ] Set strong `JWT_SECRET_KEY`
- [ ] Set `DEBUG=false`
- [ ] Configure production database
- [ ] Set up email service (SMTP)
- [ ] Configure object storage (MinIO/S3)
- [ ] Set up SSL/TLS certificates
- [ ] Configure rate limiting
- [ ] Set up log aggregation
- [ ] Configure monitoring (Prometheus/Grafana)
- [ ] Set up backup strategy
- [ ] Configure CORS origins
- [ ] Review security settings

### Kubernetes Deployment

Health check endpoints are Kubernetes-ready:

```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

Built with ❤️ using FastAPI
