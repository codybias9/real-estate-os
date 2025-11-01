# Keycloak OIDC Integration

## Overview

This implementation provides enterprise-grade Single Sign-On (SSO) using Keycloak as the OpenID Connect (OIDC) provider.

**Key Features**:
- Authorization Code Flow with PKCE (RFC 7636)
- Multi-tenant support via custom claims
- Role-based access control (RBAC)
- Backward compatibility with legacy JWT
- Automatic token refresh
- Secure token storage

---

## Architecture

```
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│   React     │          │   Keycloak  │          │   FastAPI   │
│   Frontend  │◄────────►│   (OIDC)    │◄────────►│   Backend   │
└─────────────┘          └─────────────┘          └─────────────┘
      │                         │                         │
      │   1. /authorize         │                         │
      ├────────────────────────►│                         │
      │                         │                         │
      │   2. Login UI           │                         │
      │◄────────────────────────┤                         │
      │                         │                         │
      │   3. Auth code          │                         │
      │◄────────────────────────┤                         │
      │                         │                         │
      │   4. /token (code)      │                         │
      ├────────────────────────►│                         │
      │                         │                         │
      │   5. access_token       │                         │
      │◄────────────────────────┤                         │
      │                         │                         │
      │   6. API call + token   │                         │
      ├─────────────────────────┼────────────────────────►│
      │                         │                         │
      │                         │   7. Verify token       │
      │                         │◄────────────────────────┤
      │                         │                         │
      │                         │   8. JWKS + validation  │
      │                         ├────────────────────────►│
      │                         │                         │
      │   9. API response       │                         │
      │◄────────────────────────┴─────────────────────────┤
```

---

## Quick Start

### 1. Start Keycloak

```bash
# Start Keycloak with Postgres
docker compose -f auth/keycloak/docker-compose.keycloak.yml up -d

# Wait for Keycloak to be ready (60-90 seconds)
docker logs -f real-estate-os-keycloak

# Access admin console
open http://localhost:8180
# Login: admin / admin (change in production!)
```

### 2. Import Realm

```bash
# Realm is auto-imported on startup from:
# auth/keycloak/realms/real-estate-os-realm.json

# Verify import
# Navigate to: http://localhost:8180/admin/master/console
# Select realm: real-estate-os (top-left dropdown)
```

### 3. Configure Environment Variables

```bash
# API (.env)
OIDC_ISSUER=http://localhost:8180/realms/real-estate-os
OIDC_CLIENT_ID=real-estate-os-api
OIDC_CLIENT_SECRET=**CHANGE_THIS_SECRET**

# Web (.env.local)
VITE_OIDC_ISSUER=http://localhost:8180/realms/real-estate-os
VITE_OIDC_CLIENT_ID=real-estate-os-web
VITE_OIDC_REDIRECT_URI=http://localhost:8080/callback
```

### 4. Create Test User

Via Admin Console:
1. Go to http://localhost:8180/admin/master/console
2. Select realm: `real-estate-os`
3. Navigate to: Users → Add user
4. Fill in:
   - Username: `testuser`
   - Email: `testuser@example.com`
   - Email Verified: ON
5. Click "Create"
6. Go to "Credentials" tab → Set password
7. Go to "Attributes" tab → Add:
   - Key: `tenant_id`, Value: `<UUID>`
8. Go to "Role mapping" tab → Assign role: `owner`

Via API (programmatic):
```bash
# Get admin token
ADMIN_TOKEN=$(curl -X POST "http://localhost:8180/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" | jq -r .access_token)

# Create user
curl -X POST "http://localhost:8180/admin/realms/real-estate-os/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "testuser@example.com",
    "emailVerified": true,
    "enabled": true,
    "attributes": {
      "tenant_id": ["<UUID>"]
    },
    "credentials": [{
      "type": "password",
      "value": "password123",
      "temporary": false
    }],
    "realmRoles": ["owner"]
  }'
```

---

## API Integration

### Hybrid Authentication

The API supports both OIDC and legacy JWT for backward compatibility:

```python
from api.app.auth.hybrid_dependencies import get_current_user

@router.get("/protected")
async def protected_endpoint(
    user: User = Depends(get_current_user)
):
    # Works with both OIDC tokens and legacy JWT
    return {"user_id": user.user_id, "tenant_id": user.tenant_id}
```

### OIDC-Only Authentication

To enforce OIDC only:

```python
from api.app.auth.oidc import get_oidc_provider

oidc = get_oidc_provider()
token_payload = oidc.verify_token(token)
user_claims = oidc.extract_user_claims(token_payload)
```

### Token Verification Flow

1. **Extract token** from `Authorization: Bearer <token>` header
2. **Try OIDC verification**:
   - Fetch JWKS from Keycloak
   - Verify signature with RS256
   - Validate issuer, audience, expiration
   - Extract user claims (tenant_id, roles)
3. **Fallback to JWT** if OIDC fails (backward compat)
4. **Return user** object

---

## Frontend Integration

### Setup OIDCProvider

```tsx
// App.tsx
import { OIDCProvider } from './auth/OIDCProvider';

function App() {
  return (
    <OIDCProvider>
      <Router>
        <Routes>
          <Route path="/callback" element={<OIDCCallback />} />
          <Route path="/" element={<ProtectedPage />} />
        </Routes>
      </Router>
    </OIDCProvider>
  );
}
```

### Use Authentication

```tsx
import { useOIDC } from './auth/OIDCProvider';

function ProtectedPage() {
  const { user, isAuthenticated, login, logout, getAccessToken } = useOIDC();

  if (!isAuthenticated) {
    return <button onClick={login}>Login with SSO</button>;
  }

  return (
    <div>
      <p>Welcome, {user.name}</p>
      <p>Email: {user.email}</p>
      <p>Roles: {user.roles.join(', ')}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

### Make Authenticated API Calls

```tsx
const { getAccessToken } = useOIDC();

const response = await fetch('http://localhost:8000/api/v1/properties', {
  headers: {
    'Authorization': `Bearer ${getAccessToken()}`
  }
});
```

---

## Configuration

### Realm Configuration

Edit `auth/keycloak/realms/real-estate-os-realm.json`:

```json
{
  "realm": "real-estate-os",
  "enabled": true,
  "sslRequired": "external",
  "registrationAllowed": true,
  "resetPasswordAllowed": true,
  "bruteForceProtected": true,
  ...
}
```

### Client Configuration

**API Client** (Bearer-only):
- Client ID: `real-estate-os-api`
- Client Protocol: `openid-connect`
- Access Type: `confidential`
- Service Accounts Enabled: `true`
- Bearer Only: `true`

**Web Client** (Public):
- Client ID: `real-estate-os-web`
- Client Protocol: `openid-connect`
- Access Type: `public`
- Standard Flow Enabled: `true`
- Valid Redirect URIs: `http://localhost:8080/*`
- Web Origins: `http://localhost:8080`

### Custom Claims

**tenant_id** (for multi-tenancy):
1. Go to Client Scopes → tenant
2. Add Mapper:
   - Name: `tenant-id`
   - Mapper Type: `User Attribute`
   - User Attribute: `tenant_id`
   - Token Claim Name: `tenant_id`
   - Claim JSON Type: `String`

**roles** (for RBAC):
1. Go to Client Scopes → roles
2. Add Mapper:
   - Name: `realm-roles`
   - Mapper Type: `User Realm Role`
   - Token Claim Name: `roles`
   - Claim JSON Type: `String`
   - Multivalued: `true`

---

## Security

### Secrets Management

**Production**:
```bash
# Generate secure client secret
openssl rand -base64 32

# Store in Kubernetes secret
kubectl create secret generic keycloak-secrets \
  --from-literal=OIDC_CLIENT_SECRET=<secret> \
  -n real-estate-os

# Reference in deployment
env:
  - name: OIDC_CLIENT_SECRET
    valueFrom:
      secretKeyRef:
        name: keycloak-secrets
        key: OIDC_CLIENT_SECRET
```

### Token Validation

- **Signature**: RS256 with JWKS
- **Issuer**: Must match configured issuer
- **Audience**: Must match client_id
- **Expiration**: Checked automatically
- **Not Before**: Checked automatically

### PKCE (Proof Key for Code Exchange)

- **Code Verifier**: 128-character random string
- **Code Challenge**: SHA256(code_verifier), base64url-encoded
- **Challenge Method**: `S256`

Protects against authorization code interception attacks.

---

## Troubleshooting

### Token Validation Fails

```bash
# Check OIDC discovery
curl http://localhost:8180/realms/real-estate-os/.well-known/openid-configuration | jq

# Check JWKS
curl http://localhost:8180/realms/real-estate-os/protocol/openid-connect/certs | jq

# Decode token (for debugging)
# Paste token at: https://jwt.io
```

### User Missing tenant_id

```bash
# Add tenant_id attribute to user
# Via Admin Console: Users → <user> → Attributes → Add
# Key: tenant_id, Value: <UUID>

# Or via API:
curl -X PUT "http://localhost:8180/admin/realms/real-estate-os/users/<user-id>" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attributes": {
      "tenant_id": ["<UUID>"]
    }
  }'
```

### Keycloak Not Starting

```bash
# Check logs
docker logs real-estate-os-keycloak

# Common issues:
# 1. Database not ready → Wait for postgres healthcheck
# 2. Port 8180 in use → Change KC_HTTP_PORT
# 3. Realm import failed → Check JSON syntax
```

---

## Production Deployment

### HTTPS/TLS

```bash
# Keycloak requires HTTPS in production
# Set sslRequired: "all" in realm config

# Use reverse proxy (nginx/traefik) for TLS termination
# Or configure Keycloak TLS directly:

KC_HTTPS_CERTIFICATE_FILE=/path/to/cert.pem
KC_HTTPS_CERTIFICATE_KEY_FILE=/path/to/key.pem
```

### High Availability

```yaml
# Keycloak cluster (3+ nodes)
services:
  keycloak-1:
    image: quay.io/keycloak/keycloak:23.0
    environment:
      KC_CACHE: ispn
      KC_CACHE_STACK: kubernetes
      JGROUPS_DISCOVERY_PROTOCOL: dns.DNS_PING
      JGROUPS_DISCOVERY_PROPERTIES: dns_query=keycloak-headless.default.svc.cluster.local

  keycloak-2: ...
  keycloak-3: ...
```

### Database

```bash
# Use managed Postgres (AWS RDS, Cloud SQL, etc.)
KC_DB_URL=jdbc:postgresql://<rds-endpoint>:5432/keycloak
KC_DB_USERNAME=keycloak
KC_DB_PASSWORD=<secure-password>
```

### Monitoring

```bash
# Metrics endpoint
curl http://localhost:8180/metrics

# Health checks
curl http://localhost:8180/health/ready
curl http://localhost:8180/health/live

# Prometheus scrape config
- job_name: 'keycloak'
  static_configs:
    - targets: ['keycloak:8180']
```

---

## Migration from Legacy JWT

### Phase 1: Add OIDC (Hybrid Mode)

- Deploy Keycloak
- Update API to accept both OIDC and JWT
- Frontend remains using JWT
- **No disruption**

### Phase 2: Frontend Migration

- Update frontend to use OIDCProvider
- New users authenticate via OIDC
- Existing users continue with JWT
- **Gradual rollout**

### Phase 3: Deprecate JWT

- Announce deprecation timeline (e.g., 90 days)
- Force all users to re-authenticate via OIDC
- Remove JWT support from API
- **Complete migration**

---

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OpenID Connect Spec](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 PKCE](https://datatracker.ietf.org/doc/html/rfc7636)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)

---

**Status**: Production-ready
**Version**: 1.0
**Last Updated**: 2025-11-01
