# REAL ESTATE OS - PLATFORM COMPLETION ROADMAP
**Date**: 2024-11-02  
**Purpose**: Actionable plan to achieve production readiness  
**Timeline**: 12-16 weeks  
**Based On**: Comprehensive Platform Audit findings

---

## EXECUTIVE SUMMARY

This roadmap provides a structured plan to complete the Real Estate OS platform
from its current state (35% complete) to production-ready (95%+ complete).

**Current State**: Strong architecture with partial implementation  
**Target State**: Production-ready multi-tenant SaaS platform  
**Timeline**: 12-16 weeks with focused development  
**Team Size**: Recommended 2-3 full-time engineers

---

## PHASE 1: FOUNDATION (Weeks 1-3)
**Goal**: Establish core infrastructure and security  
**Priority**: P0 - Blocking issues

### Week 1: Database Foundation

**Task 1.1: Create Base Schema**
```sql
-- File: db/migrations/001_create_base_schema.sql

-- Tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Properties table (core)
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Address
    address TEXT NOT NULL,
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(10),
    county VARCHAR(100),
    latitude NUMERIC(10, 7),
    longitude NUMERIC(11, 7),
    
    -- Normalized address (from libpostal)
    normalized_address TEXT,
    address_hash VARCHAR(16),
    
    -- Property details
    price NUMERIC(15, 2),
    bedrooms INTEGER,
    bathrooms NUMERIC(4, 1),
    sqft INTEGER,
    lot_size NUMERIC(10, 2),
    year_built INTEGER,
    property_type VARCHAR(50),
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Enable RLS
    CONSTRAINT properties_tenant_id_check CHECK (tenant_id IS NOT NULL)
);

-- Enable RLS
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY tenant_isolation_policy ON properties
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_policy ON users
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Indexes
CREATE INDEX idx_properties_tenant_id ON properties(tenant_id);
CREATE INDEX idx_properties_address_hash ON properties(address_hash);
CREATE INDEX idx_properties_city_state ON properties(city, state);
CREATE INDEX idx_properties_status ON properties(status);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- Full-text search
CREATE INDEX idx_properties_address_fts ON properties 
    USING gin(to_tsvector('english', address));
```

**Task 1.2: Apply Migrations**
- Run migration 001
- Verify tables created
- Test RLS policies
- Load seed data

**Deliverables**:
- ✅ Complete base schema
- ✅ RLS on all tables
- ✅ Proper indexes
- ✅ Migration scripts
- ✅ Seed data script

**Acceptance Criteria**:
- [ ] All tables created successfully
- [ ] RLS policies prevent cross-tenant access
- [ ] Indexes improve query performance
- [ ] Seed data loads without errors

---

### Week 2: Authentication & Authorization

**Task 2.1: Keycloak Integration**
```python
# File: api/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
import os

security = HTTPBearer()

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "real-estate-os")
KEYCLOAK_PUBLIC_KEY = os.getenv("KEYCLOAK_PUBLIC_KEY")

class User:
    def __init__(self, user_id: str, email: str, tenant_id: str, roles: list):
        self.user_id = user_id
        self.email = email
        self.tenant_id = tenant_id
        self.roles = roles

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            KEYCLOAK_PUBLIC_KEY,
            algorithms=["RS256"],
            audience="account"
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    
    return User(
        user_id=payload.get("sub"),
        email=payload.get("email"),
        tenant_id=payload.get("tenant_id"),
        roles=payload.get("realm_access", {}).get("roles", [])
    )

async def require_role(required_role: str):
    async def role_checker(user: User = Depends(get_current_user)):
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return user
    return role_checker
```

**Task 2.2: Database Context**
```python
# File: api/db_context.py

from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_db_session(tenant_id: str):
    """Get database session with tenant context set."""
    session = SessionLocal()
    try:
        # Set tenant context for RLS
        session.execute(
            text("SET app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**Task 2.3: Rate Limiting Middleware**
```python
# File: api/rate_limiter.py

from fastapi import Request, HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            "default": (100, 60),  # 100 requests per minute
            "auth": (10, 60),      # 10 auth requests per minute
            "api": (1000, 60)      # 1000 API requests per minute
        }
    
    async def check_rate_limit(
        self,
        request: Request,
        limit_type: str = "default"
    ):
        client_id = request.client.host
        limit, window = self.limits.get(limit_type, self.limits["default"])
        
        now = datetime.now()
        cutoff = now - timedelta(seconds=window)
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= limit:
            retry_after = int((self.requests[client_id][0] - cutoff).total_seconds())
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)}
            )
        
        # Record request
        self.requests[client_id].append(now)

rate_limiter = RateLimiter()
```

**Deliverables**:
- ✅ JWT token validation
- ✅ User extraction from tokens
- ✅ Role-based access control
- ✅ Database session with tenant context
- ✅ Rate limiting middleware

**Acceptance Criteria**:
- [ ] Valid JWT tokens are accepted
- [ ] Invalid tokens are rejected
- [ ] RLS enforces tenant isolation
- [ ] Rate limits return 429 with Retry-After

---

### Week 3: Core API Endpoints

**Task 3.1: Property CRUD**
```python
# File: api/endpoints/properties.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from uuid import UUID

from api.auth import get_current_user, User
from api.db_context import get_db_session

router = APIRouter(prefix="/api/v1/properties", tags=["properties"])

class PropertyCreate(BaseModel):
    address: str
    city: str
    state: str
    zip: str
    price: float
    bedrooms: int
    bathrooms: float
    sqft: int
    property_type: str

class PropertyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    address: str
    city: str
    state: str
    zip: str
    price: float
    bedrooms: int
    bathrooms: float
    sqft: int
    property_type: str
    status: str

@router.post("/", response_model=PropertyResponse)
async def create_property(
    property_data: PropertyCreate,
    user: User = Depends(get_current_user)
):
    """Create a new property."""
    with get_db_session(user.tenant_id) as session:
        # Insert property
        result = session.execute(
            text("""
                INSERT INTO properties (
                    tenant_id, address, city, state, zip,
                    price, bedrooms, bathrooms, sqft, property_type
                ) VALUES (
                    :tenant_id, :address, :city, :state, :zip,
                    :price, :bedrooms, :bathrooms, :sqft, :property_type
                )
                RETURNING *
            """),
            {
                "tenant_id": user.tenant_id,
                **property_data.dict()
            }
        )
        property_row = result.fetchone()
        return PropertyResponse(**dict(property_row))

@router.get("/", response_model=List[PropertyResponse])
async def list_properties(
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user)
):
    """List properties for the current tenant."""
    with get_db_session(user.tenant_id) as session:
        result = session.execute(
            text("""
                SELECT * FROM properties
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset}
        )
        properties = [PropertyResponse(**dict(row)) for row in result]
        return properties

@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: UUID,
    user: User = Depends(get_current_user)
):
    """Get a single property."""
    with get_db_session(user.tenant_id) as session:
        result = session.execute(
            text("SELECT * FROM properties WHERE id = :id"),
            {"id": property_id}
        )
        property_row = result.fetchone()
        
        if not property_row:
            raise HTTPException(status_code=404, detail="Property not found")
        
        return PropertyResponse(**dict(property_row))

@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    property_data: PropertyCreate,
    user: User = Depends(get_current_user)
):
    """Update a property."""
    with get_db_session(user.tenant_id) as session:
        result = session.execute(
            text("""
                UPDATE properties
                SET address = :address, city = :city, state = :state,
                    zip = :zip, price = :price, bedrooms = :bedrooms,
                    bathrooms = :bathrooms, sqft = :sqft,
                    property_type = :property_type,
                    updated_at = NOW()
                WHERE id = :id
                RETURNING *
            """),
            {
                "id": property_id,
                **property_data.dict()
            }
        )
        property_row = result.fetchone()
        
        if not property_row:
            raise HTTPException(status_code=404, detail="Property not found")
        
        return PropertyResponse(**dict(property_row))

@router.delete("/{property_id}", status_code=204)
async def delete_property(
    property_id: UUID,
    user: User = Depends(get_current_user)
):
    """Soft-delete a property."""
    with get_db_session(user.tenant_id) as session:
        session.execute(
            text("""
                UPDATE properties
                SET status = 'deleted', updated_at = NOW()
                WHERE id = :id
            """),
            {"id": property_id}
        )
```

**Deliverables**:
- ✅ Property CRUD endpoints
- ✅ Tenant isolation via RLS
- ✅ Input validation
- ✅ Error handling
- ✅ API documentation

**Acceptance Criteria**:
- [ ] All CRUD operations work
- [ ] RLS prevents cross-tenant access
- [ ] Proper HTTP status codes
- [ ] API docs auto-generated

---

## PHASE 2: CORE FUNCTIONALITY (Weeks 4-7)
**Goal**: Implement essential business logic  
**Priority**: P0-P1

### Week 4-5: Real ML Model Integration

**Task 4.1: Qdrant Integration**
```python
# File: ml/vector_store.py

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
import numpy as np
from typing import List, Dict
import os

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
        self.collection = "property_embeddings"
    
    def search_similar(
        self,
        vector: List[float],
        tenant_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """Search for similar properties within tenant."""
        results = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id)
                    )
                ]
            ),
            limit=limit
        )
        return [
            {
                "id": hit.id,
                "score": hit.score,
                **hit.payload
            }
            for hit in results
        ]
```

**Task 4.2: Replace Mock Implementations**
- Update comp_critic.py to use Qdrant
- Load actual trained model artifacts
- Implement real feature engineering
- Add proper error handling

**Deliverables**:
- ✅ Qdrant client integration
- ✅ Real vector search
- ✅ Model artifact loading
- ✅ Feature engineering pipeline

---

### Week 6-7: Complete Data Pipelines

**Task 6.1: Property Processing Pipeline**
```python
# File: dags/property_processing_pipeline_v2.py

from airflow import DAG
from airflow.decorators import task
from datetime import datetime, timedelta

with DAG(
    dag_id='property_processing_pipeline_v2',
    start_date=datetime(2024, 11, 1),
    schedule_interval='@hourly',
    catchup=False
) as dag:
    
    @task
    def extract_new_properties():
        """Extract properties from prospect_queue."""
        # Real implementation
        pass
    
    @task
    def normalize_addresses(properties):
        """Normalize addresses using libpostal."""
        from address_normalization import LibpostalClient
        client = LibpostalClient()
        # Real implementation
        return normalized_properties
    
    @task
    def enrich_with_hazards(properties):
        """Add hazard assessments."""
        from hazards import hazards_etl
        # Real implementation
        return enriched_properties
    
    @task
    def validate_quality(properties):
        """Validate with Great Expectations."""
        import great_expectations as gx
        # Real implementation
        return validation_results
    
    @task
    def load_to_properties(properties):
        """Load to properties table."""
        # Real implementation
        return load_stats
    
    # Define dependencies
    props = extract_new_properties()
    normalized = normalize_addresses(props)
    enriched = enrich_with_hazards(normalized)
    validated = validate_quality(enriched)
    loaded = load_to_properties(enriched)
```

**Deliverables**:
- ✅ Complete property processing DAG
- ✅ Enrichment DAG
- ✅ Score master DAG
- ✅ GX integration in all DAGs

---

## PHASE 3: TESTING & QUALITY (Weeks 8-10)
**Goal**: Achieve 70%+ test coverage  
**Priority**: P0

### Week 8: Unit Tests

**Task 8.1: API Tests**
```python
# File: tests/backend/test_api_comprehensive.py

import pytest
from fastapi.testclient import TestClient
from api.main import app
from uuid import uuid4

client = TestClient(app)

class TestPropertiesAPI:
    def test_create_property(self, auth_headers):
        response = client.post(
            "/api/v1/properties/",
            json={
                "address": "123 Main St",
                "city": "Austin",
                "state": "TX",
                "zip": "78701",
                "price": 500000,
                "bedrooms": 3,
                "bathrooms": 2.0,
                "sqft": 1800,
                "property_type": "single_family"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["address"] == "123 Main St"
        assert "id" in data
    
    def test_list_properties(self, auth_headers):
        response = client.get(
            "/api/v1/properties/",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_tenant_isolation(self, auth_headers_tenant_a, auth_headers_tenant_b):
        # Create property as tenant A
        response_a = client.post(
            "/api/v1/properties/",
            json={"address": "Tenant A Property", ...},
            headers=auth_headers_tenant_a
        )
        property_id = response_a.json()["id"]
        
        # Try to access as tenant B (should fail)
        response_b = client.get(
            f"/api/v1/properties/{property_id}",
            headers=auth_headers_tenant_b
        )
        assert response_b.status_code == 404
    
    def test_rate_limiting(self):
        # Send 101 requests (limit is 100/min)
        for i in range(101):
            response = client.get("/api/v1/health")
            if i < 100:
                assert response.status_code == 200
            else:
                assert response.status_code == 429
                assert "Retry-After" in response.headers
```

**Target**: 50+ test cases for API

---

### Week 9: Integration Tests

**Task 9.1: Database Tests**
```python
# File: tests/backend/test_database.py

import pytest
from sqlalchemy import text
from api.db_context import get_db_session
from uuid import uuid4

class TestRLS:
    def test_rls_isolation(self, db_session):
        tenant_a = str(uuid4())
        tenant_b = str(uuid4())
        
        # Insert as tenant A
        with get_db_session(tenant_a) as session:
            session.execute(
                text("""
                    INSERT INTO properties (tenant_id, address, city, state, zip, price)
                    VALUES (:tenant_id, '123 Main', 'Austin', 'TX', '78701', 500000)
                """),
                {"tenant_id": tenant_a}
            )
        
        # Query as tenant B (should see nothing)
        with get_db_session(tenant_b) as session:
            result = session.execute(text("SELECT * FROM properties"))
            assert result.rowcount == 0
        
        # Query as tenant A (should see 1)
        with get_db_session(tenant_a) as session:
            result = session.execute(text("SELECT * FROM properties"))
            assert result.rowcount == 1
```

**Target**: 30+ integration tests

---

### Week 10: Security & Performance Tests

**Task 10.1: Security Tests**
```python
# File: tests/security/test_authentication.py

def test_no_token_rejected():
    response = client.get("/api/v1/properties/")
    assert response.status_code == 401

def test_invalid_token_rejected():
    response = client.get(
        "/api/v1/properties/",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

def test_expired_token_rejected():
    # Test with expired token
    pass

def test_sql_injection_prevented():
    # Test SQL injection attempts
    pass
```

**Task 10.2: Performance Tests**
```python
# File: tests/performance/test_api_performance.py

import pytest
from locust import HttpUser, task, between

class PropertyAPIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def list_properties(self):
        self.client.get(
            "/api/v1/properties/",
            headers=self.auth_headers
        )
    
    @task(3)
    def get_property(self):
        self.client.get(
            f"/api/v1/properties/{self.property_id}",
            headers=self.auth_headers
        )

# Run: locust -f test_api_performance.py
# Target: P95 < 200ms for list, P95 < 50ms for get
```

**Deliverables**:
- ✅ 100+ unit tests
- ✅ 30+ integration tests
- ✅ 20+ security tests
- ✅ Performance benchmarks
- ✅ 70%+ code coverage

---

## PHASE 4: OBSERVABILITY & DEPLOYMENT (Weeks 11-12)
**Goal**: Production-ready deployment  
**Priority**: P1

### Week 11: Observability Deployment

**Task 11.1: Deploy Prometheus + Grafana**
```yaml
# File: infra/docker-compose.monitoring.yml

version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
  
  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=redis-datasource
  
  sentry:
    image: sentry:latest
    ports:
      - "9000:9000"
    environment:
      SENTRY_SECRET_KEY: ${SENTRY_SECRET_KEY}
      SENTRY_POSTGRES_HOST: postgres
      SENTRY_REDIS_HOST: redis

volumes:
  prometheus_data:
  grafana_data:
```

**Task 11.2: Configure Actual Metrics**
```python
# File: api/metrics.py

from prometheus_client import Counter, Histogram, Gauge
import time

# Request metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Business metrics
properties_total = Gauge(
    'properties_total',
    'Total number of properties',
    ['tenant_id', 'status']
)

ml_predictions_total = Counter(
    'ml_predictions_total',
    'Total ML predictions',
    ['model', 'tenant_id']
)

# Middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```

---

### Week 12: Production Deployment

**Task 12.1: Infrastructure as Code**
```terraform
# File: infra/terraform/main.tf

resource "aws_rds_cluster" "postgres" {
  cluster_identifier      = "real-estate-os-db"
  engine                  = "aurora-postgresql"
  engine_version          = "14.6"
  database_name           = "real_estate_os"
  master_username         = var.db_username
  master_password         = var.db_password
  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"
  
  serverlessv2_scaling_configuration {
    max_capacity = 16.0
    min_capacity = 0.5
  }
}

resource "aws_ecs_cluster" "main" {
  name = "real-estate-os-cluster"
}

resource "aws_ecs_task_definition" "api" {
  family                   = "real-estate-os-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  
  container_definitions = jsonencode([{
    name  = "api"
    image = "real-estate-os/api:latest"
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    environment = [
      { name = "DATABASE_URL", value = aws_rds_cluster.postgres.endpoint },
      { name = "QDRANT_HOST", value = aws_ecs_service.qdrant.name }
    ]
  }])
}
```

**Task 12.2: CI/CD Pipeline**
```yaml
# File: .github/workflows/deploy.yml

name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/ --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t real-estate-os/api:${{ github.sha }} .
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker push real-estate-os/api:${{ github.sha }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster real-estate-os-cluster \
            --service api \
            --force-new-deployment
```

**Deliverables**:
- ✅ Prometheus deployed and collecting metrics
- ✅ Grafana dashboards operational
- ✅ Sentry capturing errors
- ✅ Infrastructure as Code (Terraform)
- ✅ CI/CD pipeline functional
- ✅ Production deployment successful

---

## SUCCESS CRITERIA

### Platform Readiness Checklist:

**Database & Infrastructure** (100%):
- [x] Base schema created with all tables
- [x] RLS policies on all tables
- [x] Migrations applied successfully
- [x] Indexes optimized
- [x] Backups configured

**Security** (100%):
- [x] JWT authentication working
- [x] Multi-tenant isolation verified
- [x] Rate limiting functional
- [x] No SQL injection vulnerabilities
- [x] Security tests passing

**API** (100%):
- [x] All CRUD endpoints implemented
- [x] Input validation working
- [x] Error handling comprehensive
- [x] API documentation auto-generated
- [x] Performance targets met (P95 < 200ms)

**ML Models** (100%):
- [x] Qdrant integration complete
- [x] Real model artifacts loaded
- [x] Predictions working
- [x] Feature engineering pipeline
- [x] Model monitoring active

**Data Pipelines** (100%):
- [x] All DAGs implemented (not stubs)
- [x] GX validation integrated
- [x] OpenLineage tracking
- [x] Error handling and retries
- [x] Monitoring and alerting

**Testing** (70%+ coverage):
- [x] 100+ unit tests
- [x] 30+ integration tests
- [x] 20+ security tests
- [x] Performance benchmarks
- [x] All tests passing in CI

**Observability** (100%):
- [x] Prometheus collecting metrics
- [x] Grafana dashboards live
- [x] Sentry capturing errors
- [x] Logs aggregated
- [x] Alerts configured

**Deployment** (100%):
- [x] Infrastructure as Code
- [x] CI/CD pipeline
- [x] Production deployment
- [x] Rollback procedure tested
- [x] Disaster recovery plan

---

## RESOURCE REQUIREMENTS

### Team Composition:
- 1 Senior Backend Engineer (database, API, security)
- 1 ML Engineer (model integration, pipelines)
- 0.5 DevOps Engineer (infrastructure, deployment)
- 0.5 QA Engineer (testing, automation)

### Infrastructure Costs (estimated monthly):
- Database (Aurora Serverless): $100-300
- Compute (ECS Fargate): $200-500
- Vector DB (Qdrant Cloud): $100-200
- Monitoring (Prometheus + Grafana Cloud): $50-100
- Error Tracking (Sentry): $50
- **Total**: $500-1,150/month

### Timeline by Phase:
- Phase 1 (Foundation): 3 weeks
- Phase 2 (Functionality): 4 weeks
- Phase 3 (Testing): 3 weeks
- Phase 4 (Deployment): 2 weeks
- **Total**: 12 weeks

---

## RISK MITIGATION

### Technical Risks:
1. **Risk**: Database migration issues
   - **Mitigation**: Test migrations on staging first
   - **Rollback**: Keep migration scripts reversible

2. **Risk**: Performance degradation with RLS
   - **Mitigation**: Benchmark early, optimize indexes
   - **Fallback**: Application-level filtering if needed

3. **Risk**: ML model accuracy in production
   - **Mitigation**: A/B testing, gradual rollout
   - **Monitoring**: Track prediction quality metrics

### Schedule Risks:
1. **Risk**: Delays in testing phase
   - **Mitigation**: Start writing tests early
   - **Buffer**: 2-week buffer built into timeline

2. **Risk**: Integration issues
   - **Mitigation**: Weekly integration tests
   - **Catch-up**: Weekend sprints if needed

---

## FINAL RECOMMENDATION

**Commit to this roadmap** if you want a production-ready platform.

The current state (35% complete) cannot be deployed to production.
This roadmap provides a realistic path to 95%+ completion in 12 weeks.

**Key Success Factors**:
1. **Honest assessment** of current gaps
2. **Dedicated team** focused on completion
3. **Incremental progress** with weekly milestones
4. **Comprehensive testing** (no shortcuts)
5. **Production deployment** as the goal

**Alternative**: If 12 weeks is too long, prioritize:
1. Database + Security (Weeks 1-3)
2. Core API (Week 3)
3. One working pipeline (Week 4-5)
4. Basic tests (Week 6)
5. Minimal deployment (Week 7)

This gets you to **50% complete** in 7 weeks—enough for a beta launch.

---

*End of Roadmap*
