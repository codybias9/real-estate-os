"""Tests for authentication system (PR#1)

Tests:
- User registration
- User login
- JWT token validation
- API key creation and validation
- Rate limiting
- Role-based access control
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os

# Set test JWT secret before importing app
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

from api.main import app
from api.app.database import get_db
from db.models import Base
from db.models_auth import User, APIKey
from db.models_provenance import Tenant

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create test database for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ============================================================================
# Registration Tests
# ============================================================================

def test_register_new_user(test_db):
    """Test user registration creates tenant and user"""
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepass123",
            "tenant_name": "Test Organization"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800  # 30 minutes


def test_register_duplicate_email(test_db):
    """Test registration with existing email fails"""
    # Register first user
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepass123",
            "tenant_name": "Test Organization"
        }
    )

    # Try to register same email
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "different123",
            "tenant_name": "Another Organization"
        }
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_register_weak_password(test_db):
    """Test registration with weak password fails"""
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "short",
            "tenant_name": "Test Organization"
        }
    )

    assert response.status_code == 400
    assert "8 characters" in response.json()["detail"]


# ============================================================================
# Login Tests
# ============================================================================

def test_login_success(test_db):
    """Test login with correct credentials"""
    # Register user
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepass123",
            "tenant_name": "Test Organization"
        }
    )

    # Login
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "securepass123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(test_db):
    """Test login with incorrect password"""
    # Register user
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepass123",
            "tenant_name": "Test Organization"
        }
    )

    # Login with wrong password
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(test_db):
    """Test login with non-existent email"""
    response = client.post(
        "/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "somepassword"
        }
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


# ============================================================================
# Protected Endpoint Tests
# ============================================================================

def test_get_me_authenticated(test_db):
    """Test /auth/me with valid token"""
    # Register and get token
    register_response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepass123",
            "tenant_name": "Test Organization"
        }
    )
    token = register_response.json()["access_token"]

    # Get user info
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "tenant_id" in data
    assert "owner" in data["roles"]


def test_get_me_no_token(test_db):
    """Test /auth/me without token"""
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()


def test_get_me_invalid_token(test_db):
    """Test /auth/me with invalid token"""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token-here"}
    )

    assert response.status_code == 401


# ============================================================================
# API Key Tests
# ============================================================================

def test_create_api_key(test_db):
    """Test API key creation"""
    # Register and get token
    register_response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepass123",
            "tenant_name": "Test Organization"
        }
    )
    token = register_response.json()["access_token"]

    # Create API key
    response = client.post(
        "/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Service API Key",
            "description": "For automated tasks",
            "roles": ["service"]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "key" in data
    assert data["name"] == "Service API Key"
    assert "service" in data["roles"]
    assert len(data["key"]) > 40  # API key should be long


def test_list_api_keys(test_db):
    """Test listing API keys"""
    # Register and get token
    register_response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepass123",
            "tenant_name": "Test Organization"
        }
    )
    token = register_response.json()["access_token"]

    # Create API key
    client.post(
        "/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Service API Key",
            "roles": ["service"]
        }
    )

    # List API keys
    response = client.get(
        "/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Service API Key"
    assert "key" not in data[0]  # Full key should not be in list


def test_revoke_api_key(test_db):
    """Test API key revocation"""
    # Register and get token
    register_response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepass123",
            "tenant_name": "Test Organization"
        }
    )
    token = register_response.json()["access_token"]

    # Create API key
    create_response = client.post(
        "/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Service API Key",
            "roles": ["service"]
        }
    )
    key_id = create_response.json()["id"]

    # Revoke API key
    response = client.delete(
        f"/auth/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 204


# ============================================================================
# Rate Limiting Tests
# ============================================================================

def test_rate_limit_per_ip(test_db):
    """Test per-IP rate limiting (simplified test)"""
    # This test is simplified - in production, you'd want to test actual rate limiting
    # by making many rapid requests

    # Make a request to check rate limit headers are present
    response = client.get("/healthz")

    assert response.status_code == 200
    assert "X-RateLimit-Limit-IP" in response.headers
    assert "X-RateLimit-Remaining-IP" in response.headers


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
