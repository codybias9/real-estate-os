# Real Estate OS API - Usage Examples

This document provides comprehensive examples for using the Real Estate OS API.

## Table of Contents
- [Authentication](#authentication)
- [Properties](#properties)
- [Leads](#leads)
- [Campaigns](#campaigns)
- [Deals](#deals)
- [Analytics](#analytics)
- [Real-time Updates](#real-time-updates)
- [Error Handling](#error-handling)

## Base URL

```
http://localhost:8000
```

## Authentication

### 1. Register a New User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "organization_name": "Acme Real Estate"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "organization_id": 1
  }
}
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### 3. Get Current User

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

### 4. Refresh Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

---

## Properties

### 1. Create Property

```bash
curl -X POST "http://localhost:8000/api/v1/properties" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main Street",
    "city": "Los Angeles",
    "state": "CA",
    "zip_code": "90001",
    "country": "USA",
    "property_type": "single_family",
    "status": "available",
    "price": 750000,
    "bedrooms": 3,
    "bathrooms": 2.5,
    "square_feet": 2200,
    "lot_size": 5000,
    "year_built": 2015,
    "description": "Beautiful modern home with great views"
  }'
```

### 2. List Properties

```bash
# Basic list
curl -X GET "http://localhost:8000/api/v1/properties" \
  -H "Authorization: Bearer <access_token>"

# With filters
curl -X GET "http://localhost:8000/api/v1/properties?property_type=single_family&min_price=500000&max_price=1000000&city=Los+Angeles" \
  -H "Authorization: Bearer <access_token>"

# With pagination
curl -X GET "http://localhost:8000/api/v1/properties?skip=0&limit=20" \
  -H "Authorization: Bearer <access_token>"
```

### 3. Get Property Details

```bash
curl -X GET "http://localhost:8000/api/v1/properties/1" \
  -H "Authorization: Bearer <access_token>"
```

### 4. Update Property

```bash
curl -X PUT "http://localhost:8000/api/v1/properties/1" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "under_contract",
    "price": 725000
  }'
```

### 5. Add Property Image

```bash
curl -X POST "http://localhost:8000/api/v1/properties/1/images" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/image1.jpg",
    "title": "Front View",
    "is_primary": true
  }'
```

### 6. Add Property Valuation

```bash
curl -X POST "http://localhost:8000/api/v1/properties/1/valuations" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "value": 750000,
    "valuation_date": "2024-01-15",
    "source": "professional_appraisal",
    "notes": "Appraised by ABC Appraisal Services"
  }'
```

---

## Leads

### 1. Create Lead

```bash
curl -X POST "http://localhost:8000/api/v1/leads" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane.smith@example.com",
    "phone": "+1-555-0100",
    "source": "website",
    "status": "new",
    "budget": 800000,
    "timeline": "3-6 months",
    "notes": "Looking for 3-4 bedroom in West LA"
  }'
```

### 2. List Leads

```bash
# All leads
curl -X GET "http://localhost:8000/api/v1/leads" \
  -H "Authorization: Bearer <access_token>"

# Filter by status
curl -X GET "http://localhost:8000/api/v1/leads?status=qualified" \
  -H "Authorization: Bearer <access_token>"

# Search
curl -X GET "http://localhost:8000/api/v1/leads?search=jane" \
  -H "Authorization: Bearer <access_token>"
```

### 3. Update Lead

```bash
curl -X PUT "http://localhost:8000/api/v1/leads/1" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "qualified",
    "score": 85,
    "notes": "Very interested, pre-qualified for $850k"
  }'
```

### 4. Add Lead Activity

```bash
curl -X POST "http://localhost:8000/api/v1/leads/1/activities" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "activity_type": "call",
    "subject": "Follow-up call",
    "description": "Discussed property preferences and budget",
    "outcome": "success",
    "scheduled_at": "2024-01-20T10:00:00Z"
  }'
```

### 5. Assign Lead

```bash
curl -X POST "http://localhost:8000/api/v1/leads/1/assign" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "assigned_to": 2
  }'
```

---

## Campaigns

### 1. Create Campaign Template

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/templates" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Listing Announcement",
    "description": "Template for announcing new property listings",
    "campaign_type": "email",
    "subject": "New Property: {{property_address}}",
    "content": "Check out our new listing at {{property_address}}..."
  }'
```

### 2. Create Campaign

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Spring 2024 Open House",
    "campaign_type": "email",
    "subject": "Join us for our Spring Open House",
    "content": "You'\''re invited to our exclusive open house event...",
    "status": "draft"
  }'
```

### 3. Send Campaign

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/1/send" \
  -H "Authorization: Bearer <access_token>"
```

### 4. Get Campaign Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/stats" \
  -H "Authorization: Bearer <access_token>"
```

---

## Deals

### 1. Create Deal

```bash
curl -X POST "http://localhost:8000/api/v1/deals" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "lead_id": 1,
    "deal_type": "sale",
    "stage": "proposal",
    "value": 750000,
    "commission_rate": 5.0,
    "probability": 60,
    "expected_close_date": "2024-03-15",
    "notes": "Buyer is very interested"
  }'
```

### 2. Update Deal Stage

```bash
curl -X PUT "http://localhost:8000/api/v1/deals/1" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "negotiation",
    "probability": 75,
    "notes": "Initial offer received"
  }'
```

### 3. Add Transaction

```bash
curl -X POST "http://localhost:8000/api/v1/deals/1/transactions" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_type": "deposit",
    "amount": 25000,
    "description": "Earnest money deposit",
    "transaction_date": "2024-01-20"
  }'
```

### 4. Create Portfolio

```bash
curl -X POST "http://localhost:8000/api/v1/portfolios" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Investment Properties 2024",
    "description": "Commercial and residential investment properties"
  }'
```

---

## Analytics

### 1. Get Dashboard

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/dashboard" \
  -H "Authorization: Bearer <access_token>"
```

**Response:**
```json
{
  "properties": {
    "total": 45,
    "available": 32,
    "under_contract": 10,
    "sold": 3
  },
  "leads": {
    "total": 128,
    "new": 15,
    "qualified": 42,
    "converted": 8
  },
  "deals": {
    "total": 23,
    "total_value": 15750000,
    "average_value": 684782.61,
    "by_stage": {
      "proposal": 5,
      "negotiation": 8,
      "contract": 6,
      "closing": 4
    }
  },
  "revenue": {
    "total_commissions": 787500,
    "this_month": 125000
  }
}
```

### 2. Get Property Analytics

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/properties?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer <access_token>"
```

### 3. Get Lead Analytics

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/leads?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer <access_token>"
```

### 4. Get Revenue Analytics

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/revenue?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer <access_token>"
```

---

## Real-time Updates

### Server-Sent Events (SSE)

Connect to SSE stream for real-time updates:

**JavaScript Example:**
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/sse/stream',
  {
    headers: {
      'Authorization': 'Bearer <access_token>'
    }
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event received:', data);

  switch(data.type) {
    case 'property.created':
      console.log('New property:', data.data);
      break;
    case 'lead.assigned':
      console.log('Lead assigned:', data.data);
      break;
    case 'deal.stage_changed':
      console.log('Deal stage changed:', data.data);
      break;
  }
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};
```

**Available Event Types:**
- `property.created`
- `property.updated`
- `property.deleted`
- `lead.created`
- `lead.updated`
- `lead.assigned`
- `deal.created`
- `deal.stage_changed`
- `campaign.completed`
- `notification`

---

## Advanced Features

### 1. Idempotency

Prevent duplicate requests using the `Idempotency-Key` header:

```bash
curl -X POST "http://localhost:8000/api/v1/properties" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-12345" \
  -d '{
    "address": "456 Oak Avenue",
    ...
  }'
```

If you send the same request with the same idempotency key within 24 hours, you'll receive the cached response.

### 2. ETag Caching

Use ETags for efficient caching:

```bash
# First request
curl -X GET "http://localhost:8000/api/v1/properties/1" \
  -H "Authorization: Bearer <access_token>" \
  -i

# Response includes: ETag: "abc123..."

# Subsequent request
curl -X GET "http://localhost:8000/api/v1/properties/1" \
  -H "Authorization: Bearer <access_token>" \
  -H 'If-None-Match: "abc123..."' \
  -i

# Returns 304 Not Modified if resource hasn't changed
```

### 3. Pagination

All list endpoints support pagination:

```bash
curl -X GET "http://localhost:8000/api/v1/properties?skip=0&limit=20" \
  -H "Authorization: Bearer <access_token>"
```

**Response:**
```json
{
  "items": [...],
  "total": 145,
  "skip": 0,
  "limit": 20,
  "has_more": true
}
```

---

## Error Handling

The API returns consistent error responses:

### Error Response Format

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

### Common Error Codes

| Status Code | Error Type | Description |
|-------------|------------|-------------|
| 400 | BadRequest | Invalid request data |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | NotFound | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | ValidationError | Request validation failed |
| 429 | RateLimitExceeded | Too many requests |
| 500 | InternalServerError | Server error |
| 503 | ServiceUnavailable | External service error |

### Example Error Handling (JavaScript)

```javascript
async function createProperty(data) {
  try {
    const response = await fetch('http://localhost:8000/api/v1/properties', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error.message);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to create property:', error.message);
    throw error;
  }
}
```

---

## Health Checks

### Basic Health Check
```bash
curl -X GET "http://localhost:8000/healthz"
```

### Detailed Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "service": "Real Estate OS API",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 1.8
    },
    "celery": {
      "status": "healthy",
      "workers": 2
    },
    "storage": {
      "status": "healthy",
      "response_time_ms": 12.5
    }
  }
}
```

---

## Rate Limiting

The API implements rate limiting:

- **60 requests per minute** per IP
- **1,000 requests per hour** per IP
- **10,000 requests per day** per IP

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642680000
```

When rate limit is exceeded (HTTP 429):

```json
{
  "error": {
    "type": "RateLimitExceededError",
    "message": "Rate limit exceeded: 60 requests per minute",
    "details": {
      "limit": 60,
      "window": "minute",
      "retry_after": 42
    }
  }
}
```

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **GitHub Repository**: [Your Repository URL]
- **Support**: [Your Support Email/URL]

---

## Environment Variables

When running requests from a script, you can set these environment variables:

```bash
export API_URL="http://localhost:8000"
export ACCESS_TOKEN="your_access_token_here"

# Then use in requests
curl -X GET "$API_URL/api/v1/properties" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
