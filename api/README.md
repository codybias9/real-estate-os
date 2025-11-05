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

**Total: 80+ API Endpoints**

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
│  ├── Authentication & Authorization (JWT + RBAC)            │
│  ├── Property Management                                     │
│  ├── Lead & CRM                                             │
│  ├── Campaign Management                                     │
│  ├── Deal & Portfolio Tracking                              │
│  ├── User Management                                         │
│  └── Analytics & Reporting                                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Services                    │
├─────────────────────────────────────────────────────────────┤
│  ├── PostgreSQL - Primary Database                          │
│  ├── Redis - Caching & Celery Backend                       │
│  ├── RabbitMQ - Message Broker                              │
│  ├── MinIO - Object Storage (S3-compatible)                 │
│  ├── Celery - Background Task Processing                    │
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

### Run Tests
```bash
cd api
pytest
```

### Test Coverage
```bash
pytest --cov=. --cov-report=html
```

### Email Testing
All emails are captured by MailHog:
- Web UI: http://localhost:8025

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

- [ ] WebSocket support for real-time updates
- [ ] Advanced reporting and custom dashboards
- [ ] Integration with external MLS systems
- [ ] Mobile app API enhancements
- [ ] AI-powered lead scoring
- [ ] Automated property valuation

## 📈 Performance

- Sub-100ms response times for most endpoints
- Horizontal scaling support
- Redis caching for frequently accessed data
- Background task processing via Celery
- Database connection pooling

---

Built with ❤️ using FastAPI
