"""Add idempotency keys table

Revision ID: 003_add_idempotency
Revises: 002_add_rls_policies
Create Date: 2025-01-15

Idempotency keys prevent duplicate processing of critical operations:
- Memo generation
- Outreach enqueue
- Stage transitions
- Timeline events
- Payment processing

Keys are stored with:
- Unique constraint on (key, endpoint)
- Response caching for consistent replay
- TTL for automatic cleanup (24 hours default)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003_add_idempotency'
down_revision = '002_add_rls_policies'
branch_labels = None
depends_on = None


def upgrade():
    """Create idempotency keys table"""
    op.create_table(
        'idempotency_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('idempotency_key', sa.String(255), nullable=False, index=True),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('request_method', sa.String(10), nullable=False),
        sa.Column('request_params', postgresql.JSONB(), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', postgresql.JSONB(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),

        # Unique constraint: same key + endpoint = idempotent
        sa.UniqueConstraint('idempotency_key', 'endpoint', name='uq_idempotency_key_endpoint'),

        # Indexes
        sa.Index('idx_idempotency_user_id', 'user_id'),
        sa.Index('idx_idempotency_team_id', 'team_id'),
        sa.Index('idx_idempotency_expires_at', 'expires_at'),
    )

    # Add foreign keys
    op.create_foreign_key(
        'fk_idempotency_user',
        'idempotency_keys', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )

    op.create_foreign_key(
        'fk_idempotency_team',
        'idempotency_keys', 'teams',
        ['team_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    """Drop idempotency keys table"""
    op.drop_table('idempotency_keys')
