"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

from ..main import app
from ..database import Base, get_db
from ..models import (
    User,
    Organization,
    Role,
    Permission,
    UserRole,
    RolePermission,
    Property,
    Lead,
    Campaign,
    Deal,
)
from ..services.auth import AuthService
from ..config import settings

# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Start a transaction
    connection = engine.connect()
    transaction = connection.begin()

    # Bind session to transaction
    session.bind = connection

    yield session

    # Rollback transaction after test
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database session override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def organization(db_session):
    """Create test organization."""
    org = Organization(
        name="Test Organization",
        slug="test-org",
        is_active=True,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture(scope="function")
def admin_role(db_session):
    """Create admin role with all permissions."""
    role = Role(
        name="admin",
        description="Administrator role",
        is_system=True,
    )
    db_session.add(role)
    db_session.flush()

    # Create basic permissions
    permissions = [
        Permission(name="property:create", resource="property", action="create"),
        Permission(name="property:read", resource="property", action="read"),
        Permission(name="property:update", resource="property", action="update"),
        Permission(name="property:delete", resource="property", action="delete"),
        Permission(name="lead:create", resource="lead", action="create"),
        Permission(name="lead:read", resource="lead", action="read"),
        Permission(name="lead:update", resource="lead", action="update"),
        Permission(name="lead:delete", resource="lead", action="delete"),
        Permission(name="campaign:create", resource="campaign", action="create"),
        Permission(name="campaign:read", resource="campaign", action="read"),
        Permission(name="campaign:send", resource="campaign", action="send"),
        Permission(name="deal:create", resource="deal", action="create"),
        Permission(name="deal:read", resource="deal", action="read"),
        Permission(name="deal:update", resource="deal", action="update"),
        Permission(name="deal:delete", resource="deal", action="delete"),
        Permission(name="user:create", resource="user", action="create"),
        Permission(name="user:read", resource="user", action="read"),
        Permission(name="user:update", resource="user", action="update"),
        Permission(name="user:delete", resource="user", action="delete"),
        Permission(name="analytics:read", resource="analytics", action="read"),
        Permission(name="portfolio:create", resource="portfolio", action="create"),
        Permission(name="portfolio:read", resource="portfolio", action="read"),
        Permission(name="portfolio:update", resource="portfolio", action="update"),
        Permission(name="portfolio:delete", resource="portfolio", action="delete"),
        Permission(name="transaction:create", resource="transaction", action="create"),
        Permission(name="transaction:read", resource="transaction", action="read"),
        Permission(name="role:create", resource="role", action="create"),
        Permission(name="role:read", resource="role", action="read"),
        Permission(name="role:update", resource="role", action="update"),
        Permission(name="role:delete", resource="role", action="delete"),
    ]

    for perm in permissions:
        db_session.add(perm)
        db_session.flush()

        # Associate with role
        role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
        db_session.add(role_perm)

    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture(scope="function")
def test_user(db_session, organization, admin_role):
    """Create test user."""
    user = User(
        organization_id=organization.id,
        email="test@example.com",
        hashed_password=AuthService.hash_password("Test123!@#"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.flush()

    # Assign admin role
    user_role = UserRole(user_id=user.id, role_id=admin_role.id)
    db_session.add(user_role)

    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user):
    """Create authentication headers for test user."""
    token = AuthService.create_access_token(data={"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_property(db_session, organization, test_user):
    """Create test property."""
    from ..models.property import PropertyType, PropertyStatus

    property_obj = Property(
        organization_id=organization.id,
        created_by=test_user.id,
        address="123 Test St",
        city="Test City",
        state="CA",
        zip_code="12345",
        country="USA",
        property_type=PropertyType.SINGLE_FAMILY,
        status=PropertyStatus.AVAILABLE,
        price=500000,
        bedrooms=3,
        bathrooms=2.5,
        square_feet=2000,
        description="Test property",
    )
    db_session.add(property_obj)
    db_session.commit()
    db_session.refresh(property_obj)
    return property_obj


@pytest.fixture(scope="function")
def test_lead(db_session, organization, test_user):
    """Create test lead."""
    from ..models.lead import LeadSource, LeadStatus

    lead = Lead(
        organization_id=organization.id,
        created_by=test_user.id,
        assigned_to=test_user.id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="555-1234",
        source=LeadSource.WEBSITE,
        status=LeadStatus.NEW,
        score=50,
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


@pytest.fixture(scope="function")
def test_deal(db_session, organization, test_user, test_property):
    """Create test deal."""
    from ..models.deal import DealType, DealStage
    from datetime import date

    deal = Deal(
        organization_id=organization.id,
        created_by=test_user.id,
        property_id=test_property.id,
        deal_type=DealType.SELL,
        stage=DealStage.QUALIFIED,
        value=500000,
        probability=75,
        expected_close_date=date.today(),
    )
    db_session.add(deal)
    db_session.commit()
    db_session.refresh(deal)
    return deal


@pytest.fixture
def sample_property_data():
    """Sample property data for testing."""
    return {
        "address": "456 Main St",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94102",
        "property_type": "single_family",
        "status": "available",
        "price": 750000,
        "bedrooms": 4,
        "bathrooms": 3,
        "square_feet": 2500,
        "description": "Beautiful house in SF",
    }


@pytest.fixture
def sample_lead_data():
    """Sample lead data for testing."""
    return {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone": "555-5678",
        "source": "referral",
        "status": "new",
        "score": 60,
    }


@pytest.fixture
def sample_deal_data(test_property):
    """Sample deal data for testing."""
    from datetime import date, timedelta

    return {
        "property_id": test_property.id,
        "deal_type": "buy",
        "stage": "lead",
        "value": 600000,
        "probability": 50,
        "expected_close_date": (date.today() + timedelta(days=30)).isoformat(),
    }


@pytest.fixture(autouse=True)
def reset_database(db_session):
    """Reset database before each test."""
    # This fixture runs automatically before each test
    yield
    # Cleanup after test
    db_session.rollback()


# Utility fixtures

@pytest.fixture
def faker_factory():
    """Create Faker instance for generating test data."""
    from faker import Faker

    return Faker()


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis for testing without actual Redis connection."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    # Add common Redis methods
    mock.get.return_value = None
    mock.set.return_value = True
    mock.incr.return_value = 1
    mock.expire.return_value = True
    mock.ttl.return_value = 60

    return mock


@pytest.fixture
def disable_auth(monkeypatch):
    """Disable authentication for testing."""
    from ..dependencies import get_current_user

    def mock_get_current_user():
        return User(
            id=1,
            organization_id=1,
            email="test@example.com",
            is_superuser=True,
        )

    monkeypatch.setattr("api.dependencies.get_current_user", mock_get_current_user)
