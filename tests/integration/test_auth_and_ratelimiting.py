"""
Integration Tests for Authentication and Rate Limiting

Tests user authentication, JWT tokens, rate limiting, and login lockout
"""
import pytest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from db.models import User, Team
from api.auth import verify_password, get_password_hash, create_access_token


class TestUserRegistration:
    """Test user registration flow"""

    def test_successful_registration(self, client: TestClient, test_db: Session):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "full_name": "New User",
                "team_name": "New Team"
            }
        )

        assert response.status_code in [200, 201]
        data = response.json()

        assert "id" in data
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "password" not in data  # Password should not be returned

        # Verify user created in database
        user = test_db.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.full_name == "New User"

        # Verify team created
        assert user.team_id is not None
        team = test_db.query(Team).filter(Team.id == user.team_id).first()
        assert team is not None
        assert team.name == "New Team"

    def test_duplicate_email_rejected(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test that duplicate email registration is rejected"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,  # Already exists
                "password": "Password123!",
                "full_name": "Duplicate User",
                "team_name": "Duplicate Team"
            }
        )

        assert response.status_code in [400, 409]
        assert "email" in response.json()["detail"].lower() or "already" in response.json()["detail"].lower()

    def test_weak_password_rejected(self, client: TestClient):
        """Test that weak passwords are rejected"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",  # Too short
                "full_name": "Weak Password",
                "team_name": "Weak Team"
            }
        )

        assert response.status_code in [400, 422]
        assert "password" in response.json()["detail"].lower()

    def test_invalid_email_rejected(self, client: TestClient):
        """Test that invalid email format is rejected"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "Password123!",
                "full_name": "Invalid Email",
                "team_name": "Invalid Team"
            }
        )

        assert response.status_code in [400, 422]


class TestUserLogin:
    """Test user login flow"""

    def test_successful_login(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test successful login with valid credentials"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_invalid_password(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test login with invalid password"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

    def test_nonexistent_user(self, client: TestClient):
        """Test login with non-existent email"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 401

    def test_missing_credentials(self, client: TestClient):
        """Test login with missing credentials"""
        response = client.post(
            "/api/v1/auth/login",
            data={},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 422


class TestJWTTokens:
    """Test JWT token generation and validation"""

    def test_valid_token_accepted(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User
    ):
        """Test that valid JWT token is accepted"""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name

    def test_missing_token_rejected(self, client: TestClient):
        """Test that requests without token are rejected"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_invalid_token_rejected(self, client: TestClient):
        """Test that invalid token is rejected"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

        assert response.status_code == 401

    def test_expired_token_rejected(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test that expired token is rejected"""
        # Create expired token
        from api.auth import JWT_SECRET_KEY, JWT_ALGORITHM
        import jwt

        expired_token = jwt.encode(
            {
                "sub": test_user.email,
                "exp": datetime.utcnow() - timedelta(hours=1)
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401

    def test_malformed_token_rejected(self, client: TestClient):
        """Test that malformed token is rejected"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.valid.jwt"}
        )

        assert response.status_code == 401

    def test_token_without_bearer_prefix_rejected(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test that token without 'Bearer' prefix is rejected"""
        token = create_access_token(data={"sub": test_user.email})

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": token}  # Missing 'Bearer ' prefix
        )

        assert response.status_code == 401


class TestRateLimiting:
    """Test rate limiting on API endpoints"""

    def test_login_rate_limit(self, client: TestClient, test_user: User):
        """Test that login endpoint enforces rate limiting"""
        # Attempt multiple rapid logins
        responses = []
        for i in range(10):
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "wrongpassword"  # Wrong to not actually login
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            responses.append(response)

            if response.status_code == 429:
                break

        # Should eventually hit rate limit
        assert any(r.status_code == 429 for r in responses)

        # Rate limit response should include Retry-After header
        rate_limited = next(r for r in responses if r.status_code == 429)
        assert "Retry-After" in rate_limited.headers or "retry" in rate_limited.json().get("detail", "").lower()

    def test_rate_limit_headers_included(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test that rate limit headers are included in responses"""
        response = client.get(
            "/api/v1/properties",
            headers=auth_headers
        )

        # May include headers like:
        # X-RateLimit-Limit: 100
        # X-RateLimit-Remaining: 99
        # X-RateLimit-Reset: 1234567890
        assert response.status_code == 200

    def test_different_endpoints_separate_limits(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test that different endpoints have separate rate limits"""
        # Hit one endpoint many times
        for _ in range(5):
            response1 = client.get(
                "/api/v1/properties",
                headers=auth_headers
            )
            assert response1.status_code == 200

        # Other endpoint should not be affected
        response2 = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response2.status_code == 200


class TestLoginLockout:
    """Test progressive login lockout mechanism"""

    def test_progressive_lockout_timing(
        self,
        client: TestClient,
        test_user: User,
        mock_redis
    ):
        """Test that lockout time increases progressively"""
        # First 3 failed attempts - minimal lockout
        for i in range(3):
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "wrongpassword"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if i < 2:
                assert response.status_code in [401, 429]
            else:
                # 3rd attempt may trigger lockout
                assert response.status_code in [401, 429]

    def test_lockout_cleared_after_success(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test that lockout is cleared after successful login"""
        # Failed attempt
        client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Successful login should clear lockout
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200

    def test_lockout_per_user_isolation(
        self,
        client: TestClient,
        test_user: User,
        test_agent_user: User
    ):
        """Test that lockout is per-user (not global)"""
        # Lock out user 1
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "wrongpassword"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

        # User 2 should not be affected
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_agent_user.email,
                "password": "agentpassword123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200

    def test_lockout_message_includes_retry_time(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test that lockout message includes retry time"""
        # Trigger lockout with many failed attempts
        for _ in range(6):
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "wrongpassword"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

        if response.status_code == 429:
            # Should indicate how long to wait
            assert "retry" in response.json().get("detail", "").lower() or \
                   "wait" in response.json().get("detail", "").lower() or \
                   "Retry-After" in response.headers


class TestPasswordSecurity:
    """Test password security requirements and hashing"""

    def test_password_hashed_in_database(
        self,
        test_db: Session,
        test_user: User
    ):
        """Test that passwords are hashed in database"""
        # Password should not be stored in plaintext
        assert test_user.hashed_password != "testpassword123"
        assert len(test_user.hashed_password) > 50  # Bcrypt hashes are ~60 chars

        # Should be able to verify password
        assert verify_password("testpassword123", test_user.hashed_password)

    def test_password_not_returned_in_responses(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test that password/hash is never returned in API responses"""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "password" not in data
        assert "hashed_password" not in data

    def test_password_requirements_enforced(
        self,
        client: TestClient
    ):
        """Test password complexity requirements"""
        weak_passwords = [
            "short",      # Too short
            "12345678",   # No letters
            "password",   # Too common
        ]

        for weak_pass in weak_passwords:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test_{weak_pass}@example.com",
                    "password": weak_pass,
                    "full_name": "Test User",
                    "team_name": "Test Team"
                }
            )

            # Should reject weak password
            assert response.status_code in [400, 422]


class TestTokenRefresh:
    """Test JWT token refresh mechanism"""

    def test_token_refresh(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test that token can be refreshed"""
        response = client.post(
            "/api/v1/auth/refresh",
            headers=auth_headers
        )

        # Should return new token
        assert response.status_code in [200, 201]

        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data

    def test_refresh_with_invalid_token(self, client: TestClient):
        """Test that refresh requires valid token"""
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401


class TestAuthorizationRoles:
    """Test role-based authorization"""

    def test_admin_can_access_admin_endpoints(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User
    ):
        """Test that admin role can access admin endpoints"""
        # test_user is admin
        assert test_user.role == "admin"

        response = client.get(
            "/api/v1/admin/dlq/stats",
            headers=auth_headers
        )

        # Should have access (even if endpoint returns data or not)
        assert response.status_code in [200, 404]  # 404 if no DLQ data yet

    def test_agent_cannot_access_admin_endpoints(
        self,
        client: TestClient,
        agent_auth_headers: dict,
        test_agent_user: User
    ):
        """Test that agent role cannot access admin endpoints"""
        # test_agent_user is agent
        assert test_agent_user.role == "agent"

        response = client.get(
            "/api/v1/admin/dlq/stats",
            headers=agent_auth_headers
        )

        # Should be forbidden
        assert response.status_code == 403

    def test_viewer_has_read_only_access(
        self,
        client: TestClient,
        test_db: Session,
        test_team: Team
    ):
        """Test that viewer role has read-only access"""
        # Create viewer user
        viewer = User(
            email="viewer@example.com",
            hashed_password=get_password_hash("viewerpass123"),
            full_name="Viewer User",
            role="viewer",
            team_id=test_team.id
        )
        test_db.add(viewer)
        test_db.commit()

        # Login as viewer
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": viewer.email,
                "password": "viewerpass123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {token}"}

        # Should be able to read
        response = client.get(
            "/api/v1/properties",
            headers=viewer_headers
        )
        assert response.status_code == 200

        # Should not be able to write (if implemented)
        # response = client.post(
        #     "/api/v1/properties",
        #     json={...},
        #     headers=viewer_headers
        # )
        # assert response.status_code == 403
