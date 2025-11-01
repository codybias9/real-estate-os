"""Authentication system - JWT, API keys, RBAC

Revision ID: 004_authentication_system
Revises: 003_provenance_foundation
Create Date: 2025-11-01 19:45:00

PR#1: sec/auth-oidc-jwt

Creates:
- auth_users: User accounts with bcrypt password hashing
- auth_api_keys: API keys for service-to-service authentication

Adds support for:
- JWT bearer token authentication
- API key authentication (X-API-Key header)
- Role-based access control (owner, admin, analyst, service)
- Multi-tenant isolation via tenant_id FK
- OIDC integration fields (for Keycloak/Auth0)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TIMESTAMP
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '004_authentication_system'
down_revision = '003_provenance_foundation'
branch_labels = None
depends_on = None


def upgrade():
    """Apply authentication schema changes"""

    # Create auth_users table
    op.create_table(
        'auth_users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False, comment='bcrypt hash of password'),
        sa.Column('roles', ARRAY(sa.String), nullable=False, server_default='{}', comment='owner, admin, analyst, service'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
        sa.Column('last_login', TIMESTAMP(timezone=True), nullable=True),

        # OIDC integration fields (optional)
        sa.Column('oidc_provider', sa.String(50), nullable=True, comment='keycloak, auth0, etc.'),
        sa.Column('oidc_sub', sa.String(255), nullable=True, comment='Subject from OIDC provider'),

        comment='User accounts for JWT authentication'
    )

    # Create indexes on auth_users
    op.create_index('idx_auth_users_email', 'auth_users', ['email'])
    op.create_index('idx_auth_users_tenant_id', 'auth_users', ['tenant_id'])
    op.create_index('idx_auth_users_oidc_sub', 'auth_users', ['oidc_sub'])
    op.create_index('idx_auth_users_is_active', 'auth_users', ['is_active'], postgresql_where=sa.text("is_active = true"))

    # Create auth_api_keys table
    op.create_table(
        'auth_api_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('key_hash', sa.String(255), nullable=False, comment='bcrypt hash of full API key'),
        sa.Column('key_prefix', sa.String(8), nullable=False, comment='First 8 chars for identification'),
        sa.Column('roles', ARRAY(sa.String), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
        sa.Column('expires_at', TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_used', TIMESTAMP(timezone=True), nullable=True),

        comment='API keys for service-to-service authentication'
    )

    # Create indexes on auth_api_keys
    op.create_index('idx_auth_api_keys_key_prefix', 'auth_api_keys', ['key_prefix'])
    op.create_index('idx_auth_api_keys_tenant_id', 'auth_api_keys', ['tenant_id'])
    op.create_index('idx_auth_api_keys_is_active', 'auth_api_keys', ['is_active'], postgresql_where=sa.text("is_active = true"))

    # Add updated_at trigger for auth_users
    op.execute("""
        CREATE OR REPLACE FUNCTION update_auth_users_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trigger_auth_users_updated_at
        BEFORE UPDATE ON auth_users
        FOR EACH ROW
        EXECUTE FUNCTION update_auth_users_updated_at();
    """)

    print("✅ Authentication system tables created successfully")
    print("   - auth_users: User accounts with JWT authentication")
    print("   - auth_api_keys: API keys for service authentication")
    print("   - Indexes created for performance")
    print("   - Updated triggers created")


def downgrade():
    """Revert authentication schema changes"""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_auth_users_updated_at ON auth_users")
    op.execute("DROP FUNCTION IF EXISTS update_auth_users_updated_at()")

    # Drop tables (cascades to indexes)
    op.drop_table('auth_api_keys')
    op.drop_table('auth_users')

    print("✅ Authentication system tables removed")
