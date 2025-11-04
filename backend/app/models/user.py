"""User, Organization, Team, Role, and Permission models."""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from .base import TimestampMixin, SoftDeleteMixin


# Association tables for many-to-many relationships
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)

team_members = Table(
    'team_members',
    Base.metadata,
    Column('team_id', Integer, ForeignKey('teams.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
)


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    """Multi-tenant organization model."""
    __tablename__ = 'organizations'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(String(50), default='free')  # free, starter, pro, enterprise
    settings = Column(JSON, default={})

    # Relationships
    users = relationship('User', back_populates='organization', cascade='all, delete-orphan')
    teams = relationship('Team', back_populates='organization', cascade='all, delete-orphan')


class Team(Base, TimestampMixin, SoftDeleteMixin):
    """Team model for grouping users."""
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)

    # Relationships
    organization = relationship('Organization', back_populates='teams')
    members = relationship('User', secondary=team_members, back_populates='teams')


class Role(Base, TimestampMixin):
    """Role-based access control roles."""
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    is_system = Column(Boolean, default=False)  # System roles cannot be deleted

    # Relationships
    users = relationship('User', secondary=user_roles, back_populates='roles')
    permissions = relationship('Permission', secondary=role_permissions, back_populates='roles')


class Permission(Base, TimestampMixin):
    """Granular permissions for RBAC."""
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True, index=True)
    resource = Column(String(100), nullable=False)  # e.g., 'property', 'lead', 'campaign'
    action = Column(String(50), nullable=False)  # e.g., 'read', 'create', 'update', 'delete'
    description = Column(String(500), nullable=True)

    # Relationships
    roles = relationship('Role', secondary=role_permissions, back_populates='permissions')


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User model with authentication and authorization."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Login security
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)

    # Profile
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    timezone = Column(String(50), default='UTC')
    settings = Column(JSON, default={})

    # Relationships
    organization = relationship('Organization', back_populates='users')
    roles = relationship('Role', secondary=user_roles, back_populates='users')
    teams = relationship('Team', secondary=team_members, back_populates='members')
    leads = relationship('Lead', back_populates='assigned_user', foreign_keys='Lead.assigned_user_id')
    campaigns = relationship('Campaign', back_populates='created_by_user', foreign_keys='Campaign.created_by_id')
    audit_logs = relationship('AuditLog', back_populates='user')
