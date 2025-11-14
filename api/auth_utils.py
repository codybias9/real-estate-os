"""Authentication utilities for password hashing and verification."""
import bcrypt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.models import User
from api.database import get_db

# Security scheme for Bearer token authentication
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the Authorization header.

    For MOCK_MODE/demo purposes:
    - Accepts any Bearer token that looks valid
    - Returns the demo user from the database
    - In production, would validate JWT and extract user ID

    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        db: Database session

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )

    token = credentials.credentials

    # For MOCK_MODE: Accept any token and return demo user
    # In production, would:
    # 1. Decode JWT token
    # 2. Verify signature
    # 3. Extract user_id from token
    # 4. Look up user by ID

    # For demo, look up the demo user
    user = db.query(User).filter(User.email == "demo@example.com").first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Security(security, auto_error=False),
    db: Session = Depends(get_db)
) -> User | None:
    """
    Get the current user if authenticated, otherwise None.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if not credentials:
        return None

    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


def require_demo_write_permission(
    credentials: HTTPAuthorizationCredentials = Security(security, auto_error=False)
) -> None:
    """
    Demo write guard: Block write operations unless explicitly enabled.

    In MOCK_MODE/demo, this prevents accidental data modifications by requiring
    either:
    1. Valid authentication (Bearer token), OR
    2. DEMO_ALLOW_WRITES=true environment variable

    This is a safety mechanism for demos to operate in read-only mode by default.

    Raises:
        HTTPException: 403 if write operations are not allowed
    """
    # Check if demo writes are explicitly allowed via env var
    demo_allow_writes = os.getenv("DEMO_ALLOW_WRITES", "false").lower() == "true"

    # If demo writes are globally allowed, permit
    if demo_allow_writes:
        return

    # Otherwise, require authentication
    if not credentials:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Write operation blocked in demo mode",
                "demo_mode_write_block": True,
                "hint": "Authenticate with Bearer token or set DEMO_ALLOW_WRITES=true"
            }
        )

    # If credentials present, allow (token validation happens in get_current_user)
    return
