"""
Pytest Configuration and Shared Fixtures

Provides common fixtures for all test suites
"""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set testing environment before importing app
os.environ["MOCK_MODE"] = "true"
os.environ["TESTING"] = "true"
os.environ["DB_DSN"] = "postgresql://postgres:postgres@localhost:5432/real_estate_os_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

from api.main import app
from db.models import Base


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def test_db_engine():
    """
    Create test database engine (session-scoped)

    Uses separate test database to avoid contaminating dev data
    """
    db_dsn = os.getenv("DB_DSN", "postgresql://postgres:postgres@localhost:5432/real_estate_os_test")

    engine = create_engine(
        db_dsn,
        poolclass=StaticPool,  # Use static pool for testing
        echo=False
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Drop all tables after tests
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """
    Create a new database session for each test

    Automatically rolls back changes after test completes
    """
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )

    session = TestingSessionLocal()

    yield session

    session.rollback()
    session.close()


# =============================================================================
# API CLIENT FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """
    FastAPI test client

    Use for testing API endpoints
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def authenticated_client(client, demo_user, auth_token) -> TestClient:
    """
    Authenticated test client with auth header
    """
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


# =============================================================================
# AUTH FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def demo_user(db_session):
    """
    Create demo user for testing
    """
    from db.models import User, Team
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Create team
    team = Team(
        name="Test Team",
        slug="test-team"
    )
    db_session.add(team)
    db_session.flush()

    # Create user
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=pwd_context.hash("password123"),
        role="admin",
        team_id=team.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    return user


@pytest.fixture(scope="function")
def auth_token(demo_user) -> str:
    """
    Generate JWT token for demo user
    """
    from jose import jwt
    from datetime import datetime, timedelta

    secret_key = os.getenv("JWT_SECRET_KEY", "test-secret-key")
    algorithm = "HS256"

    payload = {
        "sub": str(demo_user.id),
        "email": demo_user.email,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }

    return jwt.encode(payload, secret_key, algorithm=algorithm)


# =============================================================================
# MOCK PROVIDER FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def mock_email_client():
    """
    Mock email client fixture
    """
    from api.integrations.mock import sendgrid_mock

    # Clear any previous mock data
    sendgrid_mock.clear_mock_data()

    yield sendgrid_mock

    # Clean up after test
    sendgrid_mock.clear_mock_data()


@pytest.fixture(scope="function")
def mock_sms_client():
    """
    Mock SMS client fixture
    """
    from api.integrations.mock import twilio_mock

    # Clear any previous mock data
    twilio_mock.clear_mock_data()

    yield twilio_mock

    # Clean up after test
    twilio_mock.clear_mock_data()


@pytest.fixture(scope="function")
def mock_storage_client():
    """
    Mock storage client fixture
    """
    from api.integrations.mock import storage_mock

    # Clear any previous mock data
    storage_mock.clear_mock_data()

    yield storage_mock

    # Clean up after test
    storage_mock.clear_mock_data()


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def sample_property(db_session, demo_user):
    """
    Create sample property for testing
    """
    from db.models import Property

    prop = Property(
        address="123 Test Street",
        city="Test City",
        state="CA",
        zip_code="90210",
        owner_name="John Doe",
        owner_phone="+15551234567",
        owner_email="john@example.com",
        asking_price=500000,
        beds=3,
        baths=2.0,
        sqft=2000,
        stage="New Lead",
        team_id=demo_user.team_id,
        assigned_to_id=demo_user.id
    )

    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    return prop


@pytest.fixture(scope="function")
def sample_communication(db_session, sample_property, demo_user):
    """
    Create sample communication for testing
    """
    from db.models import Communication
    from datetime import datetime

    comm = Communication(
        property_id=sample_property.id,
        communication_type="email",
        direction="outbound",
        subject="Test Subject",
        body="Test email body",
        from_email=demo_user.email,
        to_email=sample_property.owner_email,
        status="sent",
        sent_at=datetime.utcnow(),
        team_id=demo_user.team_id
    )

    db_session.add(comm)
    db_session.commit()
    db_session.refresh(comm)

    return comm


# =============================================================================
# UTILITY FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def reset_mock_providers():
    """
    Automatically reset all mock providers before each test
    """
    from api.integrations.mock import sendgrid_mock, twilio_mock, storage_mock

    sendgrid_mock.clear_mock_data()
    twilio_mock.clear_mock_data()
    storage_mock.clear_mock_data()

    yield

    # Clean up after test
    sendgrid_mock.clear_mock_data()
    twilio_mock.clear_mock_data()
    storage_mock.clear_mock_data()


@pytest.fixture(scope="session")
def test_config():
    """
    Test configuration dictionary
    """
    return {
        "mock_mode": True,
        "testing": True,
        "db_dsn": os.getenv("DB_DSN"),
        "redis_url": os.getenv("REDIS_URL"),
        "jwt_secret": os.getenv("JWT_SECRET_KEY")
    }


# =============================================================================
# MARKERS
# =============================================================================

def pytest_configure(config):
    """
    Register custom markers
    """
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (database, redis, etc.)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full stack)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take >1 second"
    )
    config.addinivalue_line(
        "markers", "mock: Tests using mock providers"
    )
    config.addinivalue_line(
        "markers", "real: Tests requiring real API keys"
    )
    config.addinivalue_line(
        "markers", "smoke: Smoke tests (critical paths only)"
    )


# =============================================================================
# HOOKS
# =============================================================================

def pytest_collection_modifyitems(config, items):
    """
    Modify test collection

    - Auto-mark tests based on location
    - Skip tests requiring real credentials in mock mode
    """
    for item in items:
        # Auto-mark based on directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # Skip 'real' tests in mock mode
        if "real" in item.keywords and os.getenv("MOCK_MODE") == "true":
            item.add_marker(pytest.mark.skip(reason="Requires real API credentials"))


def pytest_report_header(config):
    """
    Add custom header to test report
    """
    return [
        f"Real Estate OS Test Suite",
        f"Mock Mode: {os.getenv('MOCK_MODE', 'false')}",
        f"Database: {os.getenv('DB_DSN', 'not configured')}",
        f"Redis: {os.getenv('REDIS_URL', 'not configured')}"
    ]
