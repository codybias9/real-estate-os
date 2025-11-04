"""
Security utilities for password hashing and JWT tokens
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
import hashlib

from api.core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets strength requirements.
    Returns (is_valid, error_message)
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long"

    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if settings.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    if settings.PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"

    return True, ""


def generate_random_password(length: int = 16) -> str:
    """Generate a secure random password"""
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ============================================================================
# JWT TOKEN UTILITIES
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.
    Uses RS256 if JWT_PRIVATE_KEY is set, otherwise falls back to HS256 with SECRET_KEY.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    # Use RS256 if private key is available, otherwise HS256
    if settings.JWT_PRIVATE_KEY:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_PRIVATE_KEY,
            algorithm="RS256"
        )
    else:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm="HS256"
        )

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token.
    Refresh tokens have longer expiry than access tokens.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    # Use RS256 if private key is available, otherwise HS256
    if settings.JWT_PRIVATE_KEY:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_PRIVATE_KEY,
            algorithm="RS256"
        )
    else:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm="HS256"
        )

    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify JWT token.
    Uses RS256 if JWT_PUBLIC_KEY is set, otherwise falls back to HS256 with SECRET_KEY.
    """
    try:
        # Try RS256 first if public key is available
        if settings.JWT_PUBLIC_KEY:
            payload = jwt.decode(
                token,
                settings.JWT_PUBLIC_KEY,
                algorithms=["RS256"]
            )
        else:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
        return payload
    except JWTError:
        return None


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
    """Verify token is of the expected type (access or refresh)"""
    return payload.get("type") == expected_type


# ============================================================================
# LOGIN LOCKOUT AND PROGRESSIVE BACKOFF
# ============================================================================

def calculate_lockout_until(failed_attempts: int) -> Optional[datetime]:
    """
    Calculate when user should be locked out until based on failed login attempts.
    Returns None if user should not be locked out yet.
    """
    if failed_attempts < settings.MAX_LOGIN_ATTEMPTS:
        return None

    return datetime.utcnow() + timedelta(minutes=settings.LOGIN_LOCKOUT_DURATION_MINUTES)


def get_progressive_backoff_delay(failed_attempts: int) -> int:
    """
    Get progressive backoff delay in seconds based on failed attempts.
    Returns delay before next login attempt is allowed.
    """
    if not settings.PROGRESSIVE_BACKOFF_ENABLED:
        return 0

    delays = settings.PROGRESSIVE_BACKOFF_DELAYS
    if failed_attempts >= len(delays):
        return delays[-1]
    return delays[failed_attempts]


def is_user_locked_out(locked_until: Optional[datetime]) -> bool:
    """Check if user is currently locked out"""
    if not locked_until:
        return False
    return datetime.utcnow() < locked_until


# ============================================================================
# TOKEN UTILITIES
# ============================================================================

def generate_email_verification_token() -> str:
    """Generate a secure token for email verification"""
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    """Generate a secure token for password reset"""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()


# ============================================================================
# IDEMPOTENCY KEY
# ============================================================================

def generate_idempotency_key() -> str:
    """Generate a unique idempotency key"""
    return secrets.token_urlsafe(32)


def hash_request_body(body: bytes) -> str:
    """Hash request body for idempotency checking"""
    return hashlib.sha256(body).hexdigest()
