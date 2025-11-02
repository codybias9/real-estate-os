"""
JWT/OIDC authentication and authorization with Keycloak integration.
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
import logging
from functools import wraps, lru_cache
from enum import Enum

from api.config import settings
from api.database import AsyncSession, get_db, set_tenant_context

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


class Role(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    ANALYST = "analyst"
    OPERATOR = "operator"
    USER = "user"


class TokenData:
    """Decoded JWT token data."""

    def __init__(
        self,
        sub: str,
        email: Optional[str] = None,
        tenant_id: Optional[str] = None,
        roles: Optional[List[str]] = None,
        exp: Optional[int] = None,
        **kwargs
    ):
        self.sub = sub  # Subject (user ID)
        self.email = email
        self.tenant_id = tenant_id
        self.roles = roles or []
        self.exp = exp
        self.raw_claims = kwargs

    def has_role(self, role: Role) -> bool:
        """Check if user has a specific role."""
        return role.value in self.roles

    def has_any_role(self, roles: List[Role]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role.value in self.roles for role in roles)

    def has_all_roles(self, roles: List[Role]) -> bool:
        """Check if user has all of the specified roles."""
        return all(role.value in self.roles for role in roles)

    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.has_role(Role.ADMIN)


class JWKSCache:
    """Cache for Keycloak JWKS (JSON Web Key Set)."""

    def __init__(self, jwks_url: str = None, cache_ttl_seconds: int = 3600):
        self._jwks: Optional[Dict[str, Any]] = None
        self._last_fetch: Optional[datetime] = None
        self._ttl = timedelta(seconds=cache_ttl_seconds)
        self._jwks_url = jwks_url or settings.keycloak_jwks_url

    async def get_jwks(self) -> Dict[str, Any]:
        """
        Get JWKS from Keycloak, with caching.

        Returns:
            JWKS dictionary
        """
        now = datetime.utcnow()

        # Return cached if still valid
        if self._jwks and self._last_fetch:
            if now - self._last_fetch < self._ttl:
                return self._jwks

        # Fetch fresh JWKS
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._jwks_url,
                    timeout=10.0
                )
                response.raise_for_status()
                self._jwks = response.json()
                self._last_fetch = now
                logger.info("Refreshed JWKS from Keycloak")
                return self._jwks

        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Keycloak: {e}")
            # Return stale cache if available
            if self._jwks:
                logger.warning("Using stale JWKS cache")
                return self._jwks
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )


# Global JWKS cache
jwks_cache = JWKSCache()


async def verify_token(token: str) -> TokenData:
    """
    Verify JWT token from Keycloak.

    Args:
        token: JWT token string

    Returns:
        TokenData with decoded claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Get JWKS for signature verification
        jwks = await jwks_cache.get_jwks()

        # Decode and verify token
        payload = jwt.decode(
            token,
            jwks,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_exp": True,
            }
        )

        # Extract user ID
        sub: str = payload.get("sub")
        if not sub:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception

        # Extract email
        email: Optional[str] = payload.get("email") or payload.get("preferred_username")

        # Extract tenant_id
        tenant_id: Optional[str] = payload.get("tenant_id")
        if not tenant_id:
            logger.warning(f"Token for user {sub} missing 'tenant_id' claim")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenant_id in token. Contact administrator."
            )

        # Extract roles
        # Keycloak stores roles in realm_access.roles or resource_access
        roles: List[str] = []

        # Check realm roles
        realm_access = payload.get("realm_access", {})
        if isinstance(realm_access, dict):
            roles.extend(realm_access.get("roles", []))

        # Check client roles
        resource_access = payload.get("resource_access", {})
        if isinstance(resource_access, dict):
            client_roles = resource_access.get(settings.keycloak_client_id, {})
            if isinstance(client_roles, dict):
                roles.extend(client_roles.get("roles", []))

        # Extract expiration
        exp: Optional[int] = payload.get("exp")

        return TokenData(
            sub=sub,
            email=email,
            tenant_id=tenant_id,
            roles=roles,
            exp=exp,
            **payload
        )

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    FastAPI dependency to get current authenticated user from JWT.

    Usage:
        @app.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            return {"user_id": user.sub, "tenant": user.tenant_id}

    Args:
        credentials: HTTP Authorization header with Bearer token

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    return await verify_token(token)


async def get_current_user_with_db(
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[TokenData, AsyncSession]:
    """
    FastAPI dependency to get user and database session with tenant context set.

    This combines authentication and tenant context setup in one dependency.

    Usage:
        @app.get("/properties")
        async def list_properties(
            user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
        ):
            user, db = user_db
            # db session already has tenant context set
            properties = await db.execute(select(Property))
            return properties.scalars().all()

    Args:
        user: Current user from JWT
        db: Database session

    Returns:
        Tuple of (TokenData, AsyncSession with tenant context)
    """
    # Set tenant context for RLS
    await set_tenant_context(db, user.tenant_id)

    return user, db


def require_roles(required_roles: List[Role]):
    """
    Decorator to require specific roles for an endpoint.

    Usage:
        @app.get("/admin/users")
        @require_roles([Role.ADMIN])
        async def list_all_users(user: TokenData = Depends(get_current_user)):
            ...

        @app.post("/properties")
        @require_roles([Role.ADMIN, Role.ANALYST])
        async def create_property(user: TokenData = Depends(get_current_user)):
            ...

    Args:
        required_roles: List of roles, user must have at least one

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (injected by Depends)
            user: Optional[TokenData] = kwargs.get('user')

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )

            # Check if user has required role
            if not user.has_any_role(required_roles):
                logger.warning(
                    f"User {user.sub} attempted to access {func.__name__} "
                    f"without required roles: {[r.value for r in required_roles]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required role: {[r.value for r in required_roles]}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Keycloak API Integration
# ============================================================================

class KeycloakClient:
    """Client for interacting with Keycloak Admin API."""

    def __init__(self):
        self._admin_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def get_admin_token(self) -> str:
        """
        Get admin access token from Keycloak.

        Returns:
            Admin access token
        """
        # Return cached token if still valid
        if self._admin_token and self._token_expires:
            if datetime.utcnow() < self._token_expires:
                return self._admin_token

        # Get fresh token
        if not settings.keycloak_admin_username or not settings.keycloak_admin_password:
            raise ValueError("Keycloak admin credentials not configured")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.keycloak_token_url,
                    data={
                        "grant_type": "password",
                        "client_id": settings.keycloak_client_id,
                        "username": settings.keycloak_admin_username,
                        "password": settings.keycloak_admin_password,
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                self._admin_token = data["access_token"]
                expires_in = data.get("expires_in", 300)
                self._token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 30)

                return self._admin_token

        except Exception as e:
            logger.error(f"Failed to get Keycloak admin token: {e}")
            raise

    async def exchange_credentials_for_token(
        self,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Exchange username/password for JWT token.

        Args:
            username: User's username or email
            password: User's password

        Returns:
            Token response with access_token, refresh_token, expires_in

        Raises:
            HTTPException: If authentication fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.keycloak_token_url,
                    data={
                        "grant_type": "password",
                        "client_id": settings.keycloak_client_id,
                        "client_secret": settings.keycloak_client_secret,
                        "username": username,
                        "password": password,
                    },
                    timeout=10.0
                )

                if response.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid username or password"
                    )

                response.raise_for_status()
                return response.json()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token response

        Raises:
            HTTPException: If refresh fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.keycloak_token_url,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": settings.keycloak_client_id,
                        "client_secret": settings.keycloak_client_secret,
                        "refresh_token": refresh_token,
                    },
                    timeout=10.0
                )

                if response.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid refresh token"
                    )

                response.raise_for_status()
                return response.json()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

    async def logout(self, refresh_token: str) -> bool:
        """
        Logout user by revoking refresh token.

        Args:
            refresh_token: Token to revoke

        Returns:
            True if successful
        """
        try:
            logout_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/logout"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    logout_url,
                    data={
                        "client_id": settings.keycloak_client_id,
                        "client_secret": settings.keycloak_client_secret,
                        "refresh_token": refresh_token,
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return True

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False


# Global Keycloak client
keycloak_client = KeycloakClient()
