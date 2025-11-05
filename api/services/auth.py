"""Authentication service."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ..models import User, Organization
from ..config import settings
import secrets

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """Validate password meets security requirements."""
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"

    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if settings.PASSWORD_REQUIRE_DIGITS and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    if settings.PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"

    return True, None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})

    if settings.JWT_ALGORITHM == "RS256" and settings.JWT_PRIVATE_KEY:
        return jwt.encode(to_encode, settings.JWT_PRIVATE_KEY, algorithm="RS256")
    else:
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    if settings.JWT_ALGORITHM == "RS256" and settings.JWT_PRIVATE_KEY:
        return jwt.encode(to_encode, settings.JWT_PRIVATE_KEY, algorithm="RS256")
    else:
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token."""
    try:
        if settings.JWT_ALGORITHM == "RS256" and settings.JWT_PUBLIC_KEY:
            payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
        else:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def record_failed_login(db: Session, user: User):
    """Record a failed login attempt and lock account if necessary."""
    user.failed_login_attempts += 1

    if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)

    db.commit()


def is_account_locked(user: User) -> bool:
    """Check if account is locked."""
    if user.locked_until is None:
        return False
    if user.locked_until > datetime.utcnow():
        return True
    # Lock expired, reset counter
    return False


def reset_failed_attempts(db: Session, user: User):
    """Reset failed login attempts on successful login."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    db.commit()


def generate_verification_token() -> str:
    """Generate a secure verification token."""
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    """Generate a secure password reset token."""
    return secrets.token_urlsafe(32)


def create_organization_with_user(
    db: Session,
    org_name: str,
    org_email: str,
    user_email: str,
    user_password: str,
    user_first_name: str,
    user_last_name: str,
) -> tuple[Organization, User]:
    """Create a new organization with its first admin user."""
    # Create organization
    org_slug = org_name.lower().replace(" ", "-").replace("_", "-")
    organization = Organization(
        name=org_name,
        slug=org_slug,
        email=org_email,
        is_active=True,
    )
    db.add(organization)
    db.flush()

    # Create admin user
    user = User(
        organization_id=organization.id,
        email=user_email,
        password_hash=get_password_hash(user_password),
        first_name=user_first_name,
        last_name=user_last_name,
        is_active=True,
        is_verified=False,  # Require email verification
        is_superuser=True,  # First user is org admin
    )
    db.add(user)
    db.commit()
    db.refresh(organization)
    db.refresh(user)

    return organization, user
