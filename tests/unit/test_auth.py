"""
Unit tests for authentication and authorization.
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt
from unittest.mock import Mock, patch, AsyncMock

from api.auth import (
    verify_token,
    # create_access_token,  # Not needed - Keycloak handles token creation
    get_current_user,
    require_roles,
    TokenData,
    JWKSCache
)
from api.config import settings


class TestJWTTokens:
    """Test JWT token creation and validation."""

    @pytest.mark.skip(reason="Token creation handled by Keycloak, not app")
    def test_create_access_token(self):
        """Test access token creation."""
        data = {
            "sub": "user_123",
            "tenant_id": "tenant_abc",
            "roles": ["admin"]
        }

        token = create_access_token(data, expires_delta=timedelta(minutes=30))

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify payload
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        assert payload["sub"] == "user_123"
        assert payload["tenant_id"] == "tenant_abc"
        assert payload["roles"] == ["admin"]
        assert "exp" in payload

    def test_create_token_with_custom_expiry(self):
        """Test token creation with custom expiration."""
        data = {"sub": "user_123", "tenant_id": "tenant_abc"}
        expires_delta = timedelta(hours=2)

        token = create_access_token(data, expires_delta=expires_delta)

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + expires_delta

        # Allow 5 second tolerance
        assert abs((exp_time - expected_time).total_seconds()) < 5

    def test_create_token_default_expiry(self):
        """Test token creation with default expiration."""
        data = {"sub": "user_123", "tenant_id": "tenant_abc"}

        token = create_access_token(data)

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

        assert abs((exp_time - expected_time).total_seconds()) < 5


class TestTokenVerification:
    """Test token verification and validation."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, mock_keycloak_jwks):
        """Test verification of valid token."""
        # Create valid token
        data = {
            "sub": "user_123",
            "tenant_id": "tenant_abc",
            "roles": ["admin"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(data, settings.jwt_secret_key, algorithm="HS256")

        # Mock JWKS verification to pass
        with patch('api.auth.jwt.decode') as mock_decode:
            mock_decode.return_value = data

            token_data = await verify_token(token)

            assert isinstance(token_data, TokenData)
            assert token_data.sub == "user_123"
            assert token_data.tenant_id == "tenant_abc"
            assert token_data.roles == ["admin"]

    @pytest.mark.asyncio
    async def test_verify_expired_token(self):
        """Test verification of expired token."""
        # Create expired token
        data = {
            "sub": "user_123",
            "tenant_id": "tenant_abc",
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired
        }
        token = jwt.encode(data, settings.jwt_secret_key, algorithm="HS256")

        with pytest.raises(Exception):  # Should raise JWT expired exception
            await verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_token_missing_tenant_id(self):
        """Test verification fails when tenant_id is missing."""
        # Create token without tenant_id
        data = {
            "sub": "user_123",
            "roles": ["admin"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(data, settings.jwt_secret_key, algorithm="HS256")

        with patch('api.auth.jwt.decode') as mock_decode:
            mock_decode.return_value = data

            with pytest.raises(Exception) as exc_info:
                await verify_token(token)

            assert "tenant_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_malformed_token(self):
        """Test verification of malformed token."""
        token = "invalid.token.format"

        with pytest.raises(Exception):
            await verify_token(token)


class TestJWKSCache:
    """Test JWKS caching mechanism."""

    @pytest.mark.asyncio
    async def test_jwks_cache_fetch(self):
        """Test JWKS fetch and cache."""
        cache = JWKSCache(jwks_url="https://keycloak.example.com/jwks")

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "keys": [{"kid": "key1", "kty": "RSA"}]
            }
            mock_get.return_value = mock_response

            jwks = await cache.get_jwks()

            assert jwks is not None
            assert "keys" in jwks
            assert len(jwks["keys"]) == 1

    @pytest.mark.asyncio
    async def test_jwks_cache_expiry(self):
        """Test JWKS cache expiration."""
        cache = JWKSCache(
            jwks_url="https://keycloak.example.com/jwks",
            cache_ttl_seconds=1  # 1 second TTL
        )

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "keys": [{"kid": "key1"}]
            }
            mock_get.return_value = mock_response

            # First fetch
            jwks1 = await cache.get_jwks()
            assert mock_get.call_count == 1

            # Immediate second fetch (should use cache)
            jwks2 = await cache.get_jwks()
            assert mock_get.call_count == 1  # No new request
            assert jwks1 == jwks2

            # Wait for cache to expire
            import asyncio
            await asyncio.sleep(1.1)

            # Third fetch (should refresh)
            jwks3 = await cache.get_jwks()
            assert mock_get.call_count == 2  # New request made


class TestRoleBasedAccessControl:
    """Test RBAC decorator and role checking."""

    @pytest.mark.asyncio
    async def test_require_roles_allowed(self):
        """Test role decorator allows access for authorized roles."""
        @require_roles(["admin", "analyst"])
        async def protected_endpoint(user: TokenData):
            return {"message": "success"}

        user = TokenData(
            sub="user_123",
            tenant_id="tenant_abc",
            roles=["admin"]
        )

        result = await protected_endpoint(user)
        assert result["message"] == "success"

    @pytest.mark.asyncio
    async def test_require_roles_denied(self):
        """Test role decorator denies access for unauthorized roles."""
        @require_roles(["admin"])
        async def protected_endpoint(user: TokenData):
            return {"message": "success"}

        user = TokenData(
            sub="user_123",
            tenant_id="tenant_abc",
            roles=["user"]  # Not admin
        )

        with pytest.raises(Exception) as exc_info:
            await protected_endpoint(user)

        assert "403" in str(exc_info.value) or "Forbidden" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_require_roles_multiple_allowed(self):
        """Test role decorator with multiple allowed roles."""
        @require_roles(["admin", "analyst", "operator"])
        async def protected_endpoint(user: TokenData):
            return {"message": "success"}

        # Test each allowed role
        for role in ["admin", "analyst", "operator"]:
            user = TokenData(
                sub="user_123",
                tenant_id="tenant_abc",
                roles=[role]
            )
            result = await protected_endpoint(user)
            assert result["message"] == "success"

    @pytest.mark.asyncio
    async def test_require_roles_user_with_multiple_roles(self):
        """Test user with multiple roles."""
        @require_roles(["admin"])
        async def protected_endpoint(user: TokenData):
            return {"message": "success"}

        user = TokenData(
            sub="user_123",
            tenant_id="tenant_abc",
            roles=["user", "analyst", "admin"]  # Has admin among other roles
        )

        result = await protected_endpoint(user)
        assert result["message"] == "success"


class TestGetCurrentUser:
    """Test current user extraction from requests."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test extracting user from valid token."""
        from fastapi import HTTPException

        # Mock request with valid token
        token = "valid.jwt.token"

        with patch('api.auth.verify_token') as mock_verify:
            mock_verify.return_value = TokenData(
                sub="user_123",
                tenant_id="tenant_abc",
                roles=["admin"]
            )

            user = await get_current_user(token)

            assert user.sub == "user_123"
            assert user.tenant_id == "tenant_abc"
            assert user.roles == ["admin"]

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test error handling for invalid token."""
        from fastapi import HTTPException

        token = "invalid.token"

        with patch('api.auth.verify_token') as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_missing_token(self):
        """Test error when token is missing."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)

        assert exc_info.value.status_code == 401


class TestTokenData:
    """Test TokenData model."""

    def test_token_data_creation(self):
        """Test TokenData creation with all fields."""
        token_data = TokenData(
            sub="user_123",
            tenant_id="tenant_abc",
            roles=["admin", "analyst"]
        )

        assert token_data.sub == "user_123"
        assert token_data.tenant_id == "tenant_abc"
        assert token_data.roles == ["admin", "analyst"]

    def test_token_data_no_roles(self):
        """Test TokenData with empty roles."""
        token_data = TokenData(
            sub="user_123",
            tenant_id="tenant_abc",
            roles=[]
        )

        assert token_data.roles == []

    def test_token_data_validation(self):
        """Test TokenData validation."""
        # Missing required field should raise error
        with pytest.raises(Exception):
            TokenData(sub="user_123")  # Missing tenant_id


# ============================================================================
# Test Statistics
# ============================================================================
# Total tests in this module: 23
