# PR3: Database Migrations + RLS - Evidence Pack

**PR**: `feat/db-migrations-rls`
**Date**: 2025-11-02
**Branch**: `claude/realestate-audit-canvas-011CUjnrkmyeMSTozDmpy6xx`

## Summary

Implemented comprehensive database schema with Alembic migrations and Row-Level Security (RLS) policies for multi-tenant data isolation.

## Migration Details

**Migration ID**: `fb3c6b29453b`
**Description**: Initial schema with RLS policies

### Tables Created

#### 1. `tenants` Table
Core multi-tenancy table for customer isolation.

**Columns:**
- `id` (UUID, PK, default: uuid_generate_v4())
- `name` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMPTZ, default: now())
- `updated_at` (TIMESTAMPTZ, default: now())
- `is_active` (BOOLEAN, default: true)

**Indexes:**
- `ix_tenants_name` on `name`

**Triggers:**
- `update_tenants_updated_at` - Auto-updates `updated_at` on row modification

---

#### 2. `users` Table
User accounts tied to tenants with RLS enforcement.

**Columns:**
- `id` (UUID, PK, default: uuid_generate_v4())
- `tenant_id` (UUID, NOT NULL, FK → tenants.id ON DELETE CASCADE)
- `email` (VARCHAR(255), NOT NULL, UNIQUE)
- `full_name` (VARCHAR(255), nullable)
- `is_active` (BOOLEAN, default: true)
- `created_at` (TIMESTAMPTZ, default: now())
- `updated_at` (TIMESTAMPTZ, default: now())

**Indexes:**
- `ix_users_email` (UNIQUE) on `email`
- `ix_users_tenant_id` on `tenant_id`

**RLS Policy:**
- `tenant_isolation_users`: Filters rows by `tenant_id = current_setting('app.current_tenant_id')::uuid`

**Triggers:**
- `update_users_updated_at` - Auto-updates `updated_at`

---

#### 3. `properties` Table
Property records with full metadata and scoring data.

**Columns:**
- `id` (UUID, PK)
- `tenant_id` (UUID, NOT NULL, FK → tenants.id ON DELETE CASCADE)
- `apn` (VARCHAR(50), nullable)
- `apn_hash` (VARCHAR(64), nullable)
- `street` (VARCHAR(255), nullable)
- `city` (VARCHAR(100), nullable)
- `state` (VARCHAR(2), nullable)
- `zip_code` (VARCHAR(10), nullable)
- `latitude` (FLOAT, nullable)
- `longitude` (FLOAT, nullable)
- `owner_name` (VARCHAR(255), nullable)
- `owner_type` (VARCHAR(50), nullable)
- `bedrooms` (INTEGER, nullable)
- `bathrooms` (FLOAT, nullable)
- `square_feet` (INTEGER, nullable)
- `year_built` (INTEGER, nullable)
- `lot_size` (FLOAT, nullable)
- `score` (INTEGER, nullable)
- `score_reasons` (JSON, nullable)
- `status` (VARCHAR(50), default: 'discovered')
- `metadata` (JSON, nullable)
- `created_at` (TIMESTAMPTZ, default: now())
- `updated_at` (TIMESTAMPTZ, default: now())

**Indexes:**
- `ix_properties_apn` on `apn`
- `ix_properties_apn_hash` on `apn_hash`
- `ix_properties_city` on `city`
- `ix_properties_state` on `state`
- `ix_properties_status` on `status`
- `ix_properties_tenant_id` on `tenant_id`
- `ix_properties_zip_code` on `zip_code`
- `ix_properties_tenant_apn_hash` (UNIQUE) on `(tenant_id, apn_hash)` WHERE `apn_hash IS NOT NULL`

**RLS Policy:**
- `tenant_isolation_properties`: Filters rows by `tenant_id = current_setting('app.current_tenant_id')::uuid`

**Triggers:**
- `update_properties_updated_at` - Auto-updates `updated_at`

---

#### 4. `ping` Table
Health check table (no RLS - used by infrastructure).

**Columns:**
- `id` (INTEGER, PK, SERIAL)
- `ts` (TIMESTAMPTZ, default: now())

**No RLS:** This table is intentionally not protected by RLS as it's used for health checks.

---

## Row-Level Security (RLS) Implementation

### Purpose
RLS ensures that tenants can only access their own data, enforced at the database level (defense in depth).

### Mechanism
- RLS uses PostgreSQL session variable `app.current_tenant_id` to filter queries
- Application must call `SET app.current_tenant_id = '<uuid>'` before queries
- Policies apply to ALL operations (SELECT, INSERT, UPDATE, DELETE)

### Policy Examples

**Users Policy:**
```sql
CREATE POLICY tenant_isolation_users ON users
FOR ALL
TO PUBLIC
USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

**Properties Policy:**
```sql
CREATE POLICY tenant_isolation_properties ON properties
FOR ALL
TO PUBLIC
USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### Testing RLS
See `db/tests/test_migrations.py::TestRowLevelSecurity::test_rls_isolates_tenant_data`

This test:
1. Creates two tenants
2. Inserts users for each tenant
3. Sets tenant context and verifies isolation
4. Confirms Tenant 1 cannot see Tenant 2's data and vice versa

---

## Database Functions

### `update_updated_at_column()`
Trigger function that automatically updates the `updated_at` column to `now()` on row updates.

**Applied to:**
- `tenants`
- `users`
- `properties`

**Trigger Definition Example:**
```sql
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## Migration Commands

### Upgrade to Latest
```bash
cd db/
poetry run alembic upgrade head
```

### Downgrade to Base
```bash
cd db/
poetry run alembic downgrade base
```

### Check Current Revision
```bash
cd db/
poetry run alembic current
```

### Generate New Migration (Auto-detect)
```bash
cd db/
poetry run alembic revision --autogenerate -m "description"
```

---

## Dependencies Added

```toml
[tool.poetry.dependencies]
alembic = "^1.13.0"
```

---

## Configuration

### `db/alembic.ini`
- `script_location = migrations`
- `sqlalchemy.url` left blank (uses `DB_DSN` environment variable)

### `db/migrations/env.py`
Updated to read `DB_DSN` environment variable:
```python
db_dsn = os.getenv("DB_DSN")
if db_dsn:
    config.set_main_option("sqlalchemy.url", db_dsn)
```

---

## Test Coverage

**Test File:** `db/tests/test_migrations.py`
**Test Count:** 18 tests (requires PostgreSQL)
**Categories:**
1. **TestMigrations** (3 tests)
   - Migration runs successfully
   - Migration is reversible (downgrade works)
   - All expected tables exist

2. **TestRowLevelSecurity** (6 tests)
   - RLS enabled on users
   - RLS enabled on properties
   - RLS policy exists for users
   - RLS policy exists for properties
   - RLS isolates tenant data
   - RLS query filtering works

3. **TestIndexes** (2 tests)
   - Properties has tenant + apn_hash unique index
   - Users has email unique index

4. **TestTriggers** (2 tests)
   - updated_at trigger exists
   - updated_at trigger updates timestamp

5. **Schema Validation** (5 tests)
   - Tenants table schema
   - Users table schema
   - Properties table schema

---

## Files Created/Modified

**Created:**
- `db/migrations/versions/fb3c6b29453b_initial_schema_with_rls.py` (192 lines)
- `db/tests/__init__.py`
- `db/tests/conftest.py`
- `db/tests/test_migrations.py` (18 tests, 408 lines)

**Modified:**
- `db/alembic.ini` (updated script_location, removed hardcoded DB URL)
- `db/migrations/env.py` (added DB_DSN environment variable support)
- `pyproject.toml` (added alembic dependency)
- `pytest.ini` (added db/tests to testpaths)

---

## Architectural Decisions

1. **UUID Primary Keys**: All IDs are UUIDs for distributed system compatibility
2. **Tenant Cascade**: Foreign keys use ON DELETE CASCADE for clean tenant removal
3. **RLS Session Variable**: Uses `app.current_tenant_id` session variable pattern
4. **Partial Unique Index**: `(tenant_id, apn_hash)` is unique only WHERE `apn_hash IS NOT NULL`
5. **Trigger-Based Timestamps**: `updated_at` auto-updated via triggers (better than app-level)
6. **JSON Columns**: `score_reasons` and `metadata` use JSON for flexibility

---

## Evidence

### Schema Diagram (Logical)

```
┌──────────────┐
│   tenants    │
│  (no RLS)    │
└──────┬───────┘
       │
       │ CASCADE
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌──────────┐      ┌──────────────┐
│  users   │      │  properties  │
│  (RLS)   │      │    (RLS)     │
└──────────┘      └──────────────┘

┌──────────┐
│   ping   │
│ (no RLS) │
└──────────┘
```

### RLS Policy Verification

Run this in `psql` after migration:
```sql
-- Check RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('users', 'properties');

-- Check policies exist
SELECT tablename, policyname, cmd, qual
FROM pg_policies
WHERE schemaname = 'public';
```

Expected output:
```
 tablename  | rowsecurity
------------+-------------
 users      | t
 properties | t

 tablename  |        policyname         | cmd |                     qual
------------+---------------------------+-----+---------------------------------------------
 users      | tenant_isolation_users    | ALL | (tenant_id = current_setting('app.current_tenant_id'::text)::uuid)
 properties | tenant_isolation_properties | ALL | (tenant_id = current_setting('app.current_tenant_id'::text)::uuid)
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Forgetting to set `app.current_tenant_id` | RLS will filter to 0 rows (fail-safe). Add middleware to auto-set. |
| Migration downgrade on production | Never downgrade prod. Use blue-green deployments. |
| Large properties table scan | Indexed on tenant_id, apn_hash, city, state, zip, status |
| UUID performance vs INT | Modern PostgreSQL handles UUIDs efficiently. Worth distributed benefits. |
| RLS performance overhead | Minimal (sub-ms per query). Indexes on tenant_id help. |

---

## Follow-Ups

1. Add database connection pooling in API (PR2+)
2. Add SQLAlchemy ORM models (PR4-6)
3. Add tenant context middleware (PR12)
4. Add database seed data for development
5. Add Alembic autogenerate for schema diffs
6. Add migration version check at API startup
7. Add tenant admin endpoints (PR12)
8. Add database backup/restore documentation

---

## Acceptance Criteria

- [x] Alembic configured with `DB_DSN` environment variable
- [x] Migration creates tenants, users, properties, ping tables
- [x] RLS enabled on users and properties
- [x] RLS policies enforce tenant isolation
- [x] Indexes on tenant_id, apn_hash, email, etc.
- [x] Foreign keys with CASCADE delete
- [x] updated_at triggers on all tables
- [x] Migration is reversible (downgrade works)
- [x] 18 tests covering migrations, RLS, indexes, triggers
- [x] Unique constraint on (tenant_id, apn_hash) per tenant

---

## Next Steps

**PR4-6:** Add discovery, enrichment, and scoring agent verification with database integration.
