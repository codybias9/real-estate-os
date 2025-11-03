"""
FastAPI middleware for JWT authentication and tenant context
"""

from typing import Optional, Callable
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text

from .jwt_handler import JWTHandler, TokenData
from .models import User, UserRole


# HTTP Bearer token scheme
security = HTTPBearer()


class AuthMiddleware:
    """
    Authentication middleware for FastAPI.

    Extracts JWT token from Authorization header, validates it,
    and sets user context in request state.
    """

    def __init__(self, jwt_handler: Optional[JWTHandler] = None):
        """
        Initialize auth middleware.

        Args:
            jwt_handler: JWT handler instance (creates default if not provided)
        """
        self.jwt_handler = jwt_handler or JWTHandler()

    def get_token_data(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
        """
        Extract and verify JWT token from Authorization header.

        Args:
            credentials: HTTP bearer credentials from request

        Returns:
            TokenData with user information

        Raises:
            HTTPException: If token is missing or invalid
        """
        try:
            token = credentials.credentials
            token_data = self.jwt_handler.verify_token(token)
            return token_data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Global middleware instance
_auth_middleware = AuthMiddleware()


def get_current_user(token_data: TokenData = Depends(_auth_middleware.get_token_data)) -> User:
    """
    FastAPI dependency to get current authenticated user.

    Usage:
        @app.get("/properties")
        def get_properties(user: User = Depends(get_current_user)):
            # user is authenticated and available
            pass

    Args:
        token_data: Token data from JWT

    Returns:
        User object with user information

    Raises:
        HTTPException: If user is not authenticated
    """
    return User(
        id=token_data.user_id,
        tenant_id=token_data.tenant_id,
        email=token_data.email,
        full_name="",  # Would be loaded from database in production
        role=UserRole(token_data.role),
    )


def get_current_tenant(token_data: TokenData = Depends(_auth_middleware.get_token_data)) -> str:
    """
    FastAPI dependency to get current tenant ID.

    Usage:
        @app.get("/properties")
        def get_properties(tenant_id: str = Depends(get_current_tenant)):
            # tenant_id is available
            pass

    Args:
        token_data: Token data from JWT

    Returns:
        Tenant ID string

    Raises:
        HTTPException: If user is not authenticated
    """
    return token_data.tenant_id


def require_role(*allowed_roles: UserRole):
    """
    Decorator factory for role-based access control.

    Usage:
        @app.delete("/properties/{id}")
        @require_role(UserRole.ADMIN, UserRole.ANALYST)
        def delete_property(id: str, user: User = Depends(get_current_user)):
            # Only admins and analysts can access this endpoint
            pass

    Args:
        *allowed_roles: Roles that are allowed to access the endpoint

    Returns:
        Dependency function that checks user role
    """

    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}",
            )
        return user

    return role_checker


def require_permission(permission: str):
    """
    Decorator factory for permission-based access control.

    Usage:
        @app.post("/properties")
        @require_permission("properties:create")
        def create_property(data: dict, user: User = Depends(get_current_user)):
            # Only users with properties:create permission can access
            pass

    Args:
        permission: Permission string (e.g., "properties:create")

    Returns:
        Dependency function that checks user permission
    """

    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {permission}",
            )
        return user

    return permission_checker


class TenantContextMiddleware:
    """
    Middleware to set PostgreSQL tenant context for RLS.

    Sets the app.current_tenant_id session variable based on JWT token.
    """

    def __init__(self, jwt_handler: Optional[JWTHandler] = None):
        """
        Initialize tenant context middleware.

        Args:
            jwt_handler: JWT handler instance
        """
        self.jwt_handler = jwt_handler or JWTHandler()

    def set_tenant_context(
        self,
        session: Session,
        tenant_id: str = Depends(get_current_tenant),
    ) -> Session:
        """
        Set tenant context in PostgreSQL session for RLS.

        Usage:
            @app.get("/properties")
            def get_properties(
                db: Session = Depends(get_db),
                session: Session = Depends(tenant_middleware.set_tenant_context)
            ):
                # PostgreSQL RLS is now active for this tenant
                properties = session.query(Property).all()

        Args:
            session: SQLAlchemy database session
            tenant_id: Current tenant ID from JWT

        Returns:
            Session with tenant context set
        """
        # Check if PostgreSQL
        if "postgresql" in str(session.bind.url).lower():
            session.execute(text(f"SET app.current_tenant_id = '{tenant_id}';"))

        return session


# Global tenant context middleware instance
tenant_context_middleware = TenantContextMiddleware()
