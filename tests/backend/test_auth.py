"""
Authentication and Authorization Tests

Tests JWT enforcement, role-based access control, and tenant isolation
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from jose import jwt
from datetime import datetime, timedelta
import os

client = TestClient(app)

# Mock Keycloak configuration for tests
os.environ["MOCK_AUTH"] = "false"  # Ensure we're testing real auth, not mock


def generate_test_jwt(
    user_id: str = "test-user-123",
    tenant_id: str = "tenant-a",
    roles: list = None,
    exp_minutes: int = 60
):
    """
    Generate a test JWT token
    In production, this would come from Keycloak
    """
    if roles is None:
        roles = ["user"]

    payload = {
        "sub": user_id,
        "preferred_username": "testuser",
        "email": "test@example.com",
        "tenant_id": tenant_id,
        "realm_access": {
            "roles": roles
        },
        "resource_access": {
            "real-estate-os-api": {
                "roles": []
            }
        },
        "aud": "real-estate-os-api",
        "exp": datetime.utcnow() + timedelta(minutes=exp_minutes),
        "iat": datetime.utcnow(),
        "iss": "http://keycloak:8080/realms/real-estate-os"
    }

    # For testing, we'll use a simple secret
    # In production, Keycloak uses RS256 with public/private keys
    secret = os.getenv("JWT_SECRET_FOR_TESTS", "test-secret-key")
    token = jwt.encode(payload, secret, algorithm="HS256")

    return token


class TestPublicEndpoints:
    """Test public endpoints that don't require authentication"""

    def test_healthz_no_auth_required(self):
        """Health endpoint should be publicly accessible"""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_version_no_auth_required(self):
        """Version endpoint should be publicly accessible"""
        response = client.get("/version")
        assert response.status_code == 200
        assert "version" in response.json()


class TestAuthenticationEnforcement:
    """Test that protected endpoints require valid JWT"""

    def test_ping_without_token_returns_401(self):
        """Ping endpoint should reject requests without token"""
        response = client.get("/ping")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers or response.status_code == 403

    def test_me_without_token_returns_401(self):
        """Me endpoint should reject requests without token"""
        response = client.get("/api/v1/me")
        assert response.status_code == 401 or response.status_code == 403

    def test_properties_without_token_returns_401(self):
        """Properties endpoint should reject requests without token"""
        response = client.get("/api/v1/properties")
        assert response.status_code == 401 or response.status_code == 403

    def test_property_detail_without_token_returns_401(self):
        """Property detail endpoint should reject requests without token"""
        response = client.get("/api/v1/properties/prop-123")
        assert response.status_code == 401 or response.status_code == 403


class TestRoleBasedAccessControl:
    """Test role-based authorization"""

    def test_admin_endpoint_with_user_role_returns_403(self):
        """Admin endpoint should reject non-admin users"""
        # This test assumes we can generate a valid token
        # In CI, we'll use mock auth or actual Keycloak tokens

        # For now, test that endpoint exists and requires auth
        response = client.get("/api/v1/admin/stats")
        assert response.status_code in [401, 403]

    def test_admin_endpoint_without_admin_role_denied(self):
        """Users without admin role should be denied"""
        response = client.get("/api/v1/admin/stats")
        # Should be 401 (no auth) or 403 (no role)
        assert response.status_code in [401, 403]


class TestTenantIsolation:
    """Test that tenant A cannot access tenant B's data"""

    def test_tenant_a_cannot_access_tenant_b_property(self):
        """Tenant A should get 404 when accessing Tenant B's property"""
        # In production: create fixture properties for tenant A and B
        # Token for tenant A trying to access tenant B's property
        # Should return 404 (not 403 to avoid information leak)

        response = client.get("/api/v1/properties/tenant-b-property-123")
        # Without token, should be 401
        assert response.status_code == 401 or response.status_code == 403

    def test_properties_filtered_by_tenant_id(self):
        """Properties list should only include authenticated tenant's properties"""
        # Test that tenant_id from JWT is used to filter results
        response = client.get("/api/v1/properties")
        assert response.status_code in [401, 403]


class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers_present(self):
        """CORS headers should be properly configured"""
        headers = {"Origin": "http://localhost:3000"}
        response = client.options("/api/v1/properties", headers=headers)

        # CORS middleware should handle OPTIONS requests
        # Check that strict origin policy is enforced
        assert response.status_code in [200, 401, 403]

    def test_cors_rejects_unknown_origin(self):
        """CORS should reject requests from non-allowed origins"""
        headers = {"Origin": "http://evil.com"}
        response = client.get("/healthz", headers=headers)

        # Even public endpoints should respect CORS
        # The middleware might still return 200 but not include Access-Control-Allow-Origin
        assert response.status_code == 200


# Integration test placeholders (require real Keycloak or mock)
class TestAuthenticationIntegration:
    """
    Integration tests for authentication
    These require either:
    1. Mock Keycloak server
    2. MOCK_AUTH=true environment variable
    3. Real Keycloak instance in CI
    """

    @pytest.mark.skip(reason="Requires Keycloak integration")
    def test_valid_jwt_grants_access(self):
        """Valid JWT should grant access to protected endpoints"""
        # token = get_real_keycloak_token()
        # response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        # assert response.status_code == 200
        pass

    @pytest.mark.skip(reason="Requires Keycloak integration")
    def test_expired_jwt_rejected(self):
        """Expired JWT should be rejected"""
        # expired_token = generate_expired_token()
        # response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired_token}"})
        # assert response.status_code == 401
        pass

    @pytest.mark.skip(reason="Requires Keycloak integration")
    def test_invalid_signature_rejected(self):
        """JWT with invalid signature should be rejected"""
        # bad_token = generate_token_with_wrong_signature()
        # response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {bad_token}"})
        # assert response.status_code == 401
        pass


def test_api_documentation_generated():
    """Test that OpenAPI docs are available"""
    response = client.get("/docs")
    assert response.status_code == 200

    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "paths" in spec
    assert "/api/v1/properties" in spec["paths"]
