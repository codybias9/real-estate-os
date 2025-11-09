"""
Tests for authentication endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app

client = TestClient(app)


class TestAuthEndpoints:
    """Tests for authentication API endpoints"""

    def test_login_success(self):
        """Test successful login"""
        response = client.post(
            "/v1/auth/login",
            json={"email": "analyst@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post(
            "/v1/auth/login",
            json={"email": "analyst@example.com", "password": "wrong-password"},
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self):
        """Test login with nonexistent user"""
        response = client.post(
            "/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )

        assert response.status_code == 401

    def test_login_invalid_email_format(self):
        """Test login with invalid email format"""
        response = client.post(
            "/v1/auth/login",
            json={"email": "not-an-email", "password": "password123"},
        )

        assert response.status_code == 422  # Validation error

    def test_get_me_authenticated(self):
        """Test getting current user with valid token"""
        # Login first
        login_response = client.post(
            "/v1/auth/login",
            json={"email": "analyst@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "analyst@example.com"
        assert data["role"] == "analyst"
        assert "id" in data
        assert "tenant_id" in data

    def test_get_me_no_token(self):
        """Test getting current user without token"""
        response = client.get("/v1/auth/me")

        assert response.status_code == 403  # No credentials

    def test_get_me_invalid_token(self):
        """Test getting current user with invalid token"""
        response = client.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    def test_refresh_token(self):
        """Test refreshing access token"""
        # Login first
        login_response = client.post(
            "/v1/auth/login",
            json={"email": "analyst@example.com", "password": "password123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_invalid(self):
        """Test refreshing with invalid refresh token"""
        response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": "invalid-refresh-token"},
        )

        assert response.status_code == 401

    def test_refresh_token_using_access_token_fails(self):
        """Test that access token cannot be used for refresh"""
        # Login first
        login_response = client.post(
            "/v1/auth/login",
            json={"email": "analyst@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Try to use access token for refresh
        response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]

    def test_protected_endpoint(self):
        """Test accessing protected endpoint"""
        # Login first
        login_response = client.post(
            "/v1/auth/login",
            json={"email": "analyst@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/v1/auth/protected",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "user_id" in data
        assert "tenant_id" in data
        assert "role" in data

    def test_protected_endpoint_no_auth(self):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/v1/auth/protected")

        assert response.status_code == 403

    def test_logout(self):
        """Test logout endpoint"""
        # Login first
        login_response = client.post(
            "/v1/auth/login",
            json={"email": "analyst@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

    def test_admin_login(self):
        """Test admin user login"""
        response = client.post(
            "/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )

        assert response.status_code == 200
        access_token = response.json()["access_token"]

        # Verify admin role
        me_response = client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.json()["role"] == "admin"
