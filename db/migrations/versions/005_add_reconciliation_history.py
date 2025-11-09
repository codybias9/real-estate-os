"""Add portfolio reconciliation history table

Revision ID: 005_add_reconciliation_history
Revises: 004_add_dlq_tracking
Create Date: 2025-01-15

Tracks portfolio reconciliation runs for data integrity verification:
- Nightly reconciliation against CSV truth data
- ±0.5% drift tolerance
- Alert when metrics exceed threshold
- Full audit trail with results JSON

Reconciliation Process:
1. Load truth metrics from CSV
2. Calculate current database metrics
3. Compare and calculate drift percentage
4. Alert if any metric > 0.5% drift
5. Store results in reconciliation_history
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '005_add_reconciliation_history'
down_revision = '004_add_dlq_tracking'
branch_labels = None
depends_on = None


def upgrade():
    """Create reconciliation_history table"""
    op.create_table(
        'reconciliation_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id', ondelete='CASCADE')),
        sa.Column('reconciliation_date', sa.DateTime(), nullable=False),

        # Summary metrics
        sa.Column('total_metrics', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passing_metrics', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failing_metrics', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_drift_percentage', sa.Float(), nullable=False, server_default='0.0'),

        # Alert status
        sa.Column('alert_triggered', sa.Boolean(), nullable=False, server_default='false'),

        # Full results JSON
        sa.Column('results_json', postgresql.JSONB()),

        # Timestamp
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        # Indexes
        sa.Index('idx_reconciliation_team', 'team_id'),
        sa.Index('idx_reconciliation_date', 'reconciliation_date'),
        sa.Index('idx_reconciliation_alert', 'alert_triggered'),
    )


def downgrade():
    """Drop reconciliation_history table"""
    op.drop_table('reconciliation_history')
