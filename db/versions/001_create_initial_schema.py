"""create initial schema

Revision ID: 001_create_schema
Revises: b81dde19348f
Create Date: 2025-11-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '001_create_schema'
down_revision: Union[str, Sequence[str], None] = 'b81dde19348f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subscription_tier', sa.String(50), server_default='trial'),
        sa.Column('settings', JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subscription_tier', sa.String(50), server_default='trial'),
        sa.Column('monthly_budget_cap', sa.DECIMAL(10, 2), server_default='500.00'),
        sa.Column('settings', JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='teams_tenant_id_fkey'),
    )

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('team_id', UUID(as_uuid=True), nullable=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), server_default='agent'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('settings', JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='users_tenant_id_fkey'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], name='users_team_id_fkey'),
    )

    # Create index on email
    op.create_index('ix_users_email', 'users', ['email'])

    # Create properties table
    op.create_table(
        'properties',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('city', sa.String(100)),
        sa.Column('state', sa.String(50)),
        sa.Column('zip_code', sa.String(20)),
        sa.Column('price', sa.DECIMAL(12, 2)),
        sa.Column('bedrooms', sa.Integer),
        sa.Column('bathrooms', sa.DECIMAL(3, 1)),
        sa.Column('square_feet', sa.Integer),
        sa.Column('property_type', sa.String(50)),
        sa.Column('listing_url', sa.Text),
        sa.Column('description', sa.Text),
        sa.Column('metadata', JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='properties_tenant_id_fkey'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('properties')
    op.drop_index('ix_users_email', 'users')
    op.drop_table('users')
    op.drop_table('teams')
    op.drop_table('tenants')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
