"""add password_hash to users

Revision ID: 007
Revises: 006_add_compliance_tables
Create Date: 2025-11-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006_add_compliance_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add password_hash column to users table"""
    # Add password_hash column (nullable=True initially for existing rows)
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))

    # For any existing users, set a default hash (they'll need to reset password)
    # In production, you might want to handle this differently
    op.execute("UPDATE users SET password_hash = 'RESET_REQUIRED' WHERE password_hash IS NULL")

    # Now make it non-nullable
    op.alter_column('users', 'password_hash', nullable=False)


def downgrade():
    """Remove password_hash column from users table"""
    op.drop_column('users', 'password_hash')
