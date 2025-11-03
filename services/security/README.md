# Security Service

Security middleware for Real Estate OS API providing rate limiting, CORS, security headers, and input validation.

## Features

1. **Rate Limiting** - Prevent API abuse with configurable limits
2. **CORS** - Cross-Origin Resource Sharing for frontend integration
3. **Security Headers** - Protect against XSS, clickjacking, MIME sniffing
4. **Request ID Tracking** - Unique IDs for request tracing
5. **Input Validation** - Sanitize and validate user input

## Rate Limiting

```python
from security import rate_limit

@app.get("/api/properties")
@rate_limit("50/minute")
def get_properties():
    return {"properties": []}
```

## CORS Configuration

```python
from security import configure_cors

configure_cors(app, ["http://localhost:3000", "https://app.example.com"])
```

## Security Headers

Automatically adds:
- Content-Security-Policy
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection
- Strict-Transport-Security (HTTPS only)
- Referrer-Policy
- Permissions-Policy

## Input Validation

```python
from security import sanitize_input, validate_uuid, validate_email

# Sanitize user input
safe_text = sanitize_input(user_input, max_length=1000)

# Validate formats
if not validate_uuid(user_id):
    raise ValueError("Invalid user ID")

if not validate_email(email):
    raise ValueError("Invalid email")
```

## Request ID Tracking

```python
from security import get_request_id

request_id = get_request_id()
logger.info(f"Request {request_id}: Processing")
```

## Testing

```bash
cd services/security
pytest -v --cov=src
```
