# Real Estate OS API Documentation

Complete guide to using the Real Estate OS API for building real estate deal pipeline applications.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Core Workflows](#core-workflows)
4. [API Reference](#api-reference)
5. [Real-Time Features](#real-time-features)
6. [Webhooks](#webhooks)
7. [Best Practices](#best-practices)
8. [Error Handling](#error-handling)

---

## Quick Start

### 1. Register a New Account

```bash
curl -X POST https://api.realestateos.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePassword123!",
    "team_name": "Acme Real Estate"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "full_name": "John Doe",
    "email": "john@example.com",
    "team_id": 1,
    "role": "admin"
  },
  "team": {
    "id": 1,
    "name": "Acme Real Estate"
  }
}
```

### 2. Add Your First Property

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST https://api.realestateos.com/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip_code": "94102",
    "owner_name": "Jane Smith",
    "team_id": 1,
    "bird_dog_score": 0.85,
    "estimated_value": 850000
  }'
```

### 3. Generate and Send a Memo

```bash
curl -X POST https://api.realestateos.com/api/v1/quick-wins/generate-and-send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "template_id": 1,
    "send_immediately": true,
    "delivery_method": "email"
  }'
```

---

## Authentication

### JWT Tokens

All API requests (except registration and login) require a JWT token in the Authorization header:

```bash
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Getting a Token

**Login:**
```bash
curl -X POST https://api.realestateos.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'
```

**Token Expiration:**
- Tokens expire after 24 hours
- Refresh by logging in again
- No refresh token endpoint (for security)

### Rate Limiting

- **100 requests per minute** per user
- **1000 requests per hour** per team

Rate limit headers in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705334400
```

**Example: Handling Rate Limits**
```python
import requests
import time

def api_request_with_retry(url, headers, data):
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        return api_request_with_retry(url, headers, data)

    return response
```

---

## Core Workflows

### Workflow 1: Add Property and Generate Memo

```python
import requests

BASE_URL = "https://api.realestateos.com/api/v1"
headers = {"Authorization": f"Bearer {token}"}

# Step 1: Create property
property_data = {
    "address": "456 Oak Ave",
    "city": "Oakland",
    "state": "CA",
    "zip_code": "94601",
    "owner_name": "Bob Johnson",
    "team_id": 1,
    "bird_dog_score": 0.78
}

response = requests.post(
    f"{BASE_URL}/properties",
    headers=headers,
    json=property_data
)

property_id = response.json()["id"]

# Step 2: Generate and send memo
memo_data = {
    "property_id": property_id,
    "template_id": 1,
    "send_immediately": True,
    "delivery_method": "email"
}

response = requests.post(
    f"{BASE_URL}/quick-wins/generate-and-send",
    headers=headers,
    json=memo_data
)

print(f"Memo sent! Communication ID: {response.json()['communication_id']}")
```

### Workflow 2: Move Property Through Pipeline

```python
# Get property
response = requests.get(
    f"{BASE_URL}/properties/{property_id}",
    headers=headers
)

current_stage = response.json()["current_stage"]
print(f"Current stage: {current_stage}")

# Move to next stage
update_data = {
    "current_stage": "qualified"
}

response = requests.patch(
    f"{BASE_URL}/properties/{property_id}",
    headers=headers,
    json=update_data
)

print(f"Updated to: {response.json()['current_stage']}")
```

### Workflow 3: Search and Filter Properties

```python
# Advanced filtering
params = {
    "team_id": 1,
    "stage": "outreach",
    "bird_dog_score__gte": 0.7,
    "has_memo": True,
    "has_reply": False,
    "limit": 50
}

response = requests.get(
    f"{BASE_URL}/properties",
    headers=headers,
    params=params
)

properties = response.json()
print(f"Found {len(properties)} properties needing follow-up")

for prop in properties:
    days_since_contact = (datetime.now() - datetime.fromisoformat(prop['last_contact_at'])).days
    if days_since_contact > 7:
        print(f"Follow up needed: {prop['address']} ({days_since_contact} days)")
```

### Workflow 4: Portfolio Reconciliation

```python
# Run reconciliation
response = requests.post(
    f"{BASE_URL}/portfolio/reconcile",
    headers=headers,
    json={"portfolio_id": 1}
)

result = response.json()

if result["validation_status"] == "pass":
    print(f"✅ Reconciliation passed ({result['discrepancy_percentage']}%)")
else:
    print(f"❌ Reconciliation failed ({result['discrepancy_percentage']}%)")
    print(f"Threshold: ±{result['threshold']}%")
    print(f"Discrepancy: ${result['discrepancy_amount']:,.0f}")
```

---

## API Reference

### Properties

#### Create Property

**Endpoint:** `POST /api/v1/properties`

**Request Body:**
```json
{
  "address": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "zip_code": "94102",
  "owner_name": "Jane Smith",
  "owner_phone": "+1-555-0100",
  "owner_email": "jane@example.com",
  "team_id": 1,
  "assigned_user_id": 1,
  "bird_dog_score": 0.85,
  "estimated_value": 850000,
  "tags": ["high-priority", "owner-occupied"]
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "address": "123 Main St",
  "current_stage": "new",
  "created_at": "2024-01-15T10:30:00Z",
  ...
}
```

#### List Properties

**Endpoint:** `GET /api/v1/properties`

**Query Parameters:**
- `team_id` (int): Filter by team
- `stage` (string): Filter by stage (new, outreach, qualified, etc.)
- `assigned_user_id` (int): Filter by assigned user
- `bird_dog_score__gte` (float): Minimum score (0.0-1.0)
- `bird_dog_score__lte` (float): Maximum score (0.0-1.0)
- `has_memo` (boolean): Filter properties with/without memo
- `has_reply` (boolean): Filter properties with/without reply
- `search` (string): Full-text search (address, owner, city)
- `tags` (list): Filter by tags
- `skip` (int): Pagination offset (default: 0)
- `limit` (int): Page size (default: 100, max: 1000)

**Example:**
```bash
GET /api/v1/properties?team_id=1&stage=outreach&bird_dog_score__gte=0.7&limit=50
```

#### Update Property

**Endpoint:** `PATCH /api/v1/properties/{property_id}`

**Request Body (partial update):**
```json
{
  "current_stage": "qualified",
  "assigned_user_id": 2,
  "tags": ["hot-lead", "owner-motivated"]
}
```

**Response:** `200 OK`

#### Get Property Timeline

**Endpoint:** `GET /api/v1/properties/{property_id}/timeline`

**Response:**
```json
[
  {
    "id": 1,
    "property_id": 1,
    "event_type": "property_created",
    "event_title": "Property Added to Pipeline",
    "event_description": "Added 123 Main St",
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "event_type": "memo_sent",
    "event_title": "Memo Sent",
    "event_description": "Email sent via SendGrid",
    "created_at": "2024-01-15T11:00:00Z"
  }
]
```

### Communications

#### Generate and Send Memo

**Endpoint:** `POST /api/v1/quick-wins/generate-and-send`

**Request Body:**
```json
{
  "property_id": 1,
  "template_id": 1,
  "send_immediately": true,
  "delivery_method": "email"
}
```

**Idempotency:**
Automatically uses key: `memo_{property_id}_{template_id}_{date}`

**Response:** `200 OK`
```json
{
  "communication_id": 1,
  "property_id": 1,
  "template_id": 1,
  "subject": "Quick question about 123 Main St",
  "body": "Hi Jane,\n\nI noticed your property...",
  "delivery_method": "email",
  "status": "sent",
  "sent_at": "2024-01-15T12:00:00Z",
  "task_id": "abc-123-def"
}
```

#### List Templates

**Endpoint:** `GET /api/v1/communications/templates`

**Response:**
```json
[
  {
    "id": 1,
    "name": "Initial Outreach",
    "type": "email",
    "subject_template": "Quick question about {{address}}",
    "body_template": "Hi {{owner_name}},\n\n...",
    "stage": "outreach",
    "performance": {
      "total_sent": 150,
      "total_opened": 82,
      "total_replied": 23,
      "open_rate": 0.547,
      "reply_rate": 0.153
    }
  }
]
```

### Portfolio

#### Get Portfolio Statistics

**Endpoint:** `GET /api/v1/portfolio/stats`

**Query Parameters:**
- `team_id` (int, required)
- `date_from` (string, optional): ISO 8601 date
- `date_to` (string, optional): ISO 8601 date

**Response:**
```json
{
  "total_properties": 150,
  "by_stage": {
    "new": 20,
    "outreach": 45,
    "qualified": 30,
    "negotiation": 25,
    "under_contract": 15,
    "closed_won": 10,
    "closed_lost": 5
  },
  "avg_bird_dog_score": 0.73,
  "total_estimated_value": 125000000,
  "conversion_rate": 0.067,
  "avg_days_in_pipeline": 45,
  "this_month": {
    "new_properties": 12,
    "closed_won": 2,
    "closed_lost": 1
  }
}
```

#### Run Reconciliation

**Endpoint:** `POST /api/v1/portfolio/reconcile`

**Request Body:**
```json
{
  "portfolio_id": 1
}
```

**Response:**
```json
{
  "portfolio_id": 1,
  "validation_status": "pass",
  "discrepancy_percentage": 0.23,
  "threshold": 0.5,
  "properties_checked": 150,
  "total_value_expected": 125000000,
  "total_value_actual": 125287500,
  "discrepancy_amount": 287500,
  "checked_at": "2024-01-15T14:00:00Z"
}
```

---

## Real-Time Features

### Server-Sent Events (SSE)

Subscribe to real-time updates for property changes, memo generation, and more.

#### Step 1: Get SSE Token

```bash
curl -X POST https://api.realestateos.com/api/v1/sse/token \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "sse_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "stream_url": "http://localhost:8000/api/v1/sse/stream?token=...",
  "expires_in": 3600
}
```

#### Step 2: Connect to Event Stream

**JavaScript Example:**
```javascript
const sseToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
const eventSource = new EventSource(
  `https://api.realestateos.com/api/v1/sse/stream?token=${sseToken}`
)

eventSource.addEventListener('property_updated', (event) => {
  const data = JSON.parse(event.data)
  console.log('Property updated:', data.property_id, data.current_stage)
  // Update UI
})

eventSource.addEventListener('memo_generated', (event) => {
  const data = JSON.parse(event.data)
  console.log('Memo sent:', data.communication_id)
  // Show notification
})

eventSource.onerror = (error) => {
  console.error('SSE connection error:', error)
  // Implement reconnect logic
}
```

**Python Example:**
```python
import sseclient
import requests

response = requests.get(
    'https://api.realestateos.com/api/v1/sse/stream',
    params={'token': sse_token},
    stream=True
)

client = sseclient.SSEClient(response)

for event in client.events():
    if event.event == 'property_updated':
        data = json.loads(event.data)
        print(f"Property {data['property_id']} moved to {data['current_stage']}")
    elif event.event == 'memo_generated':
        data = json.loads(event.data)
        print(f"Memo {data['communication_id']} sent successfully")
```

### Event Types

| Event | Description | Data Fields |
|-------|-------------|-------------|
| `property_updated` | Property stage or assignment changed | `property_id`, `team_id`, `current_stage`, `updated_by` |
| `memo_generated` | Memo successfully generated and sent | `communication_id`, `property_id`, `team_id`, `status` |
| `reply_received` | Owner replied to communication | `communication_id`, `property_id`, `reply_text` |
| `task_completed` | Background task finished | `task_id`, `task_type`, `status` |

---

## Webhooks

### SendGrid Email Events

**Endpoint:** `POST /api/v1/webhooks/email-provider`

**Events:**
- `delivered`: Email successfully delivered
- `open`: Recipient opened email
- `click`: Recipient clicked link
- `bounce`: Email bounced
- `dropped`: Email dropped by SendGrid
- `spam_report`: Recipient marked as spam

**Example Payload:**
```json
{
  "event": "delivered",
  "email": "jane@example.com",
  "timestamp": 1705323600,
  "smtp-id": "<abc123@sendgrid.net>",
  "sg_message_id": "message_456",
  "communication_id": "1"
}
```

**Signature Verification:**
```python
import hmac
import hashlib

def verify_sendgrid_signature(payload_bytes, signature, secret):
    expected = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
```

### Twilio SMS Events

**Endpoint:** `POST /api/v1/webhooks/sms-provider`

**Events:**
- `sent`: SMS sent to carrier
- `delivered`: SMS delivered to recipient
- `failed`: SMS delivery failed
- `undelivered`: SMS couldn't be delivered

**Example Payload:**
```json
{
  "MessageSid": "SM1234567890",
  "MessageStatus": "delivered",
  "To": "+15550100",
  "From": "+15550199",
  "Body": "Hi Jane, quick question about...",
  "communication_id": "2"
}
```

---

## Best Practices

### 1. Use Idempotency Keys

For critical operations (memo generation, payments), always include an idempotency key:

```bash
curl -X POST ... \
  -H "Idempotency-Key: unique-operation-id-123" \
  ...
```

**Benefits:**
- Prevent duplicate operations
- Safe to retry failed requests
- Cached responses for 24 hours

### 2. Implement Exponential Backoff

```python
import time

def api_call_with_retry(url, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, ...)

            if response.status_code == 429:  # Rate limited
                retry_after = int(response.headers.get('Retry-After', 60))
                time.sleep(retry_after)
                continue

            if response.status_code >= 500:  # Server error
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue

            return response

        except requests.exceptions.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

### 3. Use ETags for Caching

```python
# First request
response = requests.get(url, headers=headers)
etag = response.headers.get('ETag')

# Subsequent requests
headers['If-None-Match'] = etag
response = requests.get(url, headers=headers)

if response.status_code == 304:
    print("Content not modified, use cached version")
else:
    # Content changed, update cache
    etag = response.headers.get('ETag')
```

### 4. Handle Pagination Efficiently

```python
def get_all_properties(team_id, batch_size=100):
    all_properties = []
    skip = 0

    while True:
        response = requests.get(
            f"{BASE_URL}/properties",
            params={
                "team_id": team_id,
                "skip": skip,
                "limit": batch_size
            },
            headers=headers
        )

        properties = response.json()
        if not properties:
            break

        all_properties.extend(properties)
        skip += batch_size

        if len(properties) < batch_size:
            break

    return all_properties
```

### 5. Monitor DLQ and Retry Failed Tasks

```python
# Check DLQ status
response = requests.get(
    f"{BASE_URL}/admin/dlq/stats",
    headers=admin_headers
)

stats = response.json()
if stats['total_failed'] > 0:
    print(f"⚠️  {stats['total_failed']} failed tasks in DLQ")

    # Replay failed tasks
    response = requests.post(
        f"{BASE_URL}/admin/dlq/replay-bulk",
        headers=admin_headers,
        json={
            "queue": "memos",
            "max_tasks": 10,
            "dry_run": False
        }
    )
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 201 | Created | Resource created successfully |
| 304 | Not Modified | Use cached version (ETag match) |
| 400 | Bad Request | Check request format/validation |
| 401 | Unauthorized | Refresh access token |
| 403 | Forbidden | Check user permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Fix validation errors |
| 429 | Rate Limited | Wait and retry (check Retry-After header) |
| 500 | Server Error | Retry with exponential backoff |

### Error Response Format

```json
{
  "detail": "Validation error message",
  "errors": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### Example Error Handling

```python
try:
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        # Token expired, re-authenticate
        token = login()
        headers['Authorization'] = f'Bearer {token}'
        return api_call(url, data, headers)  # Retry

    elif e.response.status_code == 422:
        # Validation error
        errors = e.response.json()['errors']
        for error in errors:
            print(f"Validation error: {error['loc']} - {error['msg']}")
        raise

    elif e.response.status_code == 429:
        # Rate limited
        retry_after = int(e.response.headers.get('Retry-After', 60))
        time.sleep(retry_after)
        return api_call(url, data, headers)  # Retry

    else:
        raise

except requests.exceptions.RequestException as e:
    print(f"Network error: {e}")
    # Implement retry logic
```

---

## Additional Resources

- **Swagger UI**: https://api.realestateos.com/docs
- **ReDoc**: https://api.realestateos.com/redoc
- **OpenAPI Spec**: https://api.realestateos.com/openapi.json
- **Monitoring**: https://api.realestateos.com/metrics
- **Status Page**: https://status.realestateos.com

## Support

- Email: support@realestateos.com
- Slack: #api-support
- Documentation: https://docs.realestateos.com

---

**Last Updated**: January 15, 2024
**API Version**: 1.0.0
