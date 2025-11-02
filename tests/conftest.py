"""
Pytest configuration and shared fixtures for the test suite.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient
import fakeredis.aioredis
from unittest.mock import Mock, patch

from api.main import app
from api.database import Base, get_db, set_tenant_context
from api.config import settings
from api.qdrant_client import QdrantClient
from api.minio_client import MinIOClient
from api.redis_client import RedisClient


# ============================================================================
# Test Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    # Use in-memory SQLite for fast tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def tenant_id() -> str:
    """Generate test tenant ID."""
    return str(uuid4())


@pytest.fixture
def user_id() -> str:
    """Generate test user ID."""
    return str(uuid4())


@pytest.fixture
async def tenant_db_session(db_session: AsyncSession, tenant_id: str) -> AsyncSession:
    """Create database session with tenant context set."""
    await set_tenant_context(db_session, tenant_id)
    return db_session


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test API client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_jwt_token(tenant_id: str, user_id: str) -> str:
    """Generate mock JWT token for testing."""
    import jwt
    from datetime import datetime, timedelta

    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": ["admin"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }

    # Use HS256 for testing (simpler than RS256)
    token = jwt.encode(payload, "test-secret", algorithm="HS256")
    return token


@pytest.fixture
def auth_headers(mock_jwt_token: str) -> dict:
    """Create authorization headers for API requests."""
    return {
        "Authorization": f"Bearer {mock_jwt_token}"
    }


# ============================================================================
# Storage Service Fixtures
# ============================================================================

@pytest.fixture
async def mock_redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Create mock Redis client."""
    redis = fakeredis.aioredis.FakeRedis()
    yield redis
    await redis.close()


@pytest.fixture
def mock_qdrant():
    """Create mock Qdrant client."""
    with patch('api.qdrant_client.BaseQdrantClient') as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_minio():
    """Create mock MinIO client."""
    with patch('api.minio_client.Minio') as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def temp_file():
    """Create temporary file for tests."""
    import tempfile
    import os

    # Create temp file
    fd, path = tempfile.mkstemp(suffix='.pdf')
    os.write(fd, b'Test file content')
    os.close(fd)

    yield path

    # Cleanup
    try:
        os.unlink(path)
    except OSError:
        pass


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_property_data(tenant_id: str) -> dict:
    """Generate sample property data."""
    return {
        "tenant_id": tenant_id,
        "address": "123 Main St, Austin, TX 78701",
        "latitude": 30.2672,
        "longitude": -97.7431,
        "property_type": "single_family",
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 1500,
        "lot_size_sqft": 5000,
        "year_built": 2010,
        "zoning": "R1",
        "listing_price": 450000,
        "assessed_value": 425000
    }


@pytest.fixture
def sample_prospect_data(tenant_id: str) -> dict:
    """Generate sample prospect data."""
    return {
        "tenant_id": tenant_id,
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-512-555-1234",
        "source": "website",
        "status": "new",
        "budget_min": 400000,
        "budget_max": 600000,
        "location_preferences": ["Austin", "Round Rock"]
    }


@pytest.fixture
def sample_offer_data(tenant_id: str, property_id: str) -> dict:
    """Generate sample offer data."""
    return {
        "tenant_id": tenant_id,
        "property_id": property_id,
        "prospect_id": str(uuid4()),
        "offer_amount": 475000,
        "earnest_money": 5000,
        "financing_type": "conventional",
        "closing_days": 30,
        "contingencies": ["inspection", "financing"],
        "status": "pending"
    }


@pytest.fixture
def sample_vector() -> list[float]:
    """Generate sample embedding vector (768-dimensional)."""
    import numpy as np
    return np.random.random(768).tolist()


# ============================================================================
# Pipeline Test Fixtures
# ============================================================================

@pytest.fixture
def sample_pipeline_properties() -> list[dict]:
    """Generate sample properties for pipeline testing."""
    return [
        {
            "id": "prop_001",
            "address": "123 Main St, Austin, TX",
            "price": 450000
        },
        {
            "id": "prop_002",
            "address": "456 Oak Ave, Austin, TX",
            "price": 625000
        },
        {
            "id": "prop_003",
            "address": "789 Elm Rd, Austin, TX",
            "price": 550000
        }
    ]


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_keycloak_jwks():
    """Mock Keycloak JWKS endpoint."""
    with patch('api.auth.jwks_cache.get_jwks') as mock:
        # Mock JWKS response
        mock.return_value = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "test-key-id",
                    "use": "sig",
                    "n": "test-modulus",
                    "e": "AQAB"
                }
            ]
        }
        yield mock


@pytest.fixture
def mock_google_geocoding():
    """Mock Google Geocoding API."""
    with patch('requests.get') as mock:
        mock.return_value.json.return_value = {
            "results": [
                {
                    "geometry": {
                        "location": {
                            "lat": 30.2672,
                            "lng": -97.7431
                        }
                    },
                    "formatted_address": "123 Main St, Austin, TX 78701, USA"
                }
            ],
            "status": "OK"
        }
        yield mock


@pytest.fixture
def mock_fema_api():
    """Mock FEMA NFHL API."""
    with patch('requests.get') as mock:
        mock.return_value.json.return_value = {
            "features": [
                {
                    "attributes": {
                        "FLD_ZONE": "AE",
                        "ZONE_SUBTY": "FLOODWAY",
                        "SFHA_TF": "T"
                    }
                }
            ]
        }
        yield mock


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup resources after each test."""
    yield
    # Add any cleanup logic here
    pass


# ============================================================================
# Marker Definitions
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_db: Tests requiring database")
    config.addinivalue_line("markers", "requires_redis: Tests requiring Redis")
    config.addinivalue_line("markers", "requires_qdrant: Tests requiring Qdrant")
    config.addinivalue_line("markers", "requires_minio: Tests requiring MinIO")


def pytest_runtest_setup(item):
    """Skip tests based on markers when dependencies unavailable."""
    # Skip database tests if aiosqlite not available
    if item.get_closest_marker("requires_db"):
        try:
            import aiosqlite
        except ImportError:
            pytest.skip("aiosqlite not installed - database tests skipped")
