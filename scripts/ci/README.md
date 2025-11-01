

# CI Scripts for Tenant ID Enforcement

**Wave 1.7** - Automated checks ensuring tenant_id presence and RLS correctness.

## Overview

These scripts enforce multi-tenant data isolation at the CI level by:
1. ✅ Checking all database queries include `tenant_id` filters
2. ✅ Validating migrations have `tenant_id` columns and RLS policies
3. ✅ Linting code for proper tenant context usage

## Scripts

### 1. check_tenant_queries.py

**Purpose:** Ensure all SQLAlchemy queries on tenant-scoped models include `tenant_id` filtering.

**What it checks:**
- All `db.query(Model)` statements on tenant-scoped models
- Presence of `tenant_id` filter within 10 lines
- RLS context setting: `SET app.current_tenant_id`

**Tenant-scoped models:**
- Property
- OwnerEntity
- PropertyOwnerLink
- FieldProvenance
- Scorecard
- ScoreExplainability
- Deal
- PacketEvent
- ContactSuppression
- EvidenceEvent

**Usage:**
```bash
python scripts/ci/check_tenant_queries.py
```

**Example failure:**
```
❌ Tenant ID Check Failed

api/app/routers/properties.py:42: Query on tenant-scoped model 'Property' without tenant_id filter
  → db.query(Property).filter(Property.id == property_id).first()

FIX: Add tenant_id filter or set RLS context:
  db.query(Property).filter(Property.tenant_id == tenant_id, ...)
```

**Fix options:**

Option 1: Explicit filter
```python
db.query(Property).filter(
    Property.tenant_id == tenant_id,
    Property.id == property_id
).first()
```

Option 2: RLS (Row-Level Security)
```python
db.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")
db.query(Property).filter(Property.id == property_id).first()
```

---

### 2. check_migrations.py

**Purpose:** Validate that all new database migrations include tenant_id and RLS.

**What it checks:**
- New tables have `tenant_id` column (UUID, NOT NULL)
- `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` statement
- `CREATE POLICY ...tenant_isolation...` statement
- Foreign key to `tenant` table

**Exempt tables:**
- `alembic_version`
- `spatial_ref_sys`
- `tenant` (the tenant table itself)

**Usage:**
```bash
python scripts/ci/check_migrations.py
```

**Example failure:**
```
❌ Migration Check Failed

004_new_feature.py: Table 'my_new_table'
  Issues: Missing tenant_id column, RLS not enabled, Missing tenant_isolation policy
```

**Required migration structure:**

```python
def upgrade():
    # 1. Create table with tenant_id
    op.create_table(
        'my_table',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id']),
        # ... other columns
    )

    # 2. Enable RLS
    op.execute('ALTER TABLE my_table ENABLE ROW LEVEL SECURITY')

    # 3. Create tenant_isolation policy
    op.execute('''
        CREATE POLICY my_table_tenant_isolation ON my_table
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    ''')

    # 4. Create indexes
    op.create_index('idx_my_table_tenant', 'my_table', ['tenant_id'])
```

**Reference:** `db/versions/003_provenance_foundation.py`

---

### 3. lint_tenant_usage.py

**Purpose:** Lint code for proper tenant context patterns and best practices.

**What it checks:**

#### A. FastAPI Endpoints
- All endpoints (except `/`, `/health`, `/docs`) include `tenant_id` parameter

**Bad:**
```python
@router.get("/properties/{id}")
def get_property(id: str):
    return db.query(Property).get(id)
```

**Good:**
```python
@router.get("/properties/{id}")
def get_property(id: str, tenant_id: UUID = Query(...)):
    return db.query(Property).filter_by(id=id, tenant_id=tenant_id).first()
```

#### B. Hardcoded Tenant IDs
- Detects hardcoded UUID values (except default tenant)
- Suggests using parameters or environment variables

**Bad:**
```python
tenant_id = '12345678-1234-1234-1234-123456789012'  # Hardcoded!
```

**Good:**
```python
tenant_id = os.getenv('TENANT_ID')
# or
tenant_id = request_context.tenant_id
```

#### C. DAG Tenant Context
- Ensures Airflow DAGs set tenant context before database operations

**Bad:**
```python
def my_task(**context):
    properties = db.query(Property).all()  # No tenant context!
```

**Good:**
```python
def my_task(**context):
    tenant_id = context['params']['tenant_id']
    db.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")
    properties = db.query(Property).all()
```

#### D. SQLAlchemy Models
- Checks that models have `tenant_id` column

**Bad:**
```python
class MyModel(Base):
    __tablename__ = 'my_table'
    id = Column(UUID, primary_key=True)
    name = Column(String)
    # Missing tenant_id!
```

**Good:**
```python
class MyModel(Base):
    __tablename__ = 'my_table'
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey('tenant.id'), nullable=False)
    name = Column(String)
```

**Usage:**
```bash
python scripts/ci/lint_tenant_usage.py
```

---

## GitHub Actions Integration

**File:** `.github/workflows/tenant-id-checks.yml`

Runs on:
- Pull requests touching Python files
- Pushes to `main` or `develop` branches

**Steps:**
1. Install Python 3.11
2. Install dependencies (sqlalchemy, alembic, pydantic)
3. Run `check_tenant_queries.py`
4. Run `check_migrations.py`
5. Run `lint_tenant_usage.py`

**Example workflow:**
```yaml
jobs:
  check-tenant-id:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check tenant_id in queries
        run: python scripts/ci/check_tenant_queries.py
```

---

## Pre-commit Hooks

**File:** `.pre-commit-config.yaml`

Automatically runs checks before commits.

**Installation:**
```bash
pip install pre-commit
pre-commit install
```

**Manual run:**
```bash
pre-commit run --all-files
```

**Hooks included:**
- `check-tenant-queries` - Runs on all `.py` files
- `check-migrations` - Runs on `db/versions/*.py`
- `lint-tenant-usage` - Runs on all `.py` files
- `black` - Python code formatting
- `isort` - Import sorting
- `flake8` - Python linting
- `eslint` - TypeScript/JavaScript linting (web/)

**Skip hooks (emergency only):**
```bash
git commit --no-verify
```

---

## Test Helpers

**File:** `tests/fixtures/tenant_context.py`

Provides pytest fixtures for automatic tenant context injection.

### Available Fixtures

#### 1. test_tenant_id
Returns default test tenant UUID.

```python
def test_something(test_tenant_id):
    assert test_tenant_id == UUID("10000000-0000-0000-0000-000000000001")
```

#### 2. random_tenant_id
Returns a new random UUID for each test.

```python
def test_something(random_tenant_id):
    # Unique UUID per test
    pass
```

#### 3. db_with_tenant_context
Database session with tenant context already set.

```python
def test_query(db_with_tenant_context):
    # Context is automatically set
    properties = db_with_tenant_context.query(Property).all()
    # Only returns properties for test tenant
```

#### 4. db_with_custom_tenant
Fixture factory for custom tenant IDs.

```python
def test_multi_tenant(db_with_custom_tenant):
    db_a = db_with_custom_tenant(tenant_a_id)
    props_a = db_a.query(Property).all()

    db_b = db_with_custom_tenant(tenant_b_id)
    props_b = db_b.query(Property).all()

    assert props_a != props_b  # Isolated
```

#### 5. tenant_context_manager
Context manager for scoped tenant context.

```python
def test_scoped(tenant_context_manager, db_session):
    with tenant_context_manager(tenant_a_id):
        # Context active for tenant A
        props_a = db_session.query(Property).all()

    with tenant_context_manager(tenant_b_id):
        # Context active for tenant B
        props_b = db_session.query(Property).all()
```

### Helper Functions

#### ensure_tenant_context()
Set tenant context at start of test.

```python
def test_something(db_session, test_tenant_id):
    ensure_tenant_context(db_session, test_tenant_id)
    properties = db_session.query(Property).all()
```

#### verify_tenant_isolation()
Automatically test RLS isolation for a model.

```python
def test_isolation(db_session):
    def create_property(model_class, tenant_id):
        return Property(
            id=uuid4(),
            tenant_id=tenant_id,
            canonical_address={'street': 'Test'}
        )

    assert verify_tenant_isolation(
        db_session,
        Property,
        tenant_a_id,
        tenant_b_id,
        create_property
    )
```

**Full examples:** `tests/test_tenant_isolation_example.py`

---

## Best Practices

### 1. Always Use RLS Context in APIs

```python
@router.get("/properties/{id}")
def get_property(id: UUID, tenant_id: UUID, db: Session):
    # Set RLS context first
    db.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")

    # Now query without explicit filter (RLS handles it)
    property = db.query(Property).filter(Property.id == id).first()

    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    return property
```

### 2. Use Explicit Filters in Migrations

```python
def data_migration(**context):
    # In data migrations, use explicit filters
    db.query(Property).filter(Property.tenant_id == tenant_id).update(...)
```

### 3. Test Tenant Isolation

```python
def test_property_isolation(db_session):
    # Verify isolation works for every tenant-scoped model
    assert verify_tenant_isolation(db_session, Property, ...)
```

### 4. Never Hardcode Tenant IDs

```python
# Bad
tenant_id = "12345678-1234-1234-1234-123456789012"

# Good
tenant_id = os.getenv("TENANT_ID")
tenant_id = request.user.tenant_id
tenant_id = context["params"]["tenant_id"]
```

### 5. Use Fixtures in Tests

```python
# Don't manually set context
def test_bad(db_session):
    db_session.execute("SET LOCAL app.current_tenant_id = '...'")  # Manual
    ...

# Use fixture instead
def test_good(db_with_tenant_context):
    # Context already set
    ...
```

---

## Troubleshooting

### CI Check Fails on My PR

**Problem:** `check_tenant_queries.py` fails

**Solution:**
1. Find the failing query in error output
2. Add tenant_id filter or set RLS context
3. Commit and push again

### Migration Check Fails

**Problem:** `check_migrations.py` fails for new migration

**Solution:**
1. Add `tenant_id` column to table definition
2. Add `ENABLE ROW LEVEL SECURITY` statement
3. Add `CREATE POLICY ...tenant_isolation` statement
4. See `db/versions/003_provenance_foundation.py` for example

### Test Fixtures Not Working

**Problem:** `db_with_tenant_context` not injecting context

**Solution:**
1. Ensure `tests/fixtures/tenant_context.py` is in Python path
2. Import fixtures in `conftest.py`:
   ```python
   from tests.fixtures.tenant_context import *
   ```
3. Check database supports session variables (PostgreSQL 9.2+)

### False Positives in Linting

**Problem:** Lint script flags correct code

**Solution:**
1. Add comment to suppress: `# nosec` or `# tenant-id: verified`
2. Add pattern to `SKIP_PATTERNS` in script
3. Submit issue if pattern should be globally excluded

---

## Maintenance

### Adding New Tenant-Scoped Models

1. Add model name to `TENANT_SCOPED_MODELS` in `check_tenant_queries.py`
2. Update documentation
3. Run checks: `python scripts/ci/check_tenant_queries.py`

### Updating Check Logic

1. Edit script in `scripts/ci/`
2. Test locally: `python scripts/ci/check_*.py`
3. Update GitHub Actions if needed
4. Update pre-commit hooks if needed
5. Document changes in this README

---

## Files

```
scripts/ci/
├── README.md                   # This file
├── check_tenant_queries.py     # Query validation
├── check_migrations.py         # Migration validation
└── lint_tenant_usage.py        # General linting

.github/workflows/
└── tenant-id-checks.yml        # GitHub Actions workflow

.pre-commit-config.yaml         # Pre-commit hooks

tests/fixtures/
├── tenant_context.py           # Test fixtures
└── __init__.py

tests/
└── test_tenant_isolation_example.py  # Example tests
```

---

## Related Documentation

- **Wave 1 Completion Report:** `WAVE1_COMPLETION_REPORT.md`
- **Migration Example:** `db/versions/003_provenance_foundation.py`
- **API Example:** `api/app/routers/properties.py`
- **Test Examples:** `tests/test_tenant_isolation_example.py`

---

**Wave 1.7 Complete** - Comprehensive CI enforcement of tenant_id usage
