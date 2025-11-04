"""Add DLQ (Dead Letter Queue) tracking table

Revision ID: 004_add_dlq_tracking
Revises: 003_add_idempotency
Create Date: 2025-01-15

Tracks failed Celery tasks for replay and monitoring:
- Task identification (task_id, task_name, queue)
- Failure details (exception, traceback, retries)
- Replay tracking (status, replay_count)
- Monitoring support (indexes on status, queue, failed_at)

DLQ Flow:
1. Task fails after max retries → recorded in failed_tasks
2. Admin inspects via /admin/dlq endpoints
3. Admin replays or archives failed tasks
4. Monitoring alerts if DLQ depth > 0 for > 5 minutes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004_add_dlq_tracking'
down_revision = '003_add_idempotency'
branch_labels = None
depends_on = None


def upgrade():
    """Create failed_tasks table for DLQ tracking"""
    op.create_table(
        'failed_tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('task_id', sa.String(255), nullable=False, unique=True),
        sa.Column('task_name', sa.String(255), nullable=False),
        sa.Column('queue_name', sa.String(100), nullable=False, server_default='default'),

        # Task arguments (for replay)
        sa.Column('args', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('kwargs', postgresql.JSONB(), nullable=False, server_default='{}'),

        # Failure details
        sa.Column('exception_type', sa.String(255)),
        sa.Column('exception_message', sa.Text()),
        sa.Column('traceback', sa.Text()),
        sa.Column('retries_attempted', sa.Integer(), nullable=False, server_default='0'),

        # Timestamps
        sa.Column('failed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('replayed_at', sa.DateTime()),

        # Replay tracking
        sa.Column('status', sa.String(50), nullable=False, server_default='failed'),
        sa.Column('replayed_task_id', sa.String(255)),
        sa.Column('replay_count', sa.Integer(), nullable=False, server_default='0'),

        # Indexes for efficient queries
        sa.Index('idx_failedtask_status', 'status'),
        sa.Index('idx_failedtask_queue', 'queue_name'),
        sa.Index('idx_failedtask_task_name', 'task_name'),
        sa.Index('idx_failedtask_failed_at', 'failed_at'),
    )


def downgrade():
    """Drop failed_tasks table"""
    op.drop_table('failed_tasks')
