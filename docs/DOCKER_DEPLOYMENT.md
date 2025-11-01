# Docker Deployment Guide

**PR#3: ops/docker-compose**

Complete guide to containerizing and deploying Real Estate OS with Docker and Kubernetes.

## Table of Contents

1. [Overview](#overview)
2. [Docker Compose (Local Development)](#docker-compose-local-development)
3. [Production Deployment](#production-deployment)
4. [Kubernetes Deployment (Helm)](#kubernetes-deployment-helm)
5. [Security Best Practices](#security-best-practices)
6. [Monitoring & Health Checks](#monitoring--health-checks)
7. [Troubleshooting](#troubleshooting)

---

## Overview

Real Estate OS provides multi-stage Docker builds for:
- **API** (FastAPI + Python 3.11)
- **Web** (React + Vite + Nginx)
- **PostgreSQL** database
- **Redis** cache

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Load Balancer / Ingress                │
└────────────┬────────────────────────────────────────────────┘
             │
       ┌─────┴──────┐
       │            │
   ┌───▼────┐   ┌──▼─────┐
   │  Web   │   │  API   │
   │ (Nginx)│   │(FastAPI)│
   │  8080  │   │  8000  │
   └───┬────┘   └──┬─────┘
       │           │
       │       ┌───┴──────┬──────────┐
       │       │          │          │
       │   ┌───▼────┐ ┌──▼────┐ ┌──▼────┐
       │   │ Postgres│ │ Redis │ │ ML    │
       │   │  5432  │ │ 6379  │ │Service│
       │   └────────┘ └───────┘ └───────┘
       │
       └─────────────────────────────────────┐
                                             │
                                         Static
                                         Assets
```

---

## Docker Compose (Local Development)

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/real-estate-os.git
cd real-estate-os

# Copy environment file
cp .env.example .env

# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))" > .jwt_secret
export JWT_SECRET_KEY=$(cat .jwt_secret)

# Update .env with your configuration
nano .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| **web** | 8080 | React frontend (Nginx) |
| **api** | 8000 | FastAPI backend |
| **postgres** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache |

### Development Mode

```bash
# Start with development overrides (hot reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Start with development tools (pgAdmin, Redis Commander, Mailhog)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile tools up
```

**Development Tools:**
- **PgAdmin**: http://localhost:5050 (Database UI)
- **Redis Commander**: http://localhost:8081 (Redis UI)
- **Mailhog**: http://localhost:8025 (Email testing)

### Environment Variables

Required in `.env`:

```bash
# Database
POSTGRES_DB=real_estate_os
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<secure-password>

# Redis
REDIS_PASSWORD=<secure-password>

# Authentication (REQUIRED)
JWT_SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:8080

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_TENANT_MINUTE=100

# Email (Optional)
EMAIL_PROVIDER=smtp
SENDGRID_API_KEY=

# Observability (Optional)
SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

### Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild images
docker-compose build

# View logs
docker-compose logs -f api
docker-compose logs -f web

# Execute command in container
docker-compose exec api bash
docker-compose exec postgres psql -U postgres real_estate_os

# Run database migrations
docker-compose exec api alembic upgrade head

# Run tests
docker-compose exec api pytest
docker-compose exec web npm test

# Restart specific service
docker-compose restart api

# Remove volumes (CAUTION: deletes data)
docker-compose down -v
```

---

## Production Deployment

### Multi-Stage Builds

**API Dockerfile** (`api/Dockerfile`):
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder
RUN pip install --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime
COPY --from=builder /root/.local /root/.local
USER appuser
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0"]
```

**Web Dockerfile** (`web/Dockerfile`):
```dockerfile
# Stage 1: Build React app
FROM node:18-alpine AS builder
RUN npm ci && npm run build

# Stage 2: Serve with Nginx
FROM nginx:1.25-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
USER appuser
```

### Building Images

```bash
# Build API image
docker build -t real-estate-os-api:1.0.0 -f api/Dockerfile .

# Build Web image
docker build -t real-estate-os-web:1.0.0 -f web/Dockerfile .

# Tag for registry
docker tag real-estate-os-api:1.0.0 registry.example.com/real-estate-os-api:1.0.0
docker tag real-estate-os-web:1.0.0 registry.example.com/real-estate-os-web:1.0.0

# Push to registry
docker push registry.example.com/real-estate-os-api:1.0.0
docker push registry.example.com/real-estate-os-web:1.0.0
```

### Security Scanning

```bash
# Install Trivy
brew install trivy  # macOS
apt-get install trivy  # Linux

# Scan images for vulnerabilities
trivy image real-estate-os-api:1.0.0
trivy image real-estate-os-web:1.0.0

# Generate report
trivy image --format json --output api-vulnerabilities.json real-estate-os-api:1.0.0

# Fail on HIGH/CRITICAL vulnerabilities
trivy image --exit-code 1 --severity HIGH,CRITICAL real-estate-os-api:1.0.0
```

---

## Kubernetes Deployment (Helm)

### Prerequisites

```bash
# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Connect to cluster
kubectl config use-context production
```

### Deploy with Helm

```bash
cd k8s/helm

# Validate chart
helm lint .

# Dry run (see what will be created)
helm install real-estate-os . --dry-run --debug

# Install chart
helm install real-estate-os . \
  --namespace real-estate-os \
  --create-namespace \
  --set api.image.tag=1.0.0 \
  --set web.image.tag=1.0.0

# Upgrade existing deployment
helm upgrade real-estate-os . \
  --namespace real-estate-os \
  --set api.image.tag=1.0.1

# Rollback
helm rollback real-estate-os 1

# Uninstall
helm uninstall real-estate-os --namespace real-estate-os
```

### Helm Values

**Production values** (`values.production.yaml`):
```yaml
api:
  replicaCount: 5
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
  autoscaling:
    enabled: true
    maxReplicas: 20

postgresql:
  primary:
    persistence:
      size: 100Gi
    resources:
      limits:
        memory: 4Gi
        cpu: 2000m

ingress:
  enabled: true
  hosts:
    - host: api.real-estate-os.com
    - host: app.real-estate-os.com
```

Deploy with custom values:
```bash
helm install real-estate-os . -f values.production.yaml
```

### Kubernetes Resources

The Helm chart creates:
- **Deployments**: API (3 replicas), Web (2 replicas)
- **Services**: ClusterIP for internal communication
- **Ingress**: HTTPS with cert-manager
- **HPA**: Horizontal Pod Autoscaler (3-10 pods)
- **PDB**: Pod Disruption Budget (min 1 available)
- **ConfigMaps**: Application configuration
- **Secrets**: Database credentials, JWT secrets
- **ServiceMonitor**: Prometheus metrics

### Monitoring

```bash
# Check pod status
kubectl get pods -n real-estate-os

# View logs
kubectl logs -f -l app.kubernetes.io/component=api -n real-estate-os

# Describe pod
kubectl describe pod real-estate-os-api-xxxx -n real-estate-os

# Port forward for debugging
kubectl port-forward svc/real-estate-os-api 8000:8000 -n real-estate-os

# Execute command in pod
kubectl exec -it real-estate-os-api-xxxx -n real-estate-os -- bash

# Check HPA status
kubectl get hpa -n real-estate-os

# Check ingress
kubectl get ingress -n real-estate-os
```

---

## Security Best Practices

### Container Security

✅ **Implemented:**
- Non-root user (UID 1001)
- Read-only root filesystem
- Dropped all capabilities
- Multi-stage builds (minimal runtime image)
- No secrets in images (environment variables)
- Health checks for all services
- Security headers in Nginx
- Trivy vulnerability scanning

### Secrets Management

**Development:**
```bash
# Use .env file (not committed to git)
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

**Production (Kubernetes):**
```bash
# Create secrets
kubectl create secret generic database-credentials \
  --from-literal=dsn=postgresql://user:pass@host:5432/db \
  --namespace real-estate-os

kubectl create secret generic jwt-secret \
  --from-literal=secret-key=$(python -c "import secrets; print(secrets.token_urlsafe(32))") \
  --namespace real-estate-os

# Or use external secrets operator
kubectl apply -f k8s/external-secrets.yaml
```

**Best Practice: Use Vault or AWS Secrets Manager in production**

### Network Security

- **Network Policies**: Restrict pod-to-pod communication
- **Ingress TLS**: cert-manager with Let's Encrypt
- **Rate Limiting**: Nginx ingress rate limits
- **CORS**: Strict origin allowlist

---

## Monitoring & Health Checks

### Health Checks

**API** (`/healthz`):
```bash
curl http://localhost:8000/healthz
# Response: {"status": "ok"}
```

**Web** (`/health`):
```bash
curl http://localhost:8080/health
# Response: OK
```

### Docker Health Checks

Defined in Dockerfiles:
```yaml
# API
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

# Web
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1
```

Check health status:
```bash
docker ps
# Look for "healthy" in STATUS column
```

### Kubernetes Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 40
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

---

## Troubleshooting

### Docker Compose Issues

**"Cannot connect to database"**
```bash
# Check if postgres is healthy
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart postgres
docker-compose restart postgres

# Check connection
docker-compose exec api python -c "import psycopg2; print('OK')"
```

**"JWT_SECRET_KEY not set"**
```bash
# Ensure .env file exists
cat .env | grep JWT_SECRET_KEY

# Generate if missing
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
echo "JWT_SECRET_KEY=<generated-key>" >> .env

# Restart services
docker-compose restart api
```

**"Port already in use"**
```bash
# Find process using port
lsof -i :8000

# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Map to different host port
```

### Kubernetes Issues

**"ImagePullBackOff"**
```bash
# Check image exists in registry
docker pull registry.example.com/real-estate-os-api:1.0.0

# Check imagePullSecrets
kubectl get secrets -n real-estate-os

# Describe pod for details
kubectl describe pod <pod-name> -n real-estate-os
```

**"CrashLoopBackOff"**
```bash
# View logs
kubectl logs <pod-name> -n real-estate-os

# Check previous logs if restarted
kubectl logs <pod-name> -n real-estate-os --previous

# Check events
kubectl get events -n real-estate-os --sort-by='.lastTimestamp'
```

**"Service unavailable"**
```bash
# Check all resources
kubectl get all -n real-estate-os

# Check endpoints
kubectl get endpoints -n real-estate-os

# Check ingress
kubectl describe ingress real-estate-os -n real-estate-os
```

---

## Next Steps

- **PR#4**: Observability (OpenTelemetry, Prometheus, Grafana, Sentry)
- **PR#5**: Redis caching for performance
- **Future**: Multi-region deployment
- **Future**: Blue-green deployments
- **Future**: Auto-scaling policies

---

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Trivy Security Scanner](https://trivy.dev/)
