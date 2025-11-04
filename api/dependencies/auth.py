"""
Authentication dependencies for FastAPI endpoints
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime

from api.core.database import get_db
from api.core.security import decode_token, verify_token_type, is_user_locked_out
from api.core.exceptions import AuthenticationError, AccountLockedError, PermissionDeniedError
from db.models import User, Organization, Role, Permission, UserStatus


# Security scheme for Bearer token
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    Validates token and retrieves user from database.
    """
    token = credentials.credentials

    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise AuthenticationError("Invalid token")

    # Verify token type
    if not verify_token_type(payload, "access"):
        raise AuthenticationError("Invalid token type")

    # Get user ID from payload
    user_id: str = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token payload")

    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AuthenticationError("User not found")

    # Check if user is active
    if user.status != UserStatus.ACTIVE:
        raise AuthenticationError("User account is not active")

    # Check if user is soft deleted
    if user.deleted_at is not None:
        raise AuthenticationError("User account has been deleted")

    # Check if account is locked
    if is_user_locked_out(user.locked_until):
        locked_until_str = user.locked_until.isoformat() if user.locked_until else "unknown"
        raise AccountLockedError(locked_until_str)

    # Update last login info
    user.last_login_at = datetime.utcnow()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    Additional check to ensure user is active.
    """
    if current_user.status != UserStatus.ACTIVE:
        raise AuthenticationError("Inactive user")
    return current_user


async def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Organization:
    """Get the organization of the current user"""
    org = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active"
        )

    return org


class PermissionChecker:
    """
    Dependency class to check if user has required permissions.

    Usage:
        @router.get("/properties", dependencies=[Depends(PermissionChecker(["property:read"]))])
    """

    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        # Get user's roles and permissions
        user_permissions = set()

        for role in current_user.roles:
            for permission in role.permissions:
                permission_str = f"{permission.resource}:{permission.action}"
                user_permissions.add(permission_str)

        # Check if user has all required permissions
        missing_permissions = set(self.required_permissions) - user_permissions

        if missing_permissions:
            raise PermissionDeniedError(
                f"Missing required permissions: {', '.join(missing_permissions)}"
            )

        return current_user


class RoleChecker:
    """
    Dependency class to check if user has required roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(RoleChecker(["admin"]))])
    """

    def __init__(self, required_roles: list[str]):
        self.required_roles = required_roles

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        user_roles = {role.name for role in current_user.roles}

        missing_roles = set(self.required_roles) - user_roles

        if missing_roles:
            raise PermissionDeniedError(
                f"Missing required roles: {', '.join(missing_roles)}"
            )

        return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if token is provided, otherwise return None.
    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if not credentials:
        return None

    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
