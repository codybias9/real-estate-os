# Real Estate OS - Deployment Guide

Complete guide for deploying Real Estate OS to development, staging, and production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Configuration](#configuration)
6. [Database Setup](#database-setup)
7. [Monitoring & Observability](#monitoring--observability)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB SSD
- OS: Linux (Ubuntu 20.04+), macOS, Windows (WSL2)

**Recommended (Production)**:
- CPU: 4+ cores
- RAM: 16 GB
- Disk: 100 GB SSD
- OS: Linux (Ubuntu 22.04 LTS)

### Software Dependencies

```bash
# Required
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker 20.10+ & Docker Compose 2.0+
- Node.js 18+ (for frontend)

# Optional
- Qdrant 1.7+ (for vector search)
- nginx 1.20+ (for production)
- Prometheus + Grafana (for monitoring)
```

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/real-estate-os.git
cd real-estate-os
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Install Services

```bash
# Install all services in editable mode
cd services/auth && pip install -e ".[dev]"
cd ../cache && pip install -e ".[dev]"
cd ../connectors && pip install -e ".[dev]"
cd ../observability && pip install -e ".[dev]"
cd ../security && pip install -e ".[dev]"
cd ../vector && pip install -e ".[dev]"
cd ../..
```

### 4. Start Infrastructure

```bash
# Start PostgreSQL, Redis, Qdrant
docker-compose up -d postgres redis qdrant
```

### 5. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Example `.env`**:
```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/realestate
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256

# External APIs
ATTOM_API_KEY=your-attom-key
REGRID_API_KEY=your-regrid-key

# Email
SENDGRID_API_KEY=your-sendgrid-key
SENDGRID_FROM_EMAIL=noreply@example.com

# SMS
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_FROM_NUMBER=+15551234567

# Direct Mail
LOB_API_KEY=your-lob-key
```

### 6. Run Database Migrations

```bash
# Run Alembic migrations
cd database
alembic upgrade head
cd ..
```

### 7. Start API Server

```bash
# Development server with hot reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Start Frontend (Optional)

```bash
cd frontend
npm install
npm run dev
```

Visit:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

---

## Docker Deployment

### Full Stack with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: realestate
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  qdrant:
    image: qdrant/qdrant:v1.7.0
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/realestate
      REDIS_URL: redis://redis:6379/0
      QDRANT_URL: http://qdrant:6333
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

---

## Production Deployment

### Architecture

```
Internet
    ↓
[Load Balancer / nginx]
    ↓
[API Gateway × 3 instances]
    ↓
    ├─> [PostgreSQL Primary + Replica]
    ├─> [Redis Cluster]
    └─> [Qdrant Cluster]
```

### 1. Server Setup (Ubuntu 22.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install nginx
sudo apt install nginx -y

# Install certbot (SSL)
sudo apt install certbot python3-certbot-nginx -y
```

### 2. Configure nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/realestate

upstream api_backend {
    least_conn;
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 80;
    server_name api.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy settings
    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # SSE endpoint (longer timeout)
    location /v1/timeline/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 1h;
    }

    # Static files (if serving frontend)
    location /static/ {
        alias /var/www/realestate/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/realestate /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. SSL Certificate (Let's Encrypt)

```bash
sudo certbot --nginx -d api.example.com
```

### 4. Production Environment Variables

```bash
# /opt/realestate/.env.production

# Database (use connection pooling)
DATABASE_URL=postgresql://realestate:secure_password@localhost:5432/realestate_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis (cluster or sentinel)
REDIS_URL=redis://localhost:6379/0
REDIS_SENTINEL_URLS=redis://sentinel1:26379,redis://sentinel2:26379

# Security
JWT_SECRET_KEY=$(openssl rand -base64 32)
JWT_ALGORITHM=HS256
ALLOWED_HOSTS=api.example.com

# External APIs
ATTOM_API_KEY=production-key
REGRID_API_KEY=production-key

# Logging
LOG_LEVEL=INFO
JSON_LOGS=true

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
PROMETHEUS_ENABLED=true
```

### 5. Run Production Stack

```bash
# Create production directory
sudo mkdir -p /opt/realestate
cd /opt/realestate

# Clone repository
git clone https://github.com/yourusername/real-estate-os.git .

# Copy production env
cp .env.production .env

# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose exec api alembic upgrade head
```

### 6. Systemd Service (Alternative to Docker)

```ini
# /etc/systemd/system/realestate-api.service

[Unit]
Description=Real Estate OS API
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=realestate
Group=realestate
WorkingDirectory=/opt/realestate
Environment="PATH=/opt/realestate/venv/bin"
EnvironmentFile=/opt/realestate/.env
ExecStart=/opt/realestate/venv/bin/uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable realestate-api
sudo systemctl start realestate-api
sudo systemctl status realestate-api
```

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | Yes |
| `QDRANT_URL` | Qdrant server URL | `http://localhost:6333` | No |
| `JWT_SECRET_KEY` | Secret key for JWT signing | - | Yes |
| `ATTOM_API_KEY` | ATTOM API key | - | No |
| `REGRID_API_KEY` | Regrid API key | - | No |
| `SENDGRID_API_KEY` | SendGrid API key | - | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | No |

### Application Configuration

```python
# config.py

from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str
    redis_ttl: int = 3600

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # API
    api_title: str = "Real Estate OS"
    api_version: str = "1.0.0"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Database Setup

### Initial Setup

```bash
# Create database
createdb realestate

# Create user
psql -c "CREATE USER realestate WITH PASSWORD 'secure_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE realestate TO realestate;"
```

### Migrations

```bash
# Create migration
alembic revision -m "Add new table"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current version
alembic current
```

### Backup

```bash
# Full backup
pg_dump -U postgres realestate > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
pg_dump -U postgres realestate | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore
psql -U postgres realestate < backup_20251103.sql
```

### Performance Tuning

```sql
-- Add indexes
CREATE INDEX idx_properties_tenant_id ON properties(tenant_id);
CREATE INDEX idx_properties_state ON properties(state);
CREATE INDEX idx_properties_created_at ON properties(created_at DESC);

-- Analyze tables
ANALYZE properties;
ANALYZE timeline_events;

-- Vacuum
VACUUM ANALYZE;
```

---

## Monitoring & Observability

### Prometheus Setup

```yaml
# prometheus.yml

global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'realestate-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Import pre-built dashboards from `services/observability/dashboards/`:
- `api-overview.json` - HTTP metrics, latency, errors
- `business-metrics.json` - Property ops, scoring, outreach

### Logging

```bash
# View logs (Docker)
docker-compose logs -f api

# View logs (systemd)
sudo journalctl -u realestate-api -f

# Search logs
docker-compose logs api | grep ERROR
```

### Health Checks

```bash
# API health
curl http://localhost:8000/v1/health

# Database health
curl http://localhost:8000/v1/health/db

# Metrics
curl http://localhost:8000/metrics
```

---

## Backup & Recovery

### Automated Backups

```bash
#!/bin/bash
# /opt/scripts/backup.sh

BACKUP_DIR="/backups/realestate"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump -U postgres realestate | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Redis backup (if persistent)
redis-cli --rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.rdb" -mtime +30 -delete
```

Cron job:
```cron
# Run daily at 2 AM
0 2 * * * /opt/scripts/backup.sh
```

### Disaster Recovery

```bash
# 1. Restore database
gunzip < backup_20251103.sql.gz | psql -U postgres realestate

# 2. Restart services
docker-compose restart

# 3. Verify health
curl http://localhost:8000/v1/health
```

---

## Troubleshooting

### API Not Starting

```bash
# Check logs
docker-compose logs api

# Common issues:
# - Database not reachable
# - Environment variables missing
# - Port already in use
```

### Database Connection Issues

```bash
# Test connection
psql postgresql://postgres:postgres@localhost:5432/realestate

# Check PostgreSQL status
sudo systemctl status postgresql

# Check connections
SELECT count(*) FROM pg_stat_activity;
```

### Redis Connection Issues

```bash
# Test connection
redis-cli ping

# Check Redis status
sudo systemctl status redis

# Clear cache
redis-cli FLUSHALL
```

### High Memory Usage

```bash
# Check memory
free -h
docker stats

# Optimize PostgreSQL
# Edit postgresql.conf:
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
```

### Slow Queries

```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Find slow queries
SELECT query, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Security Checklist

- [ ] Change default passwords
- [ ] Use strong JWT secret key
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall (ufw/iptables)
- [ ] Enable rate limiting
- [ ] Set up monitoring and alerting
- [ ] Regular security updates
- [ ] Automated backups
- [ ] Secure environment variables
- [ ] Enable audit logging

---

## Performance Optimization

### Application Level
- Enable caching (Redis)
- Use connection pooling
- Optimize database queries
- Enable compression
- Use CDN for static assets

### Database Level
- Add appropriate indexes
- Use connection pooling
- Regular VACUUM and ANALYZE
- Tune PostgreSQL configuration
- Use read replicas

### Infrastructure Level
- Horizontal scaling (multiple API instances)
- Load balancing
- CDN for frontend assets
- Database replication
- Redis clustering

---

## License

MIT License - Real Estate OS
