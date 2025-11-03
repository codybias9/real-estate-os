"""
Tests for JWT token handler
"""

import pytest
from datetime import timedelta
import jwt
from jwt.exceptions import InvalidTokenError

from auth.jwt_handler import JWTHandler, TokenData


class TestJWTHandler:
    """Tests for JWTHandler class"""

    @pytest.fixture
    def handler(self):
        """Create JWT handler with test secret"""
        return JWTHandler(secret_key="test-secret-key", access_token_expire_minutes=30)

    def test_create_access_token(self, handler):
        """Test creating an access token"""
        token = handler.create_access_token(
            user_id="user-123",
            tenant_id="tenant-1",
            email="test@example.com",
            role="analyst",
        )

        assert token is not None
        assert isinstance(token, str)

        # Decode without verification to check payload
        payload = handler.decode_token_unsafe(token)
        assert payload["sub"] == "user-123"
        assert payload["tenant_id"] == "tenant-1"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "analyst"
        assert payload["type"] == "access"

    def test_create_refresh_token(self, handler):
        """Test creating a refresh token"""
        token = handler.create_refresh_token(
            user_id="user-123",
            tenant_id="tenant-1",
        )

        assert token is not None
        assert isinstance(token, str)

        # Decode without verification to check payload
        payload = handler.decode_token_unsafe(token)
        assert payload["sub"] == "user-123"
        assert payload["tenant_id"] == "tenant-1"
        assert payload["type"] == "refresh"

    def test_verify_access_token(self, handler):
        """Test verifying a valid access token"""
        token = handler.create_access_token(
            user_id="user-123",
            tenant_id="tenant-1",
            email="test@example.com",
            role="analyst",
        )

        token_data = handler.verify_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.user_id == "user-123"
        assert token_data.tenant_id == "tenant-1"
        assert token_data.email == "test@example.com"
        assert token_data.role == "analyst"

    def test_verify_expired_token(self, handler):
        """Test verifying an expired token"""
        # Create token that expires immediately
        token = handler.create_access_token(
            user_id="user-123",
            tenant_id="tenant-1",
            email="test@example.com",
            role="analyst",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(InvalidTokenError, match="Token has expired"):
            handler.verify_token(token)

    def test_verify_invalid_signature(self, handler):
        """Test verifying a token with invalid signature"""
        # Create token with different secret
        other_handler = JWTHandler(secret_key="other-secret")
        token = other_handler.create_access_token(
            user_id="user-123",
            tenant_id="tenant-1",
            email="test@example.com",
            role="analyst",
        )

        with pytest.raises(InvalidTokenError):
            handler.verify_token(token)

    def test_verify_refresh_token(self, handler):
        """Test verifying a refresh token"""
        token = handler.create_refresh_token(
            user_id="user-123",
            tenant_id="tenant-1",
        )

        token_data = handler.verify_refresh_token(token)

        assert token_data["user_id"] == "user-123"
        assert token_data["tenant_id"] == "tenant-1"

    def test_verify_access_token_as_refresh_fails(self, handler):
        """Test that access token cannot be used as refresh token"""
        token = handler.create_access_token(
            user_id="user-123",
            tenant_id="tenant-1",
            email="test@example.com",
            role="analyst",
        )

        with pytest.raises(InvalidTokenError, match="Invalid token type"):
            handler.verify_refresh_token(token)

    def test_verify_refresh_token_as_access_fails(self, handler):
        """Test that refresh token cannot be used as access token"""
        token = handler.create_refresh_token(
            user_id="user-123",
            tenant_id="tenant-1",
        )

        with pytest.raises(InvalidTokenError, match="Invalid token type"):
            handler.verify_token(token)

    def test_malformed_token(self, handler):
        """Test verifying a malformed token"""
        with pytest.raises(InvalidTokenError):
            handler.verify_token("not.a.valid.token")

    def test_token_without_required_claims(self, handler):
        """Test token missing required claims"""
        # Create token manually without required claims
        payload = {"sub": "user-123"}
        token = jwt.encode(payload, handler.secret_key, algorithm=handler.algorithm)

        with pytest.raises(InvalidTokenError):
            handler.verify_token(token)

    def test_custom_expiration(self, handler):
        """Test creating token with custom expiration"""
        token = handler.create_access_token(
            user_id="user-123",
            tenant_id="tenant-1",
            email="test@example.com",
            role="analyst",
            expires_delta=timedelta(hours=24),
        )

        token_data = handler.verify_token(token)
        assert token_data.user_id == "user-123"

        # Verify expiration is approximately 24 hours from now
        payload = handler.decode_token_unsafe(token)
        import time

        exp_delta = payload["exp"] - time.time()
        assert 23 * 3600 < exp_delta < 25 * 3600  # Between 23 and 25 hours
