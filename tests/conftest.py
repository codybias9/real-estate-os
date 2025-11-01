"""Pytest configuration and shared fixtures

Provides:
- Database session fixtures
- Test client fixtures
- Authentication fixtures
- Mock data factories
- Tenant isolation helpers
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
import os

# Set test environment variables before importing app
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-not-for-production"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"  # High limit for tests
os.environ["RATE_LIMIT_PER_TENANT_MINUTE"] = "2000"

from api.main import app
from api.app.database import get_db
from db.models import Base
from db.models_auth import User as DBUser, APIKey as DBAPIKey
from db.models_provenance import Tenant as DBTenant

# Test database URL (SQLite for speed)
TEST_DATABASE_URL = "sqlite:///./test_real_estate_os.db"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine for the session"""
    return engine


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a fresh database session for each test

    Creates all tables, yields session, then drops all tables.
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db(db_session):
    """Alias for db_session (shorter name)"""
    return db_session


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with database override

    Automatically uses test database for all requests.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides after test
    app.dependency_overrides.clear()


# ============================================================================
# Tenant Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_tenant(db_session):
    """Create a test tenant"""
    tenant = DBTenant(
        name="Test Organization",
        slug="test-org"
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
def test_tenant_id(test_tenant):
    """Get test tenant ID"""
    return test_tenant.id


@pytest.fixture(scope="function")
def second_tenant(db_session):
    """Create a second tenant for isolation tests"""
    tenant = DBTenant(
        name="Second Organization",
        slug="second-org"
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_user(db_session, test_tenant):
    """Create a test user with owner role"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = DBUser(
        tenant_id=test_tenant.id,
        email="test@example.com",
        password_hash=pwd_context.hash("testpassword123"),
        roles=["owner"],
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin_user(db_session, test_tenant):
    """Create a test user with admin role"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = DBUser(
        tenant_id=test_tenant.id,
        email="admin@example.com",
        password_hash=pwd_context.hash("adminpassword123"),
        roles=["admin"],
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_analyst_user(db_session, test_tenant):
    """Create a test user with analyst role (read-only)"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = DBUser(
        tenant_id=test_tenant.id,
        email="analyst@example.com",
        password_hash=pwd_context.hash("analystpassword123"),
        roles=["analyst"],
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(client, test_user):
    """Get authentication token for test user"""
    response = client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def admin_token(client, test_admin_user):
    """Get authentication token for admin user"""
    response = client.post(
        "/auth/login",
        json={
            "email": test_admin_user.email,
            "password": "adminpassword123"
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def analyst_token(client, test_analyst_user):
    """Get authentication token for analyst user"""
    response = client.post(
        "/auth/login",
        json={
            "email": test_analyst_user.email,
            "password": "analystpassword123"
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def auth_headers(auth_token):
    """Get authorization headers with Bearer token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def admin_headers(admin_token):
    """Get authorization headers for admin"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def analyst_headers(analyst_token):
    """Get authorization headers for analyst"""
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture(scope="function")
def test_api_key(db_session, test_tenant):
    """Create a test API key"""
    from passlib.context import CryptContext
    import secrets

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    api_key_value = secrets.token_urlsafe(32)

    api_key = DBAPIKey(
        tenant_id=test_tenant.id,
        name="Test Service Key",
        description="For testing",
        key_hash=pwd_context.hash(api_key_value),
        key_prefix=api_key_value[:8],
        roles=["service"],
        is_active=True
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    # Return both the DB record and the actual key
    return {"record": api_key, "key": api_key_value}


@pytest.fixture(scope="function")
def api_key_headers(test_api_key):
    """Get API key headers"""
    return {"X-API-Key": test_api_key["key"]}


# ============================================================================
# Mock Data Factories
# ============================================================================

@pytest.fixture
def property_factory(db_session, test_tenant):
    """Factory for creating test properties"""
    def _create_property(**kwargs):
        from db.models_provenance import Property

        defaults = {
            "id": uuid4(),
            "tenant_id": test_tenant.id,
            "deterministic_id": f"prop_{uuid4().hex[:8]}",
            "canonical_address": {
                "street": "123 Test St",
                "city": "Testville",
                "state": "CA",
                "zip": "90210"
            },
            "listing_price": 500000,
            "square_feet": 2000,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2020
        }
        defaults.update(kwargs)

        prop = Property(**defaults)
        db_session.add(prop)
        db_session.commit()
        db_session.refresh(prop)
        return prop

    return _create_property


@pytest.fixture
def scorecard_factory(db_session, test_tenant):
    """Factory for creating test scorecards"""
    def _create_scorecard(property_id, **kwargs):
        from db.models_provenance import Scorecard

        defaults = {
            "id": uuid4(),
            "tenant_id": test_tenant.id,
            "property_id": property_id,
            "score": 0.75,
            "grade": "B",
            "model_version": "v1.0.0",
            "factors": {"location": 0.8, "price": 0.7}
        }
        defaults.update(kwargs)

        scorecard = Scorecard(**defaults)
        db_session.add(scorecard)
        db_session.commit()
        db_session.refresh(scorecard)
        return scorecard

    return _create_scorecard


@pytest.fixture
def campaign_factory(db_session, test_tenant):
    """Factory for creating test email campaigns"""
    def _create_campaign(**kwargs):
        from db.models_outreach import Campaign

        defaults = {
            "id": uuid4(),
            "tenant_id": test_tenant.id,
            "name": "Test Campaign",
            "campaign_type": "cold_outreach",
            "status": "draft",
            "total_recipients": 0
        }
        defaults.update(kwargs)

        campaign = Campaign(**defaults)
        db_session.add(campaign)
        db_session.commit()
        db_session.refresh(campaign)
        return campaign

    return _create_campaign


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limiters between tests"""
    # Rate limiters are in-memory, so they reset automatically
    # This is a placeholder for future Redis-based rate limiting
    yield


@pytest.fixture(autouse=True)
def clear_auth_overrides():
    """Clear any auth dependency overrides after each test"""
    yield
    app.dependency_overrides.clear()


# ============================================================================
# Test Helpers
# ============================================================================

def create_authenticated_client(client, token):
    """Helper to create client with auth headers"""
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
