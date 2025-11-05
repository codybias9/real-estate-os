# Manual API Testing Guide - Real Estate OS Platform

This guide provides step-by-step instructions for manually testing the Real Estate OS Platform API using `curl` or any HTTP client (Postman, Insomnia, etc.).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Authentication Flow](#authentication-flow)
4. [Core Features](#core-features)
5. [Advanced Features](#advanced-features)
6. [Error Handling](#error-handling)
7. [Testing with Postman/Insomnia](#testing-with-postmaninsomnia)

---

## Prerequisites

- Docker and docker-compose installed
- `curl` command-line tool
- `jq` for JSON processing (optional but recommended)
- Text editor for viewing responses

## Quick Start

### 1. Start the Platform

```bash
# Navigate to project directory
cd real-estate-os

# Start all services
docker compose up -d

# Wait for services to be healthy (~30 seconds)
sleep 30

# Verify health
curl http://localhost:8000/healthz
# Expected: {"status":"ok"}
```

### 2. Download OpenAPI Specification

```bash
# Get full API documentation
curl http://localhost:8000/docs/openapi.json | jq . > openapi.json

# Count endpoints
jq '.paths | keys | length' openapi.json
# Expected: 118 (Enterprise) or 73 (Basic CRM)

# View all endpoints
jq '.paths | keys' openapi.json
```

### 3. Access Interactive Documentation

Open in browser:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Authentication Flow

### Step 1: Register a New User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "demo@example.com",
    "password": "SecurePass123!",
    "name": "Demo User"
  }' | jq .
```

**Expected Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "demo@example.com",
  "name": "Demo User",
  "is_active": true,
  "created_at": "2025-11-05T20:00:00Z"
}
```

**Notes:**
- Password must be at least 8 characters
- Email must be valid and unique
- Save the `id` for reference

### Step 2: Login to Get JWT Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "demo@example.com",
    "password": "SecurePass123!"
  }' | jq .
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Save the token:**
```bash
# Extract and save token to variable
export TOKEN=$(curl -sS -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"SecurePass123!"}' \
  | jq -r '.access_token')

# Verify token is set
echo $TOKEN
```

### Step 3: Get Current User Profile

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expected Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "demo@example.com",
  "name": "Demo User",
  "is_active": true,
  "role": "user",
  "created_at": "2025-11-05T20:00:00Z"
}
```

---

## Core Features

All subsequent requests require the JWT token in the `Authorization` header.

### Properties Management

#### Create Property

```bash
curl -X POST http://localhost:8000/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "address": "123 Main Street",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94102",
    "price": 1500000,
    "bedrooms": 3,
    "bathrooms": 2.5,
    "square_feet": 2200,
    "property_type": "single_family",
    "status": "active"
  }' | jq .
```

**Response:**
```json
{
  "id": "prop-12345",
  "address": "123 Main Street",
  "city": "San Francisco",
  "state": "CA",
  "zip": "94102",
  "price": 1500000,
  "bedrooms": 3,
  "bathrooms": 2.5,
  "square_feet": 2200,
  "property_type": "single_family",
  "status": "active",
  "created_at": "2025-11-05T20:05:00Z"
}
```

**Save property ID:**
```bash
export PROPERTY_ID="prop-12345"
```

#### List Properties

```bash
# List all properties
curl http://localhost:8000/properties \
  -H "Authorization: Bearer $TOKEN" | jq .

# List with pagination
curl "http://localhost:8000/properties?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Filter by city
curl "http://localhost:8000/properties?city=San%20Francisco" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Get Property Details

```bash
curl http://localhost:8000/properties/$PROPERTY_ID \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Update Property

```bash
curl -X PATCH http://localhost:8000/properties/$PROPERTY_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "price": 1450000,
    "status": "pending"
  }' | jq .
```

#### Delete Property

```bash
curl -X DELETE http://localhost:8000/properties/$PROPERTY_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

### Leads Management

#### Create Lead

```bash
curl -X POST http://localhost:8000/leads \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Jane Smith",
    "email": "jane.smith@example.com",
    "phone": "415-555-0100",
    "source": "website",
    "status": "new",
    "notes": "Interested in 3BR homes in SF"
  }' | jq .
```

**Response:**
```json
{
  "id": "lead-67890",
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "phone": "415-555-0100",
  "source": "website",
  "status": "new",
  "notes": "Interested in 3BR homes in SF",
  "created_at": "2025-11-05T20:10:00Z"
}
```

**Save lead ID:**
```bash
export LEAD_ID="lead-67890"
```

#### List Leads

```bash
# All leads
curl http://localhost:8000/leads \
  -H "Authorization: Bearer $TOKEN" | jq .

# Filter by status
curl "http://localhost:8000/leads?status=new" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Get Lead Details

```bash
curl http://localhost:8000/leads/$LEAD_ID \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Add Lead Activity

```bash
curl -X POST http://localhost:8000/leads/$LEAD_ID/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "call",
    "note": "Initial contact - discussed budget and preferences",
    "outcome": "positive"
  }' | jq .
```

---

### Deals Management

#### Create Deal

```bash
curl -X POST http://localhost:8000/deals \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"lead_id\": \"$LEAD_ID\",
    \"property_id\": \"$PROPERTY_ID\",
    \"status\": \"negotiation\",
    \"value\": 1450000,
    \"notes\": \"Buyer very interested, submitted offer\"
  }" | jq .
```

**Response:**
```json
{
  "id": "deal-abc123",
  "lead_id": "lead-67890",
  "property_id": "prop-12345",
  "status": "negotiation",
  "value": 1450000,
  "notes": "Buyer very interested, submitted offer",
  "created_at": "2025-11-05T20:15:00Z"
}
```

**Save deal ID:**
```bash
export DEAL_ID="deal-abc123"
```

#### Update Deal Status

```bash
curl -X PATCH http://localhost:8000/deals/$DEAL_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "under_contract",
    "notes": "Offer accepted, pending inspection"
  }' | jq .
```

#### Get Deal Details

```bash
curl http://localhost:8000/deals/$DEAL_ID \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## Advanced Features

### Campaigns (Email/SMS Marketing)

#### List Campaign Templates

```bash
curl http://localhost:8000/campaigns/templates \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Create Campaign

```bash
curl -X POST http://localhost:8000/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "New Listing Alert - SF",
    "subject": "New 3BR Home Just Listed!",
    "template_id": "new_listing",
    "recipients": ["jane.smith@example.com"],
    "scheduled_at": "2025-11-06T09:00:00Z"
  }' | jq .
```

#### Check Campaign Status

```bash
curl http://localhost:8000/campaigns/$CAMPAIGN_ID \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

### Analytics Dashboard

#### Get Dashboard Metrics

```bash
curl http://localhost:8000/analytics/dashboard \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expected Response:**
```json
{
  "total_properties": 25,
  "active_properties": 18,
  "total_leads": 142,
  "new_leads_this_week": 12,
  "total_deals": 45,
  "deals_in_progress": 8,
  "closed_deals_this_month": 3,
  "revenue_this_month": 4350000,
  "conversion_rate": 0.317
}
```

#### Get Lead Pipeline

```bash
curl http://localhost:8000/analytics/pipeline \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Get Revenue Trends

```bash
curl http://localhost:8000/analytics/revenue?period=30d \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

### Automation Workflows

#### List Available Workflows

```bash
curl http://localhost:8000/workflows \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Create Workflow

```bash
curl -X POST http://localhost:8000/workflows \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "New Lead Auto-Response",
    "trigger": "lead_created",
    "actions": [
      {
        "type": "send_email",
        "template": "welcome_email",
        "delay_minutes": 0
      },
      {
        "type": "assign_to_agent",
        "agent_id": "agent-123",
        "delay_minutes": 5
      }
    ]
  }' | jq .
```

---

### Real-Time Updates (SSE)

#### Get SSE Token

```bash
curl http://localhost:8000/sse/token \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Response:**
```json
{
  "token": "sse-token-xyz789",
  "expires_at": "2025-11-05T21:00:00Z"
}
```

#### Connect to SSE Stream

```bash
# Open SSE connection (keep terminal open to receive events)
curl -N http://localhost:8000/sse/stream?token=sse-token-xyz789
```

**Expected Output (streaming):**
```
event: lead_created
data: {"id":"lead-99999","name":"New Lead","timestamp":"2025-11-05T20:30:00Z"}

event: deal_updated
data: {"id":"deal-abc123","status":"closed","timestamp":"2025-11-05T20:35:00Z"}
```

---

## Error Handling

### Test 404 Not Found

```bash
curl -i http://localhost:8000/properties/nonexistent-id \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:**
```
HTTP/1.1 404 Not Found
{
  "detail": "Property not found"
}
```

### Test 401 Unauthorized

```bash
# Request without token
curl -i http://localhost:8000/properties
```

**Expected:**
```
HTTP/1.1 401 Unauthorized
{
  "detail": "Not authenticated"
}
```

### Test 422 Validation Error

```bash
curl -X POST http://localhost:8000/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "address": "123 Test St"
  }'
```

**Expected:**
```
HTTP/1.1 422 Unprocessable Entity
{
  "detail": "Validation Error",
  "errors": [
    {
      "loc": ["body", "city"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Test Rate Limiting (429)

```bash
# Send 25 rapid requests to trigger rate limit
for i in {1..25}; do
  curl -X POST http://localhost:8000/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"invalid@test.com","password":"wrong"}'
  sleep 0.1
done
```

**Expected (after ~20 requests):**
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## Testing with Postman/Insomnia

### Postman Collection Setup

1. **Create Collection:** "Real Estate OS API"

2. **Configure Collection Variables:**
   - `base_url`: `http://localhost:8000`
   - `token`: (will be set by login request)

3. **Add Pre-request Script (Collection Level):**
   ```javascript
   // Auto-refresh token if needed
   const token = pm.collectionVariables.get("token");
   if (!token) {
       pm.collectionVariables.set("token", "");
   }
   ```

4. **Add Authorization (Collection Level):**
   - Type: Bearer Token
   - Token: `{{token}}`

### Sample Requests

#### 1. Login Request

**POST** `{{base_url}}/auth/login`

**Body:**
```json
{
  "email": "demo@example.com",
  "password": "SecurePass123!"
}
```

**Tests Script:**
```javascript
// Save token to collection variable
const response = pm.response.json();
pm.collectionVariables.set("token", response.access_token);
pm.test("Login successful", () => {
    pm.response.to.have.status(200);
    pm.expect(response.access_token).to.exist;
});
```

#### 2. Create Property Request

**POST** `{{base_url}}/properties`

**Headers:**
- `Authorization`: `Bearer {{token}}`

**Body:**
```json
{
  "address": "456 Oak Avenue",
  "city": "Oakland",
  "state": "CA",
  "zip": "94601",
  "price": 850000,
  "bedrooms": 2,
  "bathrooms": 2
}
```

**Tests Script:**
```javascript
const response = pm.response.json();
pm.collectionVariables.set("property_id", response.id);
pm.test("Property created", () => {
    pm.response.to.have.status(201);
    pm.expect(response.id).to.exist;
});
```

### Insomnia Workspace Setup

1. **Create Workspace:** "Real Estate OS"

2. **Create Environment:** "Local Development"
   ```json
   {
     "base_url": "http://localhost:8000",
     "token": ""
   }
   ```

3. **Import OpenAPI Spec:**
   - File → Import/Export → Import Data
   - Select: `http://localhost:8000/docs/openapi.json`
   - All endpoints will be imported automatically!

4. **Set Bearer Token:**
   - Click on collection
   - Auth tab → Bearer Token
   - Token: `{{ _.token }}`

---

## Mock Services Testing

### MailHog (Email Testing)

Access MailHog web interface:
```
http://localhost:8025
```

**API to check emails:**
```bash
curl http://localhost:8025/api/v2/messages | jq .
```

### MinIO (Storage Testing)

Access MinIO console:
```
http://localhost:9001
```

**Default credentials:**
- Username: `minioadmin`
- Password: `minioadmin`

---

## Complete Test Sequence

Run this complete sequence to verify all core functionality:

```bash
#!/bin/bash

# 1. Register
echo "1. Registering user..."
curl -sS -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"Test123!","name":"Test User"}' | jq .

# 2. Login and get token
echo "2. Logging in..."
TOKEN=$(curl -sS -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"Test123!"}' \
  | jq -r '.access_token')
echo "Token: $TOKEN"

# 3. Create property
echo "3. Creating property..."
PROP=$(curl -sS -X POST http://localhost:8000/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"address":"789 Test St","city":"Test City","state":"CA","zip":"90000","price":600000}')
PROPERTY_ID=$(echo $PROP | jq -r '.id')
echo "Property ID: $PROPERTY_ID"

# 4. Create lead
echo "4. Creating lead..."
LEAD=$(curl -sS -X POST http://localhost:8000/leads \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Test Lead","email":"lead@test.com","phone":"555-0199"}')
LEAD_ID=$(echo $LEAD | jq -r '.id')
echo "Lead ID: $LEAD_ID"

# 5. Create deal
echo "5. Creating deal..."
curl -sS -X POST http://localhost:8000/deals \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"lead_id\":\"$LEAD_ID\",\"property_id\":\"$PROPERTY_ID\",\"status\":\"negotiation\",\"value\":600000}" | jq .

echo "✅ All tests complete!"
```

---

## Troubleshooting

### Services not responding

```bash
# Check service health
docker compose ps

# Check logs
docker compose logs api
docker compose logs db

# Restart services
docker compose restart
```

### Token expired

```bash
# Get new token
TOKEN=$(curl -sS -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"SecurePass123!"}' \
  | jq -r '.access_token')
```

### Clear database and start fresh

```bash
# Stop services and remove volumes
docker compose down -v

# Start again
docker compose up -d
sleep 30

# Re-run migrations
docker compose exec api alembic upgrade head
```

---

## Next Steps

1. **Explore Interactive Docs:** http://localhost:8000/docs
2. **Run Automated Tests:** `./scripts/runtime_verification/verify_platform.sh`
3. **Check CI/CD:** See `.github/workflows/runtime-verification.yml`
4. **Review Evidence:** Check `audit_artifacts/runtime_*/`

---

**Questions or Issues?**
- Review PATH_TO_FULL_GO.md for complete verification strategy
- Check docker-compose logs for service errors
- Ensure all ports (8000, 5432, 6379, 8025, 9001) are available
