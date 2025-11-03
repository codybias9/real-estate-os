"""
User and tenant repository for database operations
"""

from typing import Optional, List
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from .models import User, UserRole, Tenant
from .password import PasswordHandler


class UserNotFoundError(Exception):
    """Raised when user is not found"""

    pass


class TenantNotFoundError(Exception):
    """Raised when tenant is not found"""

    pass


class EmailAlreadyExistsError(Exception):
    """Raised when email already exists"""

    pass


class UserRepository:
    """Repository for user database operations"""

    def __init__(self, session: Session, password_handler: Optional[PasswordHandler] = None):
        """
        Initialize user repository.

        Args:
            session: SQLAlchemy database session
            password_handler: Password handler instance
        """
        self.session = session
        self.password_handler = password_handler or PasswordHandler()

    def create_user(
        self,
        tenant_id: str,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.VIEWER,
    ) -> User:
        """
        Create a new user.

        Args:
            tenant_id: Tenant ID
            email: User email
            password: Plain-text password (will be hashed)
            full_name: User full name
            role: User role

        Returns:
            Created user

        Raises:
            EmailAlreadyExistsError: If email already exists
        """
        # Check if email exists
        existing = self.get_user_by_email(email)
        if existing:
            raise EmailAlreadyExistsError(f"Email {email} already exists")

        # Hash password
        hashed_password = self.password_handler.hash_password(password)

        user_id = str(uuid4())
        now = datetime.utcnow()

        # In production, this would insert into users table
        # For now, return User object
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email=email,
            full_name=full_name,
            role=role,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # TODO: Insert into database
        # self.session.add(user_model)
        # self.session.commit()

        return user

    def get_user_by_id(self, user_id: str, tenant_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID
            tenant_id: Tenant ID

        Returns:
            User if found, None otherwise
        """
        # TODO: Query database
        # user_model = self.session.query(UserModel).filter(
        #     and_(UserModel.id == user_id, UserModel.tenant_id == tenant_id)
        # ).first()
        # return User(**user_model.__dict__) if user_model else None

        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        # TODO: Query database
        return None

    def verify_credentials(self, email: str, password: str) -> Optional[User]:
        """
        Verify user credentials.

        Args:
            email: User email
            password: Plain-text password

        Returns:
            User if credentials are valid, None otherwise
        """
        user = self.get_user_by_email(email)
        if not user:
            return None

        # TODO: Get hashed password from database
        # if self.password_handler.verify_password(password, user.hashed_password):
        #     return user

        return None

    def update_user(
        self,
        user_id: str,
        tenant_id: str,
        full_name: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> User:
        """
        Update user.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            full_name: New full name (optional)
            role: New role (optional)
            is_active: New active status (optional)

        Returns:
            Updated user

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.get_user_by_id(user_id, tenant_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        # TODO: Update database

        return user

    def delete_user(self, user_id: str, tenant_id: str) -> None:
        """
        Delete user (soft delete by setting is_active = False).

        Args:
            user_id: User ID
            tenant_id: Tenant ID

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.get_user_by_id(user_id, tenant_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        # TODO: Soft delete in database
        # self.session.query(UserModel).filter(
        #     and_(UserModel.id == user_id, UserModel.tenant_id == tenant_id)
        # ).update({"is_active": False, "updated_at": datetime.utcnow()})
        # self.session.commit()

    def list_users(self, tenant_id: str, limit: int = 100, offset: int = 0) -> List[User]:
        """
        List users for a tenant.

        Args:
            tenant_id: Tenant ID
            limit: Maximum number of users to return
            offset: Offset for pagination

        Returns:
            List of users
        """
        # TODO: Query database
        return []


class TenantRepository:
    """Repository for tenant database operations"""

    def __init__(self, session: Session):
        """
        Initialize tenant repository.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def create_tenant(self, name: str, slug: str) -> Tenant:
        """
        Create a new tenant.

        Args:
            name: Tenant name
            slug: Tenant slug (unique identifier)

        Returns:
            Created tenant
        """
        tenant_id = str(uuid4())
        now = datetime.utcnow()

        tenant = Tenant(
            id=tenant_id,
            name=name,
            slug=slug,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # TODO: Insert into database

        return tenant

    def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """
        Get tenant by ID.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tenant if found, None otherwise
        """
        # TODO: Query database
        return None

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """
        Get tenant by slug.

        Args:
            slug: Tenant slug

        Returns:
            Tenant if found, None otherwise
        """
        # TODO: Query database
        return None
