"""Hybrid Authentication Dependencies
Supports both JWT (legacy) and OIDC (new) authentication

The system can accept:
1. OIDC tokens from Keycloak (preferred)
2. Legacy JWT tokens (for backward compatibility)
3. API keys (for service-to-service)

This allows gradual migration from JWT to OIDC without breaking existing clients.
"""

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import logging

from .oidc import get_oidc_provider, OIDCProvider
from .jwt_handler import verify_token as verify_jwt_token
from .models import User, Role, TokenPayload
from ..database import get_db
import sys
sys.path.append('/home/user/real-estate-os')
from db.models_auth import User as DBUser

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_hybrid(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from either OIDC token or legacy JWT

    Authentication flow:
    1. Try to verify as OIDC token (from Keycloak)
    2. If that fails, try legacy JWT
    3. If both fail, raise 401

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User object with user_id, tenant_id, roles

    Raises:
        HTTPException: 401 if authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials

    # Try OIDC first (preferred)
    try:
        oidc = get_oidc_provider()
        token_payload = oidc.verify_token(token)
        user_claims = oidc.extract_user_claims(token_payload)

        logger.info(f"OIDC authentication successful for user: {user_claims['email']}")

        # Convert to User model
        return User(
            user_id=UUID(user_claims["user_id"]),
            email=user_claims["email"],
            tenant_id=UUID(user_claims["tenant_id"]) if user_claims["tenant_id"] else None,
            roles=[Role(r) for r in user_claims["roles"]],
            email_verified=user_claims["email_verified"],
            name=user_claims.get("name")
        )

    except HTTPException as oidc_error:
        # OIDC failed, try legacy JWT
        logger.debug(f"OIDC validation failed: {oidc_error.detail}. Trying legacy JWT...")

        try:
            # Verify as legacy JWT
            token_data: TokenPayload = verify_jwt_token(token)
            user_id = UUID(token_data.sub)

            # Fetch user from database
            db_user = db.query(DBUser).filter(DBUser.id == user_id).first()

            if not db_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            if not db_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is inactive"
                )

            logger.info(f"Legacy JWT authentication successful for user: {db_user.email}")

            # Convert to User model
            return User(
                user_id=db_user.id,
                email=db_user.email,
                tenant_id=db_user.tenant_id,
                roles=[Role(r) for r in db_user.roles],
                name=db_user.email.split('@')[0]  # Fallback name
            )

        except Exception as jwt_error:
            # Both OIDC and JWT failed
            logger.warning(f"Authentication failed for token. OIDC error: {oidc_error.detail}, JWT error: {str(jwt_error)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )


def require_role_hybrid(required_role: Role):
    """Dependency to require specific role (works with both OIDC and JWT)

    Usage:
        @router.get("/admin/users")
        async def get_users(
            user: User = Depends(require_role_hybrid(Role.ADMIN))
        ):
            ...
    """
    async def role_checker(
        user: User = Depends(get_current_user_hybrid)
    ) -> User:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}"
            )
        return user

    return role_checker


# ============================================================================
# Convenience exports (backward compatible)
# ============================================================================

# Export hybrid version as default
get_current_user = get_current_user_hybrid
require_role = require_role_hybrid
