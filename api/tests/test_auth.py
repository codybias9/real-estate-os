"""Tests for authentication endpoints."""

import pytest
from fastapi import status


@pytest.mark.auth
@pytest.mark.unit
class TestAuthentication:
    """Test authentication endpoints."""

    def test_register_user(self, client, organization):
        """Test user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "NewPass123!@#",
                "first_name": "New",
                "last_name": "User",
                "organization_name": "Test Org",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "newuser@example.com"

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.json()["detail"].lower()

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == test_user.email

    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "Test123!@#",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user(self, client, test_user, auth_headers):
        """Test getting current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, client, test_user):
        """Test token refresh."""
        # First login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )

        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password(self, client, test_user, auth_headers):
        """Test password change."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "Test123!@#",
                "new_password": "NewPass123!@#",
            },
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify new password works
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "NewPass123!@#",
            },
        )

        assert login_response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_current(self, client, auth_headers):
        """Test password change with wrong current password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewPass123!@#",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_request(self, client, test_user):
        """Test password reset request."""
        response = client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": test_user.email},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_password_reset_nonexistent_email(self, client):
        """Test password reset for nonexistent email."""
        response = client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": "nonexistent@example.com"},
        )

        # Should still return 204 to prevent user enumeration
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.auth
@pytest.mark.slow
class TestAuthenticationSecurity:
    """Test authentication security features."""

    def test_progressive_login_delays(self, client, test_user):
        """Test progressive delays on failed login attempts."""
        import time

        # Multiple failed login attempts
        for i in range(3):
            start_time = time.time()
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "WrongPassword",
                },
            )
            elapsed = time.time() - start_time

            # First attempt should have no delay (< 0.5s)
            # Second should have ~1s delay
            # Third should have ~2s delay
            if i == 0:
                assert elapsed < 0.5
            elif i == 1:
                assert 0.8 < elapsed < 1.5
            elif i == 2:
                assert 1.5 < elapsed < 2.5

    def test_account_lockout(self, client, test_user, db_session):
        """Test account lockout after max failed attempts."""
        # Make 5 failed login attempts
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "WrongPassword",
                },
            )

        # 6th attempt should be locked
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "locked" in response.json()["detail"].lower()

    def test_jwt_token_contains_user_id(self, client, test_user):
        """Test that JWT token contains user ID."""
        from jose import jwt
        from ..config import settings

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )

        token = login_response.json()["access_token"]
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert payload["sub"] == test_user.id
        assert payload["type"] == "access"

    def test_refresh_token_different_from_access(self, client, test_user):
        """Test that refresh token is different from access token."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123!@#",
            },
        )

        data = login_response.json()
        assert data["access_token"] != data["refresh_token"]

        # Verify refresh token has correct type
        from jose import jwt
        from ..config import settings

        refresh_payload = jwt.decode(
            data["refresh_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert refresh_payload["type"] == "refresh"
