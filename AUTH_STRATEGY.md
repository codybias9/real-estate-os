# Authentication & Authorization Strategy

## Demo/MOCK_MODE Configuration

This platform uses **minimal auth enforcement** optimized for demo ease-of-use while protecting write operations.

### Public Endpoints (No Authentication Required)

#### System & Health
- `GET /healthz` - Health check
- `GET /status/*` - Provider status, incidents
- `GET /system/*` - System metrics, health, workers, queues
- `GET /analytics/*` - Platform analytics

#### Documentation
- `GET /docs` - Swagger UI
- `GET /openapi.json` - OpenAPI specification
- `GET /redoc` - ReDoc documentation

#### Read Operations
All GET endpoints are public to facilitate demo browsing:
- Properties, Leads, Deals, Templates
- Workflow, Automation, Communications
- Sharing, Jobs, Pipelines

#### SSE Events
- `GET /sse/token` - Get SSE token (separate auth)
- `GET /sse/stream` - SSE event stream (token-based)

### Protected Endpoints (Bearer Token Required)

#### Core Entity Writes
**Properties:**
- `POST /properties` - Create property
- `PATCH /properties/{id}` - Update property
- `DELETE /properties/{id}` - Delete property

**Deals:**
- `POST /deals` - Create deal
- `PATCH /deals/{id}` - Update deal

**Leads:**
- `POST /leads` - Create lead (currently public)

**Templates:**
- `POST /templates` - Create template (currently public)
- `PUT /templates/{id}` - Update template (currently public)
- `DELETE /templates/{id}` - Delete template (currently public)

**Workflow:**
- `POST /workflow/*` - Create workflow entities (currently public)
- `PATCH /workflow/*` - Update workflow entities (currently public)
- `DELETE /workflow/*` - Delete workflow entities (currently public)

**Automation:**
- `POST /automation/*` - Create automation rules (currently public)
- `PATCH /automation/*` - Update automation rules (currently public)

### Demo User Credentials

**Email:** `demo@example.com`
**Password:** `demo123`

### Token Flow

1. **Login:** `POST /auth/login` with credentials
2. **Receive:** `{"access_token": "...", "user": {...}}`
3. **Use:** Add header `Authorization: Bearer {access_token}` to protected requests
4. **Frontend:** Token stored in Zustand `authStore`, automatically attached via Axios interceptor

### Current Coverage

- **Protected:** 2 endpoints (1.4% of 139 non-auth endpoints)
- **Total Endpoints:** 142 (including 3 auth endpoints)
- **Status:** Minimal enforcement suitable for demo
- **Risk:** Most write operations are currently unprotected

### Production Upgrade Path

For production deployment:
1. Expand `get_current_user` to all write operations
2. Add team_id filtering on all queries
3. Implement JWT token validation (not just mock acceptance)
4. Add role-based permissions (admin/manager/agent)
5. Implement refresh tokens
6. Add rate limiting per user

### Implementation Files

- **Auth Utils:** `api/auth_utils.py` - `get_current_user()` dependency
- **Frontend Store:** `frontend/src/store/authStore.ts` - Token management
- **API Client:** `frontend/src/lib/api.ts` - Axios with auth interceptor
- **Routers:** Individual routers add `current_user: User = Depends(get_current_user)` parameter

### Trade-offs

✅ **Benefits:**
- Easy demo without auth friction
- Read-only operations work immediately
- Public analytics for dashboards

⚠️ **Limitations:**
- Most write operations unprotected
- No multi-tenant isolation enforced
- Suitable for demo only, not production

---

**Last Updated:** 2025-11-14
**For Production:** Expand auth coverage to all write operations and implement JWT validation.
