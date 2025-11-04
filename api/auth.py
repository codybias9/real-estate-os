"""
JWT Authentication and Authorization Middleware for FastAPI

Integrates with Keycloak OIDC for JWT validation and role-based access control.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import List, Optional
import os
import requests
from functools import lru_cache
from datetime import datetime, timedelta

security = HTTPBearer()

# Keycloak configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "real-estate-os")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "real-estate-os-api")

# Cache public key for 1 hour
@lru_cache(maxsize=1)
def get_public_key(timestamp: int = None):
    """
    Fetch public key from Keycloak
    timestamp parameter is used for cache invalidation (hourly)
    """
    certs_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    try:
        response = requests.get(certs_url, timeout=5)
        response.raise_for_status()
        keys = response.json()["keys"]
        # Return first RSA key
        for key in keys:
            if key.get("kty") == "RSA":
                return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch Keycloak public key: {str(e)}"
        )


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify JWT token and return decoded payload
    """
    token = credentials.credentials

    try:
        # Get current hour for cache key
        hour_timestamp = int(datetime.utcnow().timestamp() // 3600)
        public_key = get_public_key(hour_timestamp)

        # Decode and verify token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=KEYCLOAK_CLIENT_ID,
            options={"verify_aud": True, "verify_exp": True}
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.JWTClaimsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(payload: dict = Depends(verify_token)) -> dict:
    """
    Extract user information from JWT payload
    """
    return {
        "user_id": payload.get("sub"),
        "username": payload.get("preferred_username"),
        "email": payload.get("email"),
        "tenant_id": payload.get("tenant_id"),  # Custom claim
        "roles": payload.get("realm_access", {}).get("roles", []),
        "client_roles": payload.get("resource_access", {}).get(KEYCLOAK_CLIENT_ID, {}).get("roles", [])
    }


def require_role(required_roles: List[str]):
    """
    Dependency to enforce role-based access control

    Usage:
        @app.get("/api/admin/users", dependencies=[Depends(require_role(["admin"]))])
    """
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_roles = set(current_user["roles"] + current_user["client_roles"])
        required = set(required_roles)

        if not required.intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(required_roles)}"
            )

        return current_user

    return role_checker


def require_scope(required_scopes: List[str]):
    """
    Dependency to enforce scope-based access control

    Scopes map to operations:
    - read:properties
    - write:properties
    - read:analytics
    - admin:all
    """
    def scope_checker(payload: dict = Depends(verify_token)):
        token_scopes = payload.get("scope", "").split()

        if not any(scope in token_scopes for scope in required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of scopes: {', '.join(required_scopes)}"
            )

        return payload

    return scope_checker


def get_tenant_id(current_user: dict = Depends(get_current_user)) -> str:
    """
    Extract tenant ID from current user
    Raises 400 if tenant_id not present in token
    """
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing tenant_id claim"
        )
    return tenant_id


# Optional: For development/testing only
class MockAuthBypass:
    """
    Mock authentication for development
    Set MOCK_AUTH=true in environment to enable
    """
    def __init__(self, tenant_id: str = "test-tenant", roles: List[str] = None):
        self.tenant_id = tenant_id
        self.roles = roles or ["user", "admin"]

    def __call__(self):
        if os.getenv("MOCK_AUTH", "false").lower() != "true":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mock auth not enabled"
            )

        return {
            "user_id": "mock-user-123",
            "username": "mockuser",
            "email": "mock@example.com",
            "tenant_id": self.tenant_id,
            "roles": self.roles,
            "client_roles": []
        }
