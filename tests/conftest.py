"""
Pytest Configuration and Shared Fixtures
"""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from api.main import app
from api.database import get_db, Base
from db.models import User, Team, Property, PropertyStage
from api.auth import get_password_hash, create_access_token

# ============================================================================
# TEST DATABASE SETUP
# ============================================================================

# Use in-memory SQLite for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    Create a fresh test database for each test
    """
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db: Session) -> TestClient:
    """
    Create a test client with dependency override for database
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
def test_team(test_db: Session) -> Team:
    """Create a test team"""
    team = Team(
        name="Test Team",
        settings={"timezone": "America/New_York"}
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)
    return team


@pytest.fixture
def test_user(test_db: Session, test_team: Team) -> User:
    """Create a test user"""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role="admin",
        team_id=test_team.id
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_agent_user(test_db: Session, test_team: Team) -> User:
    """Create a test agent user"""
    user = User(
        email="agent@example.com",
        hashed_password=get_password_hash("agentpassword123"),
        full_name="Test Agent",
        role="agent",
        team_id=test_team.id
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user"""
    access_token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def agent_auth_headers(test_agent_user: User) -> dict:
    """Create authentication headers for agent user"""
    access_token = create_access_token(data={"sub": test_agent_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_property(test_db: Session, test_team: Team, test_user: User) -> Property:
    """Create a test property"""
    property = Property(
        team_id=test_team.id,
        address="123 Test St",
        city="Test City",
        state="CA",
        zip_code="12345",
        owner_name="Test Owner",
        bird_dog_score=0.75,
        current_stage=PropertyStage.NEW,
        assigned_user_id=test_user.id,
        tags=["test", "sample"]
    )
    test_db.add(property)
    test_db.commit()
    test_db.refresh(property)
    return property


@pytest.fixture
def test_properties(test_db: Session, test_team: Team, test_user: User) -> list[Property]:
    """Create multiple test properties across different stages"""
    properties = []
    stages = [
        PropertyStage.NEW,
        PropertyStage.OUTREACH,
        PropertyStage.QUALIFIED,
        PropertyStage.NEGOTIATION,
        PropertyStage.UNDER_CONTRACT,
    ]

    for i, stage in enumerate(stages):
        prop = Property(
            team_id=test_team.id,
            address=f"{100 + i} Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
            owner_name=f"Owner {i}",
            bird_dog_score=0.5 + (i * 0.1),
            current_stage=stage,
            assigned_user_id=test_user.id,
        )
        test_db.add(prop)
        properties.append(prop)

    test_db.commit()
    for prop in properties:
        test_db.refresh(prop)

    return properties


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis for testing rate limiting"""
    class MockRedis:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def setex(self, key, ttl, value):
            self.data[key] = value

        def incr(self, key):
            self.data[key] = self.data.get(key, 0) + 1
            return self.data[key]

        def expire(self, key, ttl):
            pass

        def delete(self, key):
            if key in self.data:
                del self.data[key]

    mock = MockRedis()
    return mock


@pytest.fixture
def mock_celery(monkeypatch):
    """Mock Celery for testing task queueing"""
    class MockTask:
        def __init__(self):
            self.called_tasks = []

        def apply_async(self, args=None, kwargs=None, queue=None):
            self.called_tasks.append({
                "args": args,
                "kwargs": kwargs,
                "queue": queue
            })
            return self

        @property
        def id(self):
            return "mock-task-id"

    mock = MockTask()
    return mock


# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("DATABASE_URL", SQLALCHEMY_TEST_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
