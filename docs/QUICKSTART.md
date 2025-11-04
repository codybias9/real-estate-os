# ⚡ Quick Start - Real Estate OS

Get the platform running in **5 minutes** with zero configuration!

---

## 🎯 Prerequisites

- **Docker Desktop** installed and running
- **Git** installed
- **4GB+ RAM** available
- **Port 8000** available (API)

---

## 🚀 Start in 3 Commands

```bash
# 1. Clone
git clone https://github.com/codybias9/real-estate-os.git
cd real-estate-os

# 2. Start (wait ~2 minutes)
./scripts/docker/start.sh

# 3. Seed demo data
./scripts/demo/seed.sh
```

**That's it!** ✅

---

## 🎬 Try It Out

### Open API Documentation

```bash
open http://localhost:8000/docs
```

### Login with Demo Account

**Credentials:**
```
Email:    admin@demo.com
Password: password123
```

**Using curl:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.com", "password": "password123"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@demo.com",
    "full_name": "Admin User",
    "role": "admin"
  }
}
```

### List Properties

```bash
# Replace <TOKEN> with access_token from login
curl http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer <TOKEN>"
```

### Send a Mock Email

```bash
curl -X POST http://localhost:8000/api/v1/communications/email/send \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "to_email": "owner@example.com",
    "subject": "Investment Opportunity",
    "body": "<p>We would like to make an offer on your property.</p>"
  }'
```

**Result:** Email sent via mock SendGrid (no API key needed!)

---

## 🎛️ Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| **API Docs** | http://localhost:8000/docs | - |
| **API Redoc** | http://localhost:8000/redoc | - |
| **Celery Jobs** | http://localhost:5555 | - |
| **RabbitMQ** | http://localhost:15672 | admin/admin |
| **MinIO** | http://localhost:9001 | minioadmin/minioadmin |
| **Grafana** | http://localhost:3001 | admin/admin |

---

## 📊 What's Running?

```bash
# Check service health
./scripts/docker/health.sh

# View logs
docker-compose logs -f api

# Check all containers
docker ps
```

**11 Services Running:**
1. PostgreSQL (database)
2. Redis (cache)
3. RabbitMQ (message queue)
4. MinIO (S3 storage)
5. FastAPI (backend API)
6. Celery Worker (background jobs)
7. Celery Beat (scheduler)
8. Flower (job monitoring)
9. Nginx (reverse proxy)
10. Prometheus (metrics)
11. Grafana (dashboards)

---

## 🎯 Common Tasks

### Stop Everything

```bash
./scripts/docker/stop.sh
```

### Restart

```bash
./scripts/docker/stop.sh
./scripts/docker/start.sh
```

### Reseed Data

```bash
./scripts/demo/seed.sh
```

### Run Tests

```bash
./scripts/test/run_tests.sh
```

### Generate Proofs

```bash
./scripts/proofs/run_all_proofs.sh
```

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Restart stack
./scripts/docker/start.sh
```

### Services Not Starting

```bash
# Check Docker resources (need 4GB+ RAM)
docker info

# Restart Docker Desktop

# Try again
./scripts/docker/start.sh
```

### Database Errors

```bash
# Check PostgreSQL
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

---

## 📚 Next Steps

1. **[Demo Guide](DEMO_GUIDE.md)** - Complete demo scenarios
2. **[API Documentation](http://localhost:8000/docs)** - Interactive API docs
3. **[Full README](../README.md)** - Complete project documentation
4. **[Testing Guide](TESTING_GUIDE.md)** - Run tests and check coverage

---

## ✨ Key Features to Try

### 1. Create a Property

```bash
curl -X POST http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "456 Demo St",
    "city": "Los Angeles",
    "state": "CA",
    "zip_code": "90001",
    "owner_name": "John Doe",
    "asking_price": 500000
  }'
```

### 2. Get Next Best Actions

```bash
curl -X POST http://localhost:8000/api/v1/workflow/next-best-actions/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"property_id": 1}'
```

### 3. Generate Property Memo

```bash
curl -X POST http://localhost:8000/api/v1/jobs/memo/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"property_id": 1, "template": "default"}'
```

### 4. View Timeline

```bash
curl http://localhost:8000/api/v1/properties/1/timeline \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 🎉 You're Ready!

The platform is now running with:
- ✅ 50 demo properties
- ✅ 4 demo users
- ✅ Complete API functionality
- ✅ Mock mode (no external APIs)

**Explore the API docs:** http://localhost:8000/docs

**Need help?** Check [DEMO_GUIDE.md](DEMO_GUIDE.md) for complete walkthrough!

---

**Total Time:** ~5 minutes ⚡
**Setup Required:** Zero 🎯
**External APIs Needed:** None 🚀
