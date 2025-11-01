"""OpenID Connect (OIDC) Provider Integration
Supports Keycloak and other OIDC-compliant providers

Features:
- Token validation (JWT from OIDC provider)
- User info retrieval
- Token refresh
- Backward compatibility with existing JWT auth
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, status
from functools import lru_cache
import os
import logging

logger = logging.getLogger(__name__)


class OIDCProvider:
    """OIDC provider client for Keycloak"""

    def __init__(self):
        self.issuer = os.getenv("OIDC_ISSUER", "http://localhost:8180/realms/real-estate-os")
        self.client_id = os.getenv("OIDC_CLIENT_ID", "real-estate-os-api")
        self.client_secret = os.getenv("OIDC_CLIENT_SECRET")

        # Discover OIDC endpoints
        self.well_known_url = f"{self.issuer}/.well-known/openid-configuration"
        self._discovery_cache = None
        self._jwks_cache = None
        self._jwks_cache_time = None

    @lru_cache(maxsize=1)
    def _discover_endpoints(self) -> Dict[str, Any]:
        """Discover OIDC endpoints from well-known URL

        Cached for performance (invalidate on restart)
        """
        try:
            with httpx.Client() as client:
                response = client.get(self.well_known_url, timeout=10)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to discover OIDC endpoints: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC provider unavailable"
            )

    def _get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set from provider

        Cached for 1 hour
        """
        now = datetime.utcnow()

        # Check cache
        if self._jwks_cache and self._jwks_cache_time:
            if (now - self._jwks_cache_time) < timedelta(hours=1):
                return self._jwks_cache

        # Fetch fresh JWKS
        discovery = self._discover_endpoints()
        jwks_uri = discovery["jwks_uri"]

        try:
            with httpx.Client() as client:
                response = client.get(jwks_uri, timeout=10)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._jwks_cache_time = now
                return self._jwks_cache
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to fetch JWKS"
            )

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode OIDC access token

        Args:
            token: JWT access token from OIDC provider

        Returns:
            Decoded token payload with claims

        Raises:
            HTTPException: If token is invalid
        """
        jwks = self._get_jwks()

        try:
            # Decode header to get key ID (kid)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            # Find matching key in JWKS
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break

            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: key not found"
                )

            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.client_id,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True
                }
            )

            return payload

        except JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from OIDC provider

        Args:
            access_token: Valid access token

        Returns:
            User info dict with standard OIDC claims
        """
        discovery = self._discover_endpoints()
        userinfo_endpoint = discovery["userinfo_endpoint"]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch user info: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to fetch user info"
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            Token response with new access_token and refresh_token
        """
        discovery = self._discover_endpoints()
        token_endpoint = discovery["token_endpoint"]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_endpoint,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    },
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed"
            )

    def extract_user_claims(self, token_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant user claims from token payload

        Args:
            token_payload: Decoded JWT payload

        Returns:
            Dict with user_id, tenant_id, roles, email, etc.
        """
        return {
            "user_id": token_payload.get("sub"),
            "email": token_payload.get("email"),
            "email_verified": token_payload.get("email_verified", False),
            "name": token_payload.get("name"),
            "preferred_username": token_payload.get("preferred_username"),
            "tenant_id": token_payload.get("tenant_id"),  # Custom claim
            "roles": token_payload.get("roles", []),  # Custom claim
            "exp": token_payload.get("exp"),
            "iat": token_payload.get("iat"),
            "iss": token_payload.get("iss")
        }


# ============================================================================
# Singleton instance
# ============================================================================

_oidc_provider: Optional[OIDCProvider] = None


def get_oidc_provider() -> OIDCProvider:
    """Get singleton OIDC provider instance"""
    global _oidc_provider
    if _oidc_provider is None:
        _oidc_provider = OIDCProvider()
    return _oidc_provider
