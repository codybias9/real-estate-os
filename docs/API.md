# Real Estate OS - API Documentation

Base URL: `http://localhost:8000/v1`

## Table of Contents

1. [Authentication](#authentication)
2. [Properties](#properties)
3. [Timeline](#timeline)
4. [Health & Metrics](#health--metrics)

---

## Authentication

### Login

```http
POST /v1/auth/login
Content-Type: application/json

{
  "email": "analyst@example.com",
  "password": "password123"
}
```

**Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Refresh Token

```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Get Current User

```http
GET /v1/auth/me
Authorization: Bearer <access_token>
```

**Response (200 OK)**:
```json
{
  "id": "user-123",
  "tenant_id": "tenant-456",
  "email": "analyst@example.com",
  "full_name": "Jane Analyst",
  "role": "Analyst"
}
```

### Logout

```http
POST /v1/auth/logout
Authorization: Bearer <access_token>
```

**Response (200 OK)**:
```json
{
  "message": "Successfully logged out"
}
```

---

## Properties

### List Properties

```http
GET /v1/properties?page=1&page_size=50&state=scored
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `page` (integer, default: 1) - Page number
- `page_size` (integer, default: 50, max: 100) - Items per page
- `state` (string, optional) - Filter by property state
  - Values: `discovered`, `enriched`, `scored`, `memo_generated`, `outreach_pending`, `contacted`, `responded`, `archived`

**Response (200 OK)**:
```json
{
  "properties": [
    {
      "id": "prop-123",
      "tenant_id": "tenant-456",
      "apn": "123-456-789",
      "apn_hash": "abc123...",
      "street": "123 Main St",
      "city": "Los Angeles",
      "state": "CA",
      "zip": "90001",
      "county": "Los Angeles",
      "lat": 34.0522,
      "lng": -118.2437,
      "beds": 3,
      "baths": 2.0,
      "sqft": 1500,
      "lot_sqft": 5000,
      "year_built": 1950,
      "state": "scored",
      "score": 85.5,
      "created_at": "2025-11-03T00:00:00Z",
      "updated_at": "2025-11-03T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50
}
```

**Cache**: 5 minutes

### Get Property

```http
GET /v1/properties/{property_id}
Authorization: Bearer <access_token>
```

**Response (200 OK)**:
```json
{
  "id": "prop-123",
  "tenant_id": "tenant-456",
  "apn": "123-456-789",
  "street": "123 Main St",
  "city": "Los Angeles",
  "state": "CA",
  "zip": "90001",
  "county": "Los Angeles",
  "lat": 34.0522,
  "lng": -118.2437,
  "beds": 3,
  "baths": 2.0,
  "sqft": 1500,
  "lot_sqft": 5000,
  "year_built": 1950,
  "state": "scored",
  "score": 85.5,
  "score_reasons": [
    {
      "factor": "location",
      "score": 90,
      "reason": "Prime downtown location"
    },
    {
      "factor": "condition",
      "score": 80,
      "reason": "Well-maintained property"
    }
  ],
  "created_at": "2025-11-03T00:00:00Z",
  "updated_at": "2025-11-03T00:00:00Z"
}
```

**Cache**: 10 minutes

**Errors**:
- `404 Not Found` - Property does not exist

### Create Property

```http
POST /v1/properties
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "apn": "123-456-789",
  "street": "123 Main St",
  "city": "Los Angeles",
  "state": "CA",
  "zip": "90001",
  "county": "Los Angeles"
}
```

**Required Role**: Analyst, Admin

**Response (201 Created)**:
```json
{
  "id": "prop-123",
  "tenant_id": "tenant-456",
  "apn": "123-456-789",
  "apn_hash": "abc123...",
  "street": "123 Main St",
  "city": "Los Angeles",
  "state": "CA",
  "zip": "90001",
  "county": "Los Angeles",
  "state": "discovered",
  "created_at": "2025-11-03T00:00:00Z",
  "updated_at": "2025-11-03T00:00:00Z"
}
```

**Side Effects**:
- Publishes `property.created` event
- Invalidates property list cache

### Update Property

```http
PUT /v1/properties/{property_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "street": "123 Main Street",
  "beds": 4,
  "baths": 2.5,
  "sqft": 1800
}
```

**Required Role**: Analyst, Admin, Ops

**Response (200 OK)**:
```json
{
  "id": "prop-123",
  "tenant_id": "tenant-456",
  "apn": "123-456-789",
  "street": "123 Main Street",
  "city": "Los Angeles",
  "state": "CA",
  "beds": 4,
  "baths": 2.5,
  "sqft": 1800,
  "updated_at": "2025-11-03T01:00:00Z"
}
```

**Side Effects**:
- Publishes `property.updated` event
- Invalidates property cache (detail, score, lists)

### Delete Property

```http
DELETE /v1/properties/{property_id}
Authorization: Bearer <access_token>
```

**Required Role**: Admin

**Response (204 No Content)**

**Side Effects**:
- Publishes `property.deleted` event
- Invalidates property cache

### Get Property Score

```http
GET /v1/properties/{property_id}/score
Authorization: Bearer <access_token>
```

**Response (200 OK)**:
```json
{
  "property_id": "prop-123",
  "score": 85.5,
  "reasons": [
    {
      "factor": "location",
      "score": 90,
      "weight": 0.4,
      "reason": "Prime downtown location with high foot traffic"
    },
    {
      "factor": "condition",
      "score": 80,
      "weight": 0.3,
      "reason": "Well-maintained with recent renovations"
    },
    {
      "factor": "price",
      "score": 85,
      "weight": 0.3,
      "reason": "Priced 10% below market average"
    }
  ],
  "calculated_at": "2025-11-03T00:00:00Z"
}
```

**Cache**: 30 minutes

### Invalidate Property Cache (Admin)

```http
POST /v1/properties/{property_id}/cache/invalidate
Authorization: Bearer <access_token>
```

**Required Role**: Admin

**Response (204 No Content)**

---

## Timeline

### Get Timeline

```http
GET /v1/timeline/{property_id}
Authorization: Bearer <access_token>
```

**Response (200 OK)**:
```json
{
  "property_id": "prop-123",
  "events": [
    {
      "id": "event-1",
      "event_type": "comment",
      "user_id": "user-123",
      "user_name": "Jane Analyst",
      "content": "This property looks promising",
      "timestamp": "2025-11-03T10:30:00Z",
      "metadata": {}
    },
    {
      "id": "event-2",
      "event_type": "state_change",
      "user_id": "system",
      "user_name": "System",
      "content": "Property state changed to scored",
      "timestamp": "2025-11-03T10:00:00Z",
      "metadata": {
        "old_state": "enriched",
        "new_state": "scored"
      }
    }
  ]
}
```

### Add Comment

```http
POST /v1/timeline/{property_id}/comments
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "This property looks promising. Let's schedule a viewing."
}
```

**Response (201 Created)**:
```json
{
  "id": "event-1",
  "event_type": "comment",
  "user_id": "user-123",
  "user_name": "Jane Analyst",
  "content": "This property looks promising. Let's schedule a viewing.",
  "timestamp": "2025-11-03T10:30:00Z"
}
```

**Side Effects**:
- Broadcasts via SSE to all connected clients
- Publishes `timeline.comment_added` event
- Invalidates timeline cache

### Add Note

```http
POST /v1/timeline/{property_id}/notes
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "Owner interested in selling. Follow up next week.",
  "tags": ["follow-up", "interested"]
}
```

**Response (201 Created)**:
```json
{
  "id": "event-2",
  "event_type": "note",
  "user_id": "user-123",
  "user_name": "Jane Analyst",
  "content": "Owner interested in selling. Follow up next week.",
  "tags": ["follow-up", "interested"],
  "timestamp": "2025-11-03T10:35:00Z"
}
```

### Subscribe to Timeline (SSE)

```http
GET /v1/timeline/{property_id}/stream
Authorization: Bearer <access_token>
Accept: text/event-stream
```

**Response (200 OK, streaming)**:
```
event: comment
data: {"id":"event-1","event_type":"comment","user_id":"user-123","user_name":"Jane Analyst","content":"This property looks promising","timestamp":"2025-11-03T10:30:00Z"}

event: note
data: {"id":"event-2","event_type":"note","user_id":"user-456","user_name":"John Underwriter","content":"Approved for outreach","timestamp":"2025-11-03T10:35:00Z"}

event: state_change
data: {"id":"event-3","event_type":"state_change","content":"Property state changed to contacted","metadata":{"old_state":"memo_generated","new_state":"contacted"},"timestamp":"2025-11-03T10:40:00Z"}
```

**Connection**: Long-lived, auto-reconnects on disconnect

---

## Health & Metrics

### Health Check

```http
GET /v1/health
```

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-03T00:00:00Z",
  "checks": {
    "database": "healthy",
    "cache": "healthy",
    "vector_db": "healthy"
  }
}
```

### Database Health

```http
GET /v1/health/db
```

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "database": "postgresql",
  "connections": {
    "active": 5,
    "max": 100
  },
  "latency_ms": 2.5
}
```

### Prometheus Metrics

```http
GET /metrics
```

**Response (200 OK, text/plain)**:
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/v1/properties",status_code="200"} 1234

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/v1/properties",le="0.1"} 980
http_request_duration_seconds_bucket{method="GET",endpoint="/v1/properties",le="0.5"} 1200
http_request_duration_seconds_bucket{method="GET",endpoint="/v1/properties",le="+Inf"} 1234
http_request_duration_seconds_sum{method="GET",endpoint="/v1/properties"} 125.5
http_request_duration_seconds_count{method="GET",endpoint="/v1/properties"} 1234

# HELP property_operations_total Total property operations
# TYPE property_operations_total counter
property_operations_total{operation="create",status="success"} 50
property_operations_total{operation="list",status="success"} 1000
property_operations_total{operation="get",status="success"} 800
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid input: APN must be in format XXX-XXX-XXX"
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden

```json
{
  "detail": "Insufficient permissions. Required role: Admin"
}
```

### 404 Not Found

```json
{
  "detail": "Property not found"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

### 500 Internal Server Error

```json
{
  "detail": "An unexpected error occurred",
  "error_id": "err-abc123"
}
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/v1/auth/login` | 5 requests | 1 minute |
| `/v1/properties` (GET) | 100 requests | 1 minute |
| `/v1/properties` (POST) | 20 requests | 1 minute |
| `/v1/timeline/*` | 50 requests | 1 minute |
| Global default | 1000 requests | 1 hour |

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699000000
```

---

## Authentication

All endpoints (except `/health` and `/metrics`) require authentication via JWT bearer token.

**Header**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Token Lifetime**:
- Access Token: 30 minutes
- Refresh Token: 7 days

**Refresh Flow**:
1. Access token expires (401 response)
2. Client uses refresh token to get new access token
3. Retry original request with new access token

---

## Pagination

List endpoints support pagination:

**Request**:
```http
GET /v1/properties?page=2&page_size=25
```

**Response Headers**:
```
X-Total-Count: 100
X-Page: 2
X-Page-Size: 25
X-Total-Pages: 4
```

---

## Versioning

API version is specified in the URL path: `/v1/`

Breaking changes will increment the version number: `/v2/`

---

## OpenAPI Specification

Interactive API documentation available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## License

MIT License - Real Estate OS
