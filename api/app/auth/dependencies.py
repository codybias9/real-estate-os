"""FastAPI dependencies for authentication

Provides:
- get_current_user: Extract and validate JWT token from Authorization header
- get_current_tenant: Extract tenant from token
- require_role: Check user has required role
- get_api_key_user: Authenticate via API key
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from .jwt_handler import verify_token
from .models import User, Role, TokenPayload
from ..database import get_db

import sys
sys.path.append('/home/user/real-estate-os')
from db.models_auth import User as DBUser, APIKey as DBAPIKey


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate user from JWT token

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User object with id, tenant_id, roles

    Raises:
        HTTPException: 401 if token invalid or user not found
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Verify JWT token
        token_data: TokenPayload = verify_token(credentials.credentials)

        # Load user from database
        user_id = UUID(token_data.sub)
        db_user = db.query(DBUser).filter(DBUser.id == user_id).first()

        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )

        # Update last login
        from datetime import datetime
        db_user.last_login = datetime.utcnow()
        db.commit()

        return User(
            id=db_user.id,
            email=db_user.email,
            tenant_id=db_user.tenant_id,
            roles=[Role(r) for r in token_data.roles],
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            last_login=db_user.last_login
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_api_key_user(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """Authenticate via API key (X-API-Key header)

    Args:
        api_key: API key from X-API-Key header
        db: Database session

    Returns:
        User object representing the API key

    Raises:
        HTTPException: 401 if API key invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    # Hash the API key to compare with stored hash
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Find API key by prefix (first 8 chars)
    key_prefix = api_key[:8]
    db_keys = db.query(DBAPIKey).filter(
        DBAPIKey.key_prefix == key_prefix,
        DBAPIKey.is_active == True
    ).all()

    # Verify full key against hash
    matching_key = None
    for db_key in db_keys:
        if pwd_context.verify(api_key, db_key.key_hash):
            matching_key = db_key
            break

    if not matching_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Check expiration
    from datetime import datetime
    if matching_key.expires_at and matching_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )

    # Update last used
    matching_key.last_used = datetime.utcnow()
    db.commit()

    # Return synthetic user for API key
    return User(
        id=matching_key.id,
        email=f"apikey-{matching_key.name}@service",
        tenant_id=matching_key.tenant_id,
        roles=[Role(r) for r in matching_key.roles],
        is_active=True,
        created_at=matching_key.created_at,
        last_login=matching_key.last_used
    )


async def get_current_user_or_api_key(
    user_from_token: Optional[User] = Depends(get_current_user),
    user_from_api_key: Optional[User] = Depends(get_api_key_user)
) -> User:
    """Get user from either JWT token or API key

    Tries JWT first, falls back to API key

    Args:
        user_from_token: User from JWT token (if present)
        user_from_api_key: User from API key (if present)

    Returns:
        User object

    Raises:
        HTTPException: 401 if neither auth method succeeds
    """
    # Try JWT token first
    try:
        if user_from_token:
            return user_from_token
    except HTTPException:
        pass

    # Fall back to API key
    if user_from_api_key:
        return user_from_api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (Bearer token or X-API-Key)"
    )


def get_current_tenant(current_user: User = Depends(get_current_user)) -> UUID:
    """Extract tenant ID from current user

    Args:
        current_user: Current authenticated user

    Returns:
        Tenant UUID
    """
    return current_user.tenant_id


def require_role(required_roles: List[Role]):
    """Dependency factory to require specific roles

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role([Role.OWNER, Role.ADMIN]))])

    Args:
        required_roles: List of roles that are allowed

    Returns:
        Dependency function
    """
    def check_role(current_user: User = Depends(get_current_user)) -> User:
        if not any(role in required_roles for role in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[r.value for r in required_roles]}"
            )
        return current_user

    return check_role
