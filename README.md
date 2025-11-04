# Real Estate OS

> 10x better decision speed, not just data

A comprehensive real estate investment platform built with FastAPI, featuring pipeline management, intelligent automation, and real-time collaboration.

## 🎯 Key Features

### Quick Wins (Month 1)
- **Generate & Send Combo**: PDF memo generation → auto-email in one click
- **Auto-Assign on Reply**: Automatic lead assignment when owners respond
- **Stage-Aware Templates**: Context-appropriate email templates
- **Flag Data Issues**: One-click data quality reporting

### Workflow Accelerators
- **Next Best Action (NBA) Panel**: AI-driven recommendations for each property
- **Smart Lists**: Saved queries with dynamic filtering
- **One-Click Tasking**: Convert events into tasks with SLA tracking

### Communication Pipeline
- **Email Threading**: Automatic conversation grouping
- **Call Capture**: Twilio integration with transcription
- **Reply Drafting**: AI-powered response suggestions with objection handling

### Portfolio & Outcomes
- **Deal Economics**: ROI, assignment fees, and profit calculations
- **Investor Readiness**: Red/yellow/green status tracking
- **Template Performance**: A/B testing and champion templates

### Sharing & Collaboration
- **Secure Share Links**: Password-protected, time-limited property sharing
- **Deal Rooms**: Investor portals with document management
- **View Tracking**: Detailed analytics on link engagement

### Data & Propensity
- **Propensity Signals**: Tax delinquency, foreclosure, owner demographics
- **Provenance Inspector**: Track data sources, costs, and quality
- **Deliverability Management**: Bounce tracking and suppression lists

### Automation & Guardrails
- **Cadence Engine**: Multi-channel follow-up automation
- **Compliance Checks**: DNC list verification, opt-out handling
- **Budget Alerts**: Real-time cost tracking with alerts at 80%/100%

### Differentiators
- **Explainable Probability**: Transparent close probability with factor breakdown
- **What-If Analysis**: Deal scenario comparison
- **Investor Network**: Automated buyer matching and outreach

## 🏗️ Architecture

### Backend
- **Framework**: FastAPI 0.111+ with Python 3.11+
- **ORM**: SQLAlchemy 2.0 with Alembic migrations
- **Database**: PostgreSQL 14+ with JSONB, UUID, Row-Level Security
- **Authentication**: JWT tokens with bcrypt password hashing
- **Validation**: Pydantic v2 for request/response schemas

### External Services
- **Email**: SendGrid with delivery tracking webhooks
- **SMS/Voice**: Twilio with transcription and recording
- **Storage**: MinIO (S3-compatible) for PDFs and documents
- **PDF Generation**: WeasyPrint (HTML to PDF)

### Background Jobs
- **Task Queue**: Celery with RabbitMQ broker
- **Result Backend**: Redis
- **Monitoring**: Flower web UI

### Real-Time Features
- **Server-Sent Events (SSE)**: Live pipeline updates
- **Webhooks**: SendGrid and Twilio event processing

### Monitoring
- **Metrics**: Prometheus + Grafana
- **Error Tracking**: Sentry (optional)
- **Logging**: Structured JSON logs

## 📦 Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- RabbitMQ 3.12+
- MinIO (or S3-compatible storage)
- Docker & Docker Compose (for local development)

### Quick Start (Local Development)

1. **Clone the repository**
```bash
git clone https://github.com/codybias9/real-estate-os.git
cd real-estate-os
```

2. **Run setup script**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This script will:
- Check prerequisites
- Create `.env` from `.env.example`
- Start infrastructure services (PostgreSQL, Redis, RabbitMQ, MinIO)
- Run database migrations
- Seed test data

3. **Start the API**
```bash
poetry run uvicorn api.main:app --reload
```

4. **Start Celery workers** (in separate terminals)
```bash
# Main worker
poetry run celery -A api.celery_app worker --loglevel=info -Q memos,enrichment,emails,maintenance

# Beat scheduler (for periodic tasks)
poetry run celery -A api.celery_app beat --loglevel=info

# Flower monitoring UI
poetry run celery -A api.celery_app flower
```

5. **Access the services**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Flower: http://localhost:5555
- MinIO Console: http://localhost:9001

### Docker Compose (All-in-One)

```bash
docker-compose up -d
```

This starts all services:
- API (FastAPI)
- PostgreSQL
- Redis
- RabbitMQ
- MinIO
- Celery Worker
- Celery Beat
- Flower
- Nginx (reverse proxy)
- Prometheus
- Grafana

## 🔑 Authentication

### Test Credentials (from seed data)

```
Admin:   admin@demo.com   / password123
Manager: manager@demo.com / password123
Agent:   agent@demo.com   / password123
Viewer:  viewer@demo.com  / password123
```

### Login Example

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.com", "password": "password123"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@demo.com",
    "full_name": "Admin User",
    "role": "admin",
    "team_id": 1
  }
}
```

### Use Token in Requests

```bash
curl http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer <your-token-here>"
```

## 📚 API Documentation

### Interactive API Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Core Endpoints

#### Properties
- `GET /api/v1/properties` - List properties with filters
- `POST /api/v1/properties` - Create property
- `GET /api/v1/properties/{id}` - Get property details
- `PATCH /api/v1/properties/{id}` - Update property
- `POST /api/v1/properties/{id}/change-stage` - Move pipeline stage
- `GET /api/v1/properties/{id}/timeline` - Get property timeline
- `GET /api/v1/properties/pipeline-stats` - Pipeline distribution

#### Quick Wins
- `POST /api/v1/quick-wins/generate-and-send` - Generate memo + send email
- `POST /api/v1/quick-wins/auto-assign-on-reply/{communication_id}` - Auto-assign property

#### Background Jobs
- `POST /api/v1/jobs/memo/generate` - Queue memo generation
- `POST /api/v1/jobs/enrich/property` - Queue property enrichment
- `POST /api/v1/jobs/email/send` - Queue email sending
- `GET /api/v1/jobs/{job_id}/status` - Check job status

#### Server-Sent Events (SSE)
- `GET /api/v1/sse/stream` - Establish real-time event stream

#### Webhooks
- `POST /api/v1/webhooks/sendgrid` - SendGrid delivery events
- `POST /api/v1/webhooks/twilio/sms` - Twilio SMS status
- `POST /api/v1/webhooks/twilio/voice` - Twilio voice status

## 🔄 Real-Time Updates (SSE)

Connect to Server-Sent Events for live updates:

```javascript
const eventSource = new EventSource('/api/v1/sse/stream', {
  headers: {
    'Authorization': 'Bearer ' + token
  }
});

// Listen for property updates
eventSource.addEventListener('property_updated', (event) => {
  const data = JSON.parse(event.data);
  console.log('Property updated:', data);
  // Update UI in real-time
});

// Listen for stage changes
eventSource.addEventListener('stage_changed', (event) => {
  const data = JSON.parse(event.data);
  // Move card in Kanban board
});

// Listen for email events
eventSource.addEventListener('email_opened', (event) => {
  const data = JSON.parse(event.data);
  // Show notification
});

// Listen for job completions
eventSource.addEventListener('job_complete', (event) => {
  const data = JSON.parse(event.data);
  // Update progress indicator
});
```

## 🗃️ Database Schema

### Core Models
- **Team**: Multi-tenant organization
- **User**: Team members with roles (Admin, Manager, Agent, Viewer)
- **Property**: Real estate properties with pipeline stage tracking
- **Communication**: Email, SMS, calls with threading
- **Template**: Stage-aware email templates with performance tracking
- **Task**: Action items with SLA and priority
- **Deal**: Offer economics and scenarios
- **ShareLink**: Secure property sharing
- **DealRoom**: Investor portals with artifacts

### Supporting Models
- **PropertyProvenance**: Data source tracking
- **PropertyTimeline**: Activity feed
- **PropensitySignal**: Seller likelihood indicators
- **NextBestAction**: AI-driven recommendations
- **SmartList**: Saved property filters
- **Investor**: Buyer network
- **CadenceRule**: Automation rules
- **DeliverabilityMetrics**: Email performance
- **BudgetTracking**: Cost monitoring

## 🚀 Deployment

### Kubernetes (Production)

1. **Configure Secrets**
```bash
kubectl create secret generic real-estate-os-secrets \
  --from-env-file=.env.production
```

2. **Deploy with Helm**
```bash
helm install real-estate-os ./helm \
  --namespace production \
  --values values-production.yaml
```

3. **Configure Ingress with cert-manager**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: real-estate-os
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: api-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: real-estate-os-api
            port:
              number: 8000
```

### Environment Variables

Key configuration (see `.env.example` for complete list):

```bash
# Database (in-cluster PostgreSQL)
DB_DSN=postgresql://user:pass@postgres:5432/real_estate_os

# Redis (in-cluster)
REDIS_URL=redis://redis:6379/0

# RabbitMQ (in-cluster)
RABBITMQ_URL=amqp://admin:admin@rabbitmq:5672/

# MinIO (in-cluster S3-compatible)
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=real-estate-os-files

# External Services (REQUIRED)
SENDGRID_API_KEY=SG.your-api-key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
TWILIO_ACCOUNT_SID=ACyour-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=+1234567890

# JWT Authentication
JWT_SECRET_KEY=your-secure-random-string

# Optional Monitoring
SENTRY_DSN=https://your-key@sentry.io/project-id
```

## 📊 Monitoring

### Metrics (Prometheus)

Default metrics exposed at `/metrics`:
- Request count and duration
- Active SSE connections
- Background job queue lengths
- Database connection pool stats

### Dashboards (Grafana)

Pre-built dashboards available:
- API Performance
- Background Job Status
- Email Deliverability
- User Activity

### Error Tracking (Sentry)

Configure Sentry DSN in `.env`:
```bash
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_ENVIRONMENT=production
```

## 🧪 Testing

### Run Tests
```bash
poetry run pytest
```

### Test Authentication Flow
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.com", "password": "password123"}' \
  | jq -r '.access_token')

# List properties
curl http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer $TOKEN"

# Queue memo generation
curl -X POST http://localhost:8000/api/v1/jobs/memo/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"property_id": 1, "template": "default"}'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL with JSONB and UUID
- **Queue**: Celery + RabbitMQ
- **Cache**: Redis
- **Storage**: MinIO (S3-compatible)
- **Email**: SendGrid
- **SMS/Voice**: Twilio
- **PDF**: WeasyPrint
- **Real-time**: Server-Sent Events (SSE)
- **Monitoring**: Prometheus, Grafana, Sentry
- **Deployment**: Docker, Kubernetes, Helm

## 📞 Support

For support and questions:
- GitHub Issues: https://github.com/codybias9/real-estate-os/issues

---

Built with ❤️ for real estate investors who demand speed and accuracy.
