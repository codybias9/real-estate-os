"""
Authentication Utilities
JWT token generation, validation, password hashing
"""
from datetime import datetime, timedelta
from typing import Optional
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from api.database import get_db
from db.models import User

# ============================================================================
# CONFIGURATION
# ============================================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ============================================================================
# PASSWORD HASHING
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


# ============================================================================
# JWT TOKEN GENERATION
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Payload data to encode in token (should include 'sub' with user_id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ============================================================================
# TOKEN VALIDATION & USER RETRIEVAL
# ============================================================================

def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user

    Usage in routes:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id}

    Args:
        credentials: HTTP Bearer token from request header
        db: Database session

    Returns:
        Current authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = decode_token(token)

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


# ============================================================================
# AUTHENTICATION HELPERS
# ============================================================================

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password

    Args:
        db: Database session
        email: User's email
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    if not user.password_hash:
        # User doesn't have a password set (shouldn't happen in production)
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


# ============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC) DEPENDENCIES
# ============================================================================

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require admin role

    Usage:
        @router.post("/admin-only")
        def admin_route(current_user: User = Depends(require_admin)):
            return {"message": "Admin access granted"}
    """
    from db.models import UserRole

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


def require_manager_or_above(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require manager or admin role
    """
    from db.models import UserRole

    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or Admin access required"
        )

    return current_user


def require_agent_or_above(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require agent, manager, or admin role (excludes viewers)
    """
    from db.models import UserRole

    if current_user.role == UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required (Viewer role cannot perform this action)"
        )

    return current_user


# ============================================================================
# TEAM-BASED ACCESS CONTROL
# ============================================================================

def verify_team_access(user: User, team_id: int) -> bool:
    """
    Verify that a user has access to a specific team

    Args:
        user: User object
        team_id: Team ID to check access for

    Returns:
        True if user has access, False otherwise
    """
    return user.team_id == team_id


def require_team_access(
    team_id: int,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to verify user has access to specified team

    Usage:
        @router.get("/teams/{team_id}/properties")
        def get_team_properties(
            team_id: int,
            current_user: User = Depends(lambda: require_team_access(team_id))
        ):
            return {"team_id": team_id}
    """
    if not verify_team_access(current_user, team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this team's resources"
        )

    return current_user
