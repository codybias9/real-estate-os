"""User, Role, and Permission models."""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel, SoftDeleteMixin


class User(BaseModel, SoftDeleteMixin):
    """User model."""

    __tablename__ = "users"

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    timezone = Column(String(50), nullable=True, default="UTC")

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Security
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)

    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verification_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_sent_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_at = Column(DateTime(timezone=True), nullable=True)

    # Preferences
    preferences = Column(JSON, nullable=True, default=dict)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    teams = relationship("Team", secondary="team_members", back_populates="members")
    assigned_leads = relationship("Lead", back_populates="assigned_to", foreign_keys="Lead.assigned_to_id")
    created_leads = relationship("Lead", back_populates="created_by", foreign_keys="Lead.created_by_id")


class Role(BaseModel):
    """Role model for RBAC."""

    __tablename__ = "roles"

    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles cannot be deleted

    # Relationships
    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")


class Permission(BaseModel):
    """Permission model for fine-grained access control."""

    __tablename__ = "permissions"

    name = Column(String(100), nullable=False, unique=True, index=True)
    resource = Column(String(100), nullable=False, index=True)  # properties, leads, campaigns, etc.
    action = Column(String(50), nullable=False, index=True)     # create, read, update, delete, list
    description = Column(Text, nullable=True)

    # Relationships
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")


class UserRole(BaseModel):
    """User-Role association."""

    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)


class RolePermission(BaseModel):
    """Role-Permission association."""

    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
