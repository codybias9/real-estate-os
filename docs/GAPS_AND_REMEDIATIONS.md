# Gaps and Remediations

This document tracks all identified gaps with clear ownership, remediation steps, and acceptance criteria.

**Last Updated**: 2024-11-02
**Status**: 8 gaps documented

---

## GAP-001: API JWT Middleware Integration

**Category**: Security / AuthN/Z
**Priority**: P0 (High)
**Owner**: Backend Team

### Current State
- Keycloak realm configured with clients and roles
- JWT tokens can be issued
- API endpoints do NOT yet enforce JWT validation

### Remediation Steps
1. Install `python-jose[cryptography]` and `python-multipart`
2. Create FastAPI dependency for JWT validation:
   ```python
   from fastapi import Depends, HTTPException, status
   from fastapi.security import OAuth2PasswordBearer
   from jose import JWTError, jwt

   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

   async def get_current_user(token: str = Depends(oauth2_scheme)):
       # Validate JWT, extract claims
       # Raise HTTPException(401) if invalid
       pass
   ```
3. Apply to all `/api/*` routes:
   ```python
   @app.get("/api/properties", dependencies=[Depends(get_current_user)])
   ```
4. Add integration tests for:
   - Request without token → 401
   - Request with invalid token → 401
   - Request with valid token → 200

### Acceptance Criteria
- [ ] All `/api/*` routes enforce JWT
- [ ] Tests pass: no token → 401
- [ ] Tests pass: invalid token → 401
- [ ] Tests pass: valid token → 200
- [ ] `/healthz` endpoint remains unauthenticated
- [ ] Documentation updated

### Test Plan
```python
def test_api_requires_jwt():
    response = client.get("/api/properties")
    assert response.status_code == 401

def test_api_with_valid_jwt():
    token = get_test_jwt()
    response = client.get("/api/properties", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
```

---

## GAP-002: Rate Limiting Middleware

**Category**: Security / API Protection
**Priority**: P1 (Medium-High)
**Owner**: Backend Team

### Current State
- No rate limiting on API endpoints
- Vulnerable to abuse

### Remediation Steps
1. Install `slowapi` package
2. Configure rate limiter:
   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   from slowapi.errors import RateLimitExceeded

   limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```
3. Apply rate limits per endpoint:
   ```python
   @app.get("/api/score")
   @limiter.limit("10/minute")
   async def score_property(...):
       pass
   ```
4. Ensure 429 response includes `Retry-After` header

### Acceptance Criteria
- [ ] Rate limiter installed and configured
- [ ] 429 status code returned when limit exceeded
- [ ] `Retry-After` header present in 429 response
- [ ] Different limits for different endpoint classes
- [ ] Redis backend for distributed rate limiting (production)
- [ ] Tests verify rate limit enforcement

### Test Plan
```python
def test_rate_limit_enforced():
    for i in range(15):
        response = client.get("/api/score/DEMO123")
        if i < 10:
            assert response.status_code == 200
        else:
            assert response.status_code == 429
            assert "Retry-After" in response.headers
```

---

## GAP-003: Multi-Tenant Isolation Tests

**Category**: Security / Data Isolation
**Priority**: P0 (High)
**Owner**: Backend + QA Teams

### Current State
- Tenant ID concept exists in data model
- No negative tests to verify isolation

### Remediation Steps
1. Add tenant_id to JWT claims
2. Implement tenant filtering in all DB queries:
   ```python
   def get_properties(tenant_id: str, db: Session):
       return db.query(Property).filter(Property.tenant_id == tenant_id).all()
   ```
3. Create negative tests:
   ```python
   def test_tenant_a_cannot_access_tenant_b_data():
       # Tenant A JWT
       token_a = get_jwt_for_tenant("tenant-a")
       # Try to access tenant B resource
       response = client.get(
           "/api/properties/tenant-b-property-id",
           headers={"Authorization": f"Bearer {token_a}"}
       )
       assert response.status_code == 404  # Not 403, to avoid information leak
   ```
4. Test isolation across:
   - PostgreSQL (property data)
   - Qdrant (vectors)
   - MinIO (documents)
   - Redis (cache)

### Acceptance Criteria
- [ ] All queries filtered by tenant_id
- [ ] Negative tests pass for all data stores
- [ ] Tenant ID extracted from JWT claims
- [ ] 404 (not 403) returned for cross-tenant access attempts
- [ ] Audit log for any cross-tenant access attempts
- [ ] Integration tests cover all 4 data stores

### Test Plan
```python
class TestMultiTenantIsolation:
    def test_postgres_isolation(self):
        # Tenant A cannot query Tenant B properties
        pass

    def test_qdrant_isolation(self):
        # Tenant A cannot search Tenant B vectors
        pass

    def test_minio_isolation(self):
        # Tenant A cannot access Tenant B documents
        pass

    def test_redis_isolation(self):
        # Tenant A cache doesn't leak to Tenant B
        pass
```

---

## GAP-004: Great Expectations Full Integration

**Category**: Data Quality
**Priority**: P1 (Medium-High)
**Owner**: Data Engineering Team

### Current State
- GX expectation suites defined in documentation
- Not yet integrated into Airflow DAGs

### Remediation Steps
1. Install Great Expectations: `pip install great-expectations`
2. Initialize GX project: `great_expectations init`
3. Create expectation suites in `libs/data_quality/gx/expectations/`
4. Configure checkpoints in `libs/data_quality/gx/checkpoints/`
5. Integrate into Airflow:
   ```python
   from great_expectations.data_context import DataContext

   def validate_data(**context):
       ge_context = DataContext("/path/to/gx")
       result = ge_context.run_checkpoint(
           checkpoint_name="properties_ingress",
           batch_request={"datasource_name": "postgres", "data_asset_name": "properties"}
       )
       if not result.success:
           raise AirflowException("Data quality check failed")
   ```
6. Add pre-enrichment and pre-ML validation gates

### Acceptance Criteria
- [ ] GX project initialized in `libs/data_quality/gx/`
- [ ] 5 expectation suites created (properties, ownership, leases, outreach, market)
- [ ] Checkpoints configured for ingress and pre-ML
- [ ] Integration with Airflow DAGs
- [ ] Failed validations block downstream tasks
- [ ] Data Docs published to artifacts/data-quality/
- [ ] Example of failed checkpoint with clear error message

### Test Plan
```python
def test_gx_validation_blocks_pipeline():
    # Inject bad data (e.g., null property_id)
    # Run DAG
    # Assert validation task fails
    # Assert downstream tasks not executed
```

---

## GAP-005: OpenLineage + Marquez Deployment

**Category**: Data Lineage
**Priority**: P2 (Medium)
**Owner**: Data Engineering Team

### Current State
- Lineage graph documented
- Marquez not deployed

### Remediation Steps
1. Deploy Marquez using Docker:
   ```yaml
   # docker-compose.yml
   services:
     marquez:
       image: marquezproject/marquez:latest
       ports:
         - "5000:5000"
         - "5001:5001"
       environment:
         - MARQUEZ_PORT=5000
         - MARQUEZ_ADMIN_PORT=5001
   ```
2. Install OpenLineage Airflow integration:
   ```python
   pip install openlineage-airflow
   ```
3. Configure Airflow to emit lineage:
   ```python
   # airflow.cfg or env
   [lineage]
   backend = openlineage.lineage_backend.OpenLineageBackend
   openlineage_url = http://marquez:5000
   ```
4. Verify lineage for end-to-end pipeline

### Acceptance Criteria
- [ ] Marquez deployed and accessible
- [ ] Airflow emitting lineage events
- [ ] DAG visualization in Marquez UI
- [ ] Dataset lineage graph complete (discovery → outreach)
- [ ] Screenshot of lineage graph saved to artifacts/
- [ ] Lineage URL accessible

---

## GAP-006: libpostal Address Normalization

**Category**: Data Quality / Geospatial
**Priority**: P2 (Medium)
**Owner**: Data Engineering Team

### Current State
- Addresses stored as-is
- No normalization

### Remediation Steps
1. Deploy libpostal service:
   ```yaml
   services:
     libpostal:
       image: openvenues/libpostal-rest-docker
       ports:
         - "8080:8080"
   ```
2. Create normalization function:
   ```python
   import requests

   def normalize_address(raw_address: str) -> dict:
       response = requests.post(
           "http://libpostal:8080/parser",
           json={"query": raw_address}
       )
       return response.json()
   ```
3. Integrate into enrichment pipeline:
   ```python
   @task
   def enrich_property(property_data):
       normalized = normalize_address(property_data["raw_address"])
       property_data["normalized_address"] = normalized
       return property_data
   ```

### Acceptance Criteria
- [ ] libpostal service deployed
- [ ] Address normalization integrated in enrichment DAG
- [ ] Normalized fields: house_number, street, city, state, zip
- [ ] 95%+ addresses successfully parsed
- [ ] Validation tests for various address formats

---

## GAP-007: Lease/Rent-Roll Parsing (Tika + Unstructured)

**Category**: Document Processing
**Priority**: P2 (Medium)
**Owner**: ML/Document Team

### Current State
- Lease parsing not implemented

### Remediation Steps
1. Deploy Apache Tika:
   ```yaml
   services:
     tika:
       image: apache/tika:latest
       ports:
         - "9998:9998"
   ```
2. Install Unstructured: `pip install unstructured[pdf]`
3. Create parsing pipeline:
   ```python
   from unstructured.partition.pdf import partition_pdf

   def parse_lease(file_path: str) -> dict:
       elements = partition_pdf(file_path, url="http://tika:9998")
       # Extract structured data (tenant, rent, dates, etc.)
       return extracted_data
   ```
4. Implement conflict resolution:
   - If multiple values found, flag for manual review
5. Create validation dataset with ground truth

### Acceptance Criteria
- [ ] Tika and Unstructured deployed
- [ ] Parsing pipeline extracts: tenant name, rent amount, lease start/end, sqft, type
- [ ] OCR fallback for scanned documents
- [ ] Conflict resolution flow implemented
- [ ] Accuracy ≥95% on validation dataset (n≥100)
- [ ] `artifacts/leases/accuracy-table.csv` with results
- [ ] Sample parsed JSON for 3 lease types

---

## GAP-008: Hazard Layers Integration

**Category**: Risk Assessment
**Priority**: P2 (Medium)
**Owner**: Data Engineering + ML Team

### Current State
- Hazard data not integrated

### Remediation Steps
1. Integrate FEMA NFHL API:
   ```python
   def get_flood_zone(lat: float, lon: float) -> str:
       # Query FEMA NFHL Web Service
       # Return flood zone designation
       pass
   ```
2. Add wildfire risk data (e.g., USGS, state fire authorities)
3. Add heat risk data (NOAA, local climate)
4. Store hazard attributes on property:
   ```python
   class Property(Base):
       ...
       flood_zone = Column(String)
       wildfire_risk_score = Column(Float)  # 0-1
       heat_index_avg = Column(Float)
   ```
5. Adjust scoring model to factor hazards:
   ```python
   def calculate_score(features):
       base_score = ...
       hazard_penalty = (
           features["flood_zone"] in ["A", "V"] * -0.15 +
           features["wildfire_risk_score"] * -0.10
       )
       return base_score + hazard_penalty
   ```

### Acceptance Criteria
- [ ] FEMA NFHL integration working
- [ ] Wildfire risk data source identified and integrated
- [ ] Heat index data integrated
- [ ] Hazard attributes persisted on properties
- [ ] Scoring model updated with hazard factors
- [ ] `artifacts/hazards/property-<id>-hazard-attrs.json` example
- [ ] UI displays hazard information
- [ ] Documentation of hazard scoring weights

---

## GAP-009: Field-Level Provenance Tracking

**Category**: Data Governance / Trust
**Priority**: P2 (Medium)
**Owner**: Data Engineering Team

### Current State
- Property data stored without provenance metadata

### Remediation Steps
1. Define provenance schema:
   ```python
   class FieldProvenance(Base):
       __tablename__ = "field_provenance"
       id = Column(UUID, primary_key=True)
       entity_type = Column(String)  # "property", "owner", etc.
       entity_id = Column(String)
       field_name = Column(String)
       value = Column(JSONB)
       source_id = Column(String)  # "zillow", "county_records", "manual_entry"
       method = Column(String)  # "api", "scrape", "ocr", "user_input"
       timestamp = Column(DateTime)
       confidence = Column(Float)  # 0-1
       evidence_uri = Column(String)  # Link to source document
   ```
2. Update data ingestion to record provenance:
   ```python
   def ingest_property(data, source_id, method):
       property = Property(**data)
       db.add(property)

       for field_name, value in data.items():
           provenance = FieldProvenance(
               entity_type="property",
               entity_id=property.id,
               field_name=field_name,
               value=value,
               source_id=source_id,
               method=method,
               timestamp=datetime.utcnow(),
               confidence=calculate_confidence(source_id, method),
               evidence_uri=f"s3://evidence/{property.id}/{field_name}"
           )
           db.add(provenance)
   ```
3. Implement trust score formula:
   ```python
   def calculate_trust_score(property_id):
       provenances = db.query(FieldProvenance).filter_by(entity_id=property_id).all()

       # Weighted by field importance
       field_weights = {
           "address": 0.20,
           "owner_name": 0.15,
           "sqft": 0.10,
           # ...
       }

       weighted_confidence = sum(
           p.confidence * field_weights.get(p.field_name, 0.05)
           for p in provenances
       )

       # Bonus for multiple sources agreeing
       multi_source_bonus = calculate_agreement_bonus(provenances)

       return min(1.0, weighted_confidence + multi_source_bonus)
   ```

### Acceptance Criteria
- [ ] `field_provenance` table created
- [ ] All ingestion pipelines record provenance
- [ ] Trust score formula implemented
- [ ] API endpoint: `GET /api/properties/{id}/provenance`
- [ ] `artifacts/provenance/property-<id>-provenance.json` example
- [ ] `artifacts/provenance/trust-score-examples.csv` with 10+ examples
- [ ] UI displays field-level provenance on hover

---

## Remediation Priority Matrix

| Gap | Priority | Effort | Risk if Unresolved | Planned Sprint |
|-----|----------|--------|-------------------|----------------|
| GAP-001 JWT Middleware | P0 | Medium | High (security) | Sprint 1 |
| GAP-002 Rate Limiting | P1 | Low | Medium (abuse) | Sprint 1 |
| GAP-003 Tenant Isolation | P0 | High | Critical (data leak) | Sprint 1 |
| GAP-004 GX Integration | P1 | Medium | Medium (data quality) | Sprint 2 |
| GAP-005 Marquez | P2 | Low | Low (observability) | Sprint 3 |
| GAP-006 libpostal | P2 | Medium | Low (data quality) | Sprint 2 |
| GAP-007 Lease Parsing | P2 | High | Low (feature) | Sprint 3 |
| GAP-008 Hazard Layers | P2 | Medium | Low (risk assessment) | Sprint 3 |
| GAP-009 Provenance | P2 | High | Low (governance) | Sprint 4 |

---

## Sign-Off Process

Each gap must have:
1. ✅ Remediation steps completed
2. ✅ All acceptance criteria met
3. ✅ Tests passing
4. ✅ Documentation updated
5. ✅ Code review approved
6. ✅ Evidence committed to artifacts/

**Sign-off approver**: Tech Lead + Product Owner
