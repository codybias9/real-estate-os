"""JWT token generation and validation

Handles:
- Creating signed JWT tokens with tenant_id + roles
- Validating and decoding JWT tokens
- Token expiration
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from jose import JWTError, jwt
from uuid import UUID

from .config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
from .models import TokenPayload, Role


def create_access_token(
    user_id: UUID,
    tenant_id: UUID,
    roles: list[Role],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token

    Args:
        user_id: User UUID
        tenant_id: Tenant UUID
        roles: List of user roles
        expires_delta: Optional custom expiration time

    Returns:
        Signed JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": [role.value for role in roles],
        "exp": int(expire.timestamp())
    }

    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenPayload:
    """Verify and decode JWT token

    Args:
        token: JWT token string

    Returns:
        TokenPayload with user_id, tenant_id, roles, exp

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        token_data = TokenPayload(**payload)

        # Check expiration
        if datetime.utcnow().timestamp() > token_data.exp:
            raise JWTError("Token has expired")

        return token_data

    except JWTError as e:
        raise JWTError(f"Could not validate token: {str(e)}")


def decode_token_without_verification(token: str) -> Optional[Dict]:
    """Decode token without signature verification (for debugging)

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return None
