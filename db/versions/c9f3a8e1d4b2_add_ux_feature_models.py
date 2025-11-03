"""Add UX feature models for pipeline, communications, and workflow management

Revision ID: c9f3a8e1d4b2
Revises: b81dde19348f
Create Date: 2025-11-03 03:05:00.000000

This migration adds comprehensive tables for:
- Property pipeline management
- User authentication and teams
- Communications (email, SMS, calls) with threading
- Tasks and workflow automation
- Deal tracking with economics
- Templates and smart lists
- Compliance and deliverability tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9f3a8e1d4b2'
down_revision: Union[str, Sequence[str], None] = 'b81dde19348f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create all new tables for UX features"""

    # Create enums
    pipelinestage_enum = postgresql.ENUM(
        'prospect', 'enrichment', 'scored', 'outreach', 'contact_made',
        'negotiation', 'packet_sent', 'offer', 'won', 'lost', 'archived',
        name='pipelinestage_enum', create_type=True
    )
    communicationtype_enum = postgresql.ENUM(
        'email', 'sms', 'call', 'postcard', 'note',
        name='communicationtype_enum', create_type=True
    )
    communicationdirection_enum = postgresql.ENUM(
        'inbound', 'outbound',
        name='communicationdirection_enum', create_type=True
    )
    taskstatus_enum = postgresql.ENUM(
        'pending', 'in_progress', 'completed', 'cancelled', 'overdue',
        name='taskstatus_enum', create_type=True
    )
    taskpriority_enum = postgresql.ENUM(
        'low', 'medium', 'high', 'urgent',
        name='taskpriority_enum', create_type=True
    )
    dealstatus_enum = postgresql.ENUM(
        'active', 'won', 'lost', 'cancelled',
        name='dealstatus_enum', create_type=True
    )
    userrole_enum = postgresql.ENUM(
        'admin', 'manager', 'agent', 'viewer',
        name='userrole_enum', create_type=True
    )

    # Create enums in database
    pipelinestage_enum.create(op.get_bind(), checkfirst=True)
    communicationtype_enum.create(op.get_bind(), checkfirst=True)
    communicationdirection_enum.create(op.get_bind(), checkfirst=True)
    taskstatus_enum.create(op.get_bind(), checkfirst=True)
    taskpriority_enum.create(op.get_bind(), checkfirst=True)
    dealstatus_enum.create(op.get_bind(), checkfirst=True)
    userrole_enum.create(op.get_bind(), checkfirst=True)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', userrole_enum, nullable=False, server_default='agent'),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create pipeline_stages table
    op.create_table(
        'pipeline_stages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pipeline_stages_slug'), 'pipeline_stages', ['slug'], unique=True)

    # Create properties table
    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prospect_queue_id', sa.Integer(), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=2), nullable=True),
        sa.Column('zip_code', sa.String(length=10), nullable=True),
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('apn', sa.String(length=50), nullable=True),
        sa.Column('beds', sa.Integer(), nullable=True),
        sa.Column('baths', sa.Float(), nullable=True),
        sa.Column('sqft', sa.Integer(), nullable=True),
        sa.Column('lot_size', sa.Integer(), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('property_type', sa.String(length=50), nullable=True),
        sa.Column('assessed_value', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('market_value', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('asking_price', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('last_sale_price', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('last_sale_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('owner_name', sa.String(length=255), nullable=True),
        sa.Column('owner_type', sa.String(length=50), nullable=True),
        sa.Column('owner_occupied', sa.Boolean(), nullable=True),
        sa.Column('mailing_address', sa.Text(), nullable=True),
        sa.Column('owner_phone', sa.String(length=50), nullable=True),
        sa.Column('owner_email', sa.String(length=255), nullable=True),
        sa.Column('current_stage', sa.String(length=100), nullable=False, server_default='prospect'),
        sa.Column('assigned_user_id', sa.Integer(), nullable=True),
        sa.Column('bird_dog_score', sa.Float(), nullable=True),
        sa.Column('probability_close', sa.Float(), nullable=True),
        sa.Column('expected_value', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('owner_propensity_score', sa.Float(), nullable=True),
        sa.Column('propensity_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('data_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('data_sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('last_contact_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_reply_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('total_touches', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('reply_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('memo_generated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('memo_url', sa.Text(), nullable=True),
        sa.Column('packet_generated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('packet_url', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('archived_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_properties_apn'), 'properties', ['apn'])
    op.create_index(op.f('ix_properties_assigned_user_id'), 'properties', ['assigned_user_id'])
    op.create_index(op.f('ix_properties_created_at'), 'properties', ['created_at'])
    op.create_index(op.f('ix_properties_current_stage'), 'properties', ['current_stage'])
    op.create_index(op.f('ix_properties_prospect_queue_id'), 'properties', ['prospect_queue_id'])
    op.create_index('idx_property_stage_assigned', 'properties', ['current_stage', 'assigned_user_id'])
    op.create_index('idx_property_score', 'properties', ['bird_dog_score'])
    op.create_index('idx_property_created', 'properties', ['created_at'])

    # Create property_stage_history table
    op.create_table(
        'property_stage_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('from_stage', sa.String(length=100), nullable=True),
        sa.Column('to_stage', sa.String(length=100), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_property_stage_history_property_id'), 'property_stage_history', ['property_id'])

    # Create templates table
    op.create_table(
        'templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', communicationtype_enum, nullable=False),
        sa.Column('allowed_stages', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('send_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('open_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('reply_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('meeting_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_champion', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('variant_group', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create communications table
    op.create_table(
        'communications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('type', communicationtype_enum, nullable=False),
        sa.Column('direction', communicationdirection_enum, nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=True),
        sa.Column('message_id', sa.String(length=255), nullable=True),
        sa.Column('in_reply_to', sa.String(length=255), nullable=True),
        sa.Column('from_address', sa.String(length=255), nullable=True),
        sa.Column('to_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('cc_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('opened_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('clicked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('replied_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('bounced_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('call_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('call_recording_url', sa.Text(), nullable=True),
        sa.Column('call_transcription', sa.Text(), nullable=True),
        sa.Column('call_summary', sa.Text(), nullable=True),
        sa.Column('call_sentiment', sa.String(length=20), nullable=True),
        sa.Column('call_action_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_communications_created_at'), 'communications', ['created_at'])
    op.create_index(op.f('ix_communications_message_id'), 'communications', ['message_id'], unique=True)
    op.create_index(op.f('ix_communications_property_id'), 'communications', ['property_id'])
    op.create_index(op.f('ix_communications_thread_id'), 'communications', ['thread_id'])
    op.create_index('idx_communication_property_type', 'communications', ['property_id', 'type'])
    op.create_index('idx_communication_thread', 'communications', ['thread_id'])
    op.create_index('idx_communication_sent', 'communications', ['sent_at'])

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('status', taskstatus_enum, nullable=False, server_default='pending'),
        sa.Column('priority', taskpriority_enum, nullable=False, server_default='medium'),
        sa.Column('due_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('sla_hours', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_assignee_id'), 'tasks', ['assignee_id'])
    op.create_index(op.f('ix_tasks_due_date'), 'tasks', ['due_date'])
    op.create_index(op.f('ix_tasks_property_id'), 'tasks', ['property_id'])
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'])
    op.create_index('idx_task_assignee_status', 'tasks', ['assignee_id', 'status'])
    op.create_index('idx_task_due_date', 'tasks', ['due_date'])

    # Create timeline_events table
    op.create_table(
        'timeline_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('related_type', sa.String(length=50), nullable=True),
        sa.Column('related_id', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_timeline_events_created_at'), 'timeline_events', ['created_at'])
    op.create_index(op.f('ix_timeline_events_property_id'), 'timeline_events', ['property_id'])
    op.create_index('idx_timeline_property_created', 'timeline_events', ['property_id', 'created_at'])

    # Create deals table
    op.create_table(
        'deals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('status', dealstatus_enum, nullable=False, server_default='active'),
        sa.Column('offer_price', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('assignment_fee', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('estimated_margin', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('expected_value', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('probability_close', sa.Float(), nullable=True),
        sa.Column('probability_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('offer_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('expected_close_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('actual_close_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('days_to_close', sa.Integer(), nullable=True),
        sa.Column('investor_name', sa.String(length=255), nullable=True),
        sa.Column('investor_email', sa.String(length=255), nullable=True),
        sa.Column('investor_phone', sa.String(length=50), nullable=True),
        sa.Column('has_packet', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('packet_sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deals_property_id'), 'deals', ['property_id'])
    op.create_index(op.f('ix_deals_status'), 'deals', ['status'])

    # Create deal_documents table
    op.create_table(
        'deal_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('deal_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=True),
        sa.Column('file_url', sa.Text(), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deal_documents_deal_id'), 'deal_documents', ['deal_id'])

    # Create investor_shares table
    op.create_table(
        'investor_shares',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('share_token', sa.String(length=100), nullable=False),
        sa.Column('share_url', sa.Text(), nullable=True),
        sa.Column('investor_email', sa.String(length=255), nullable=True),
        sa.Column('requires_email', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('watermark_text', sa.String(length=255), nullable=True),
        sa.Column('allow_download', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('view_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_viewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('has_questions', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_investor_shares_property_id'), 'investor_shares', ['property_id'])
    op.create_index(op.f('ix_investor_shares_share_token'), 'investor_shares', ['share_token'], unique=True)

    # Create data_flags table
    op.create_table(
        'data_flags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('issue_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('suggested_value', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('reported_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reported_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_flags_property_id'), 'data_flags', ['property_id'])
    op.create_index(op.f('ix_data_flags_status'), 'data_flags', ['status'])

    # Create smart_lists table
    op.create_table(
        'smart_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('is_shared', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('property_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_refreshed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create next_best_actions table
    op.create_table(
        'next_best_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('priority_score', sa.Float(), nullable=True),
        sa.Column('signals', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('is_completed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('dismissed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_next_best_actions_created_at'), 'next_best_actions', ['created_at'])
    op.create_index(op.f('ix_next_best_actions_property_id'), 'next_best_actions', ['property_id'])
    op.create_index('idx_nba_property_completed', 'next_best_actions', ['property_id', 'is_completed'])

    # Create compliance_records table
    op.create_table(
        'compliance_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('record_type', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('effective_date', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compliance_records_email'), 'compliance_records', ['email'])
    op.create_index(op.f('ix_compliance_records_phone'), 'compliance_records', ['phone'])
    op.create_index('idx_compliance_phone_active', 'compliance_records', ['phone', 'is_active'])
    op.create_index('idx_compliance_email_active', 'compliance_records', ['email', 'is_active'])

    # Create deliverability_metrics table
    op.create_table(
        'deliverability_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('sender', sa.String(length=255), nullable=False),
        sa.Column('sent_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('delivered_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('bounced_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('opened_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('clicked_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('spam_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('unsubscribed_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('delivery_rate', sa.Float(), nullable=True),
        sa.Column('bounce_rate', sa.Float(), nullable=True),
        sa.Column('open_rate', sa.Float(), nullable=True),
        sa.Column('click_rate', sa.Float(), nullable=True),
        sa.Column('spam_rate', sa.Float(), nullable=True),
        sa.Column('reputation_score', sa.Float(), nullable=True),
        sa.Column('warmup_status', sa.String(length=50), nullable=True),
        sa.Column('has_alerts', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('alerts', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deliverability_metrics_date'), 'deliverability_metrics', ['date'])
    op.create_index(op.f('ix_deliverability_metrics_sender'), 'deliverability_metrics', ['sender'])
    op.create_index('idx_deliverability_sender_date', 'deliverability_metrics', ['sender', 'date'])

    # Create cadence_rules table
    op.create_table(
        'cadence_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trigger_type', sa.String(length=100), nullable=False),
        sa.Column('trigger_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('action_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('triggered_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_triggered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create budget_monitors table
    op.create_table(
        'budget_monitors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('period_end', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('email_cap', sa.Integer(), nullable=True),
        sa.Column('sms_cap', sa.Integer(), nullable=True),
        sa.Column('call_minutes_cap', sa.Integer(), nullable=True),
        sa.Column('data_cost_cap', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('email_sent', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('sms_sent', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('call_minutes_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('data_cost', sa.DECIMAL(precision=10, scale=2), nullable=True, server_default='0'),
        sa.Column('alert_threshold', sa.Float(), nullable=True, server_default='0.8'),
        sa.Column('alerts_sent', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_budget_period', 'budget_monitors', ['period_start', 'period_end'])


def downgrade() -> None:
    """Downgrade schema - drop all new tables"""

    # Drop tables in reverse order (to handle foreign keys)
    op.drop_table('budget_monitors')
    op.drop_table('cadence_rules')
    op.drop_table('deliverability_metrics')
    op.drop_table('compliance_records')
    op.drop_table('next_best_actions')
    op.drop_table('smart_lists')
    op.drop_table('data_flags')
    op.drop_table('investor_shares')
    op.drop_table('deal_documents')
    op.drop_table('deals')
    op.drop_table('timeline_events')
    op.drop_table('tasks')
    op.drop_table('communications')
    op.drop_table('templates')
    op.drop_table('property_stage_history')
    op.drop_table('properties')
    op.drop_table('pipeline_stages')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS userrole_enum CASCADE')
    op.execute('DROP TYPE IF EXISTS dealstatus_enum CASCADE')
    op.execute('DROP TYPE IF EXISTS taskpriority_enum CASCADE')
    op.execute('DROP TYPE IF EXISTS taskstatus_enum CASCADE')
    op.execute('DROP TYPE IF EXISTS communicationdirection_enum CASCADE')
    op.execute('DROP TYPE IF EXISTS communicationtype_enum CASCADE')
    op.execute('DROP TYPE IF EXISTS pipelinestage_enum CASCADE')
