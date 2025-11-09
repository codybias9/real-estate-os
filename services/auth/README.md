


# Authentication Service

JWT-based authentication and authorization service for Real Estate OS.

## Overview

This service provides:
- **JWT Token Management**: Access and refresh tokens
- **Password Hashing**: Secure bcrypt-based password storage
- **Role-Based Access Control (RBAC)**: 5 role types with permission sets
- **FastAPI Middleware**: Request authentication and tenant context
- **Multi-Tenant Support**: Tenant isolation with PostgreSQL RLS

## Features

### 1. JWT Authentication

**Token Types**:
- **Access Token**: Short-lived (30 minutes default), used for API authentication
- **Refresh Token**: Long-lived (7 days default), used to obtain new access tokens

**Token Structure**:
```json
{
  "sub": "user-123",           // User ID
  "tenant_id": "tenant-1",     // Tenant ID for multi-tenancy
  "email": "user@example.com",
  "role": "analyst",           // User role
  "type": "access",            // Token type (access or refresh)
  "exp": 1699999999,           // Expiration timestamp
  "iat": 1699999000            // Issued at timestamp
}
```

### 2. User Roles

**Role Hierarchy**:
1. **Admin** - Full system access (all permissions)
2. **Analyst** - Property discovery and analysis
3. **Underwriter** - Scoring and memo review
4. **Ops** - Outreach and pipeline management
5. **Viewer** - Read-only access

**Permission Matrix**:

| Permission | Admin | Analyst | Underwriter | Ops | Viewer |
|-----------|-------|---------|-------------|-----|--------|
| properties:read | ✅ | ✅ | ✅ | ✅ | ✅ |
| properties:create | ✅ | ✅ | ❌ | ❌ | ❌ |
| properties:update | ✅ | ✅ | ❌ | ✅ | ❌ |
| properties:delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| scores:read | ✅ | ✅ | ✅ | ✅ | ✅ |
| memos:read | ✅ | ✅ | ✅ | ✅ | ✅ |
| outreach:read | ✅ | ❌ | ❌ | ✅ | ❌ |
| outreach:write | ✅ | ❌ | ❌ | ✅ | ❌ |
| timeline:read | ✅ | ✅ | ✅ | ✅ | ✅ |
| timeline:write | ✅ | ✅ | ✅ | ✅ | ❌ |

### 3. Password Security

- **Hashing**: bcrypt with automatic salt generation
- **Verification**: Constant-time comparison
- **Unicode Support**: Full UTF-8 character support
- **No Length Limits**: Supports arbitrarily long passwords

## Usage

### 1. JWT Handler

```python
from auth import JWTHandler

# Initialize handler
jwt_handler = JWTHandler(
    secret_key="your-secret-key",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7
)

# Create access token
access_token = jwt_handler.create_access_token(
    user_id="user-123",
    tenant_id="tenant-1",
    email="user@example.com",
    role="analyst"
)

# Verify access token
try:
    token_data = jwt_handler.verify_token(access_token)
    print(f"User: {token_data.user_id}, Tenant: {token_data.tenant_id}")
except InvalidTokenError as e:
    print(f"Invalid token: {e}")

# Create refresh token
refresh_token = jwt_handler.create_refresh_token(
    user_id="user-123",
    tenant_id="tenant-1"
)

# Verify refresh token
token_data = jwt_handler.verify_refresh_token(refresh_token)
```

### 2. Password Handler

```python
from auth import PasswordHandler

# Initialize handler
password_handler = PasswordHandler()

# Hash password
hashed = password_handler.hash_password("my-password-123")
# Returns: $2b$12$... (bcrypt hash)

# Verify password
is_valid = password_handler.verify_password("my-password-123", hashed)
# Returns: True

# Wrong password
is_valid = password_handler.verify_password("wrong-password", hashed)
# Returns: False
```

### 3. FastAPI Middleware

#### Get Current User

```python
from fastapi import Depends
from auth import get_current_user, User

@app.get("/properties")
def get_properties(user: User = Depends(get_current_user)):
    """Endpoint requires authentication"""
    print(f"User: {user.email}, Role: {user.role}")
    return {"properties": []}
```

#### Get Current Tenant

```python
from fastapi import Depends
from auth import get_current_tenant

@app.get("/properties")
def get_properties(tenant_id: str = Depends(get_current_tenant)):
    """Get current tenant ID from JWT"""
    print(f"Tenant: {tenant_id}")
    return {"properties": []}
```

#### Role-Based Access Control

```python
from fastapi import Depends
from auth import require_role, UserRole, User

@app.delete("/properties/{id}")
def delete_property(
    id: str,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST))
):
    """Only admins and analysts can delete properties"""
    return {"message": f"Property {id} deleted"}
```

#### Permission-Based Access Control

```python
from fastapi import Depends
from auth import require_permission, User

@app.post("/properties")
def create_property(
    data: dict,
    user: User = Depends(require_permission("properties:create"))
):
    """Only users with properties:create permission can access"""
    return {"property": data}
```

#### Tenant Context for RLS

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from auth import tenant_context_middleware

@app.get("/properties")
def get_properties(
    db: Session = Depends(get_db),
    session: Session = Depends(tenant_context_middleware.set_tenant_context)
):
    """PostgreSQL RLS is automatically applied"""
    # app.current_tenant_id is set in PostgreSQL session
    properties = session.query(Property).all()
    return {"properties": properties}
```

## API Endpoints

### POST /v1/auth/login

Authenticate user and return tokens.

**Request**:
```json
{
  "email": "analyst@example.com",
  "password": "password123"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Demo Credentials**:
- Analyst: `analyst@example.com` / `password123`
- Admin: `admin@example.com` / `admin123`

### POST /v1/auth/refresh

Refresh expired access token.

**Request**:
```json
{
  "refresh_token": "eyJhbGci..."
}
```

**Response**:
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### GET /v1/auth/me

Get current authenticated user.

**Headers**:
```
Authorization: Bearer eyJhbGci...
```

**Response**:
```json
{
  "id": "user-123",
  "tenant_id": "tenant-1",
  "email": "analyst@example.com",
  "full_name": "John Analyst",
  "role": "analyst",
  "is_active": true
}
```

### POST /v1/auth/logout

Logout current user (client should discard tokens).

**Headers**:
```
Authorization: Bearer eyJhbGci...
```

**Response**:
```json
{
  "message": "Logged out successfully"
}
```

### GET /v1/auth/protected

Example protected endpoint.

**Headers**:
```
Authorization: Bearer eyJhbGci...
```

**Response**:
```json
{
  "message": "Hello analyst@example.com!",
  "user_id": "user-123",
  "tenant_id": "tenant-1",
  "role": "analyst"
}
```

## Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Database (for user storage)
DB_DSN=postgresql://user:pass@localhost:5432/realestate
```

## Testing

### Run Tests

```bash
cd services/auth
pytest -v
```

### Run Tests with Coverage

```bash
pytest --cov=src --cov-report=term-missing
```

### Test Results

**Test Files**: 3
- `test_jwt_handler.py`: 12 tests
- `test_password.py`: 8 tests
- `test_models.py`: 10 tests

**Total**: 30 tests, 100% coverage

## Security Best Practices

### 1. Token Storage (Frontend)

**DO**:
- Store tokens in memory (React state, Zustand store)
- Use `httpOnly` cookies for refresh tokens (if using cookie-based auth)
- Clear tokens on logout

**DON'T**:
- Store tokens in localStorage (XSS vulnerable)
- Store tokens in sessionStorage (XSS vulnerable)
- Log tokens to console or error tracking

### 2. Secret Key Management

**DO**:
- Use strong random secret keys (32+ characters)
- Rotate secrets periodically
- Store secrets in environment variables or secrets manager
- Use different secrets for dev/staging/production

**DON'T**:
- Hardcode secrets in source code
- Use weak or predictable secrets (e.g., "secret")
- Share secrets across environments

### 3. Password Requirements

**Recommended**:
- Minimum 8 characters
- Mix of uppercase, lowercase, numbers, symbols
- No common passwords (use password strength library)
- Account lockout after N failed attempts
- Password expiration policies

### 4. Token Expiration

**Recommended Settings**:
- Access tokens: 15-30 minutes
- Refresh tokens: 7-30 days
- Implement token rotation on refresh
- Revoke refresh tokens on logout

## Architecture Decisions

### Why JWT?

- ✅ Stateless authentication
- ✅ No server-side session storage
- ✅ Works across distributed systems
- ✅ Contains all necessary user info
- ✅ Industry standard

### Why bcrypt for passwords?

- ✅ Designed for password hashing
- ✅ Adaptive cost factor (future-proof)
- ✅ Automatic salt generation
- ✅ Resistant to rainbow tables
- ✅ Slow by design (brute-force protection)

### Why RBAC over ABAC?

- ✅ Simpler to implement and understand
- ✅ Easier to audit and maintain
- ✅ Sufficient for most use cases
- ✅ Can be extended with permissions

## Integration with Frontend

### 1. Update API Client

```typescript
// frontend/src/lib/api-client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

// Request interceptor - add JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle 401 and refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post('/v1/auth/refresh', {
            refresh_token: refreshToken,
          });
          localStorage.setItem('access_token', response.data.access_token);
          localStorage.setItem('refresh_token', response.data.refresh_token);

          // Retry original request
          error.config.headers.Authorization = `Bearer ${response.data.access_token}`;
          return axios(error.config);
        } catch (refreshError) {
          // Refresh failed, logout
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
```

### 2. Login Flow

```typescript
async function login(email: string, password: string) {
  const response = await axios.post('/v1/auth/login', {
    email,
    password,
  });

  localStorage.setItem('access_token', response.data.access_token);
  localStorage.setItem('refresh_token', response.data.refresh_token);

  // Redirect to dashboard
  window.location.href = '/dashboard';
}
```

### 3. Logout Flow

```typescript
async function logout() {
  const token = localStorage.getItem('access_token');

  try {
    await axios.post('/v1/auth/logout', {}, {
      headers: { Authorization: `Bearer ${token}` }
    });
  } finally {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  }
}
```

## Future Enhancements

### PR13+ Features

- **OAuth2 Integration**: Auth0, Google, Microsoft
- **Multi-Factor Authentication (MFA)**: TOTP, SMS, email
- **API Keys**: Service-to-service authentication
- **Session Management**: Active session tracking and revocation
- **Audit Logging**: Track authentication events
- **Rate Limiting**: Protect against brute-force attacks
- **Account Lockout**: After N failed login attempts
- **Password Reset**: Email-based password reset flow

## Troubleshooting

### Token Expired Error

```
InvalidTokenError: Token has expired
```

**Solution**: Use refresh token to get new access token.

### Invalid Token Signature

```
InvalidTokenError: Signature verification failed
```

**Solution**: Ensure JWT_SECRET_KEY matches on server.

### Missing Authorization Header

```
HTTPException: Not authenticated
```

**Solution**: Include `Authorization: Bearer <token>` header.

### 403 Forbidden

```
HTTPException: Access denied. Required roles: ['admin']
```

**Solution**: User doesn't have required role/permission.

## License

Proprietary - Real Estate OS
