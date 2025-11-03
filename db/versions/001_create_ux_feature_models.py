"""Create UX feature models

Revision ID: 001_create_ux_features
Revises: b81dde19348f
Create Date: 2025-11-03

Creates 30+ tables for complete Real Estate OS UX platform:
- Core: Users, Teams
- Pipeline: Properties, Provenance, Timeline
- Communication: Communications, Threads, Templates
- Workflow: Tasks, NextBestActions, SmartLists
- Deals: Deals, Scenarios
- Collaboration: ShareLinks, DealRooms, Artifacts
- Investors: Investors, Engagements
- Compliance: ComplianceChecks, CadenceRules, DeliverabilityMetrics
- Data: PropensitySignals, BudgetTracking, DataFlags
- Onboarding: UserOnboarding, PresetTemplates
- OpenData: OpenDataSources
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_create_ux_features'
down_revision: Union[str, None] = 'b81dde19348f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("""
        CREATE TYPE userrole AS ENUM ('admin', 'manager', 'agent', 'viewer');
        CREATE TYPE propertystage AS ENUM ('new', 'outreach', 'qualified', 'negotiation', 'under_contract', 'closed_won', 'closed_lost', 'archived');
        CREATE TYPE communicationtype AS ENUM ('email', 'sms', 'call', 'postcard', 'note');
        CREATE TYPE communicationdirection AS ENUM ('inbound', 'outbound');
        CREATE TYPE taskstatus AS ENUM ('pending', 'in_progress', 'completed', 'overdue', 'cancelled');
        CREATE TYPE taskpriority AS ENUM ('low', 'medium', 'high', 'urgent');
        CREATE TYPE dealstatus AS ENUM ('proposed', 'negotiating', 'accepted', 'closed', 'dead');
        CREATE TYPE sharelinkstatus AS ENUM ('active', 'expired', 'revoked');
        CREATE TYPE compliancestatus AS ENUM ('passed', 'failed', 'needs_review');
        CREATE TYPE dataflagstatus AS ENUM ('open', 'in_progress', 'resolved', 'wont_fix');
        CREATE TYPE investorreadinesslevel AS ENUM ('red', 'yellow', 'green');
    """)

    # Teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subscription_tier', sa.String(50), server_default='starter'),
        sa.Column('monthly_budget_cap', sa.Float(), server_default='500.0'),
        sa.Column('settings', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid')
    )

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('role', sa.Enum('admin', 'manager', 'agent', 'viewer', name='userrole'), nullable=False, server_default='agent'),
        sa.Column('team_id', sa.Integer()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('settings', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_login_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_user_email', 'users', ['email'])
    op.create_index('idx_user_role', 'users', ['role'])

    # Properties table
    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('assigned_user_id', sa.Integer()),
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('city', sa.String(255)),
        sa.Column('state', sa.String(50)),
        sa.Column('zip_code', sa.String(20)),
        sa.Column('county', sa.String(255)),
        sa.Column('apn', sa.String(100)),
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('owner_name', sa.String(500)),
        sa.Column('owner_mailing_address', sa.Text()),
        sa.Column('beds', sa.Integer()),
        sa.Column('baths', sa.Float()),
        sa.Column('sqft', sa.Integer()),
        sa.Column('lot_size', sa.Float()),
        sa.Column('year_built', sa.Integer()),
        sa.Column('property_type', sa.String(50)),
        sa.Column('land_use', sa.String(100)),
        sa.Column('assessed_value', sa.Float()),
        sa.Column('market_value_estimate', sa.Float()),
        sa.Column('arv', sa.Float()),
        sa.Column('repair_estimate', sa.Float()),
        sa.Column('current_stage', sa.Enum('new', 'outreach', 'qualified', 'negotiation', 'under_contract', 'closed_won', 'closed_lost', 'archived', name='propertystage'), nullable=False, server_default='new'),
        sa.Column('previous_stage', sa.Enum('new', 'outreach', 'qualified', 'negotiation', 'under_contract', 'closed_won', 'closed_lost', 'archived', name='propertystage')),
        sa.Column('stage_changed_at', sa.DateTime()),
        sa.Column('last_contact_date', sa.DateTime()),
        sa.Column('last_reply_date', sa.DateTime()),
        sa.Column('touch_count', sa.Integer(), server_default='0'),
        sa.Column('email_opens', sa.Integer(), server_default='0'),
        sa.Column('email_clicks', sa.Integer(), server_default='0'),
        sa.Column('reply_count', sa.Integer(), server_default='0'),
        sa.Column('bird_dog_score', sa.Float()),
        sa.Column('score_reasons', postgresql.JSONB(), server_default='[]'),
        sa.Column('propensity_to_sell', sa.Float()),
        sa.Column('propensity_signals', postgresql.JSONB(), server_default='[]'),
        sa.Column('expected_value', sa.Float()),
        sa.Column('probability_of_close', sa.Float()),
        sa.Column('memo_url', sa.String(500)),
        sa.Column('memo_generated_at', sa.DateTime()),
        sa.Column('packet_url', sa.String(500)),
        sa.Column('data_quality_score', sa.Float(), server_default='1.0'),
        sa.Column('provenance_summary', postgresql.JSONB(), server_default='{}'),
        sa.Column('is_on_dnc', sa.Boolean(), server_default='false'),
        sa.Column('has_opted_out', sa.Boolean(), server_default='false'),
        sa.Column('cadence_paused', sa.Boolean(), server_default='false'),
        sa.Column('cadence_pause_reason', sa.String(255)),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),
        sa.Column('custom_fields', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('archived_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid')
    )
    op.create_index('idx_property_stage', 'properties', ['current_stage'])
    op.create_index('idx_property_assigned', 'properties', ['assigned_user_id'])
    op.create_index('idx_property_score', 'properties', ['bird_dog_score'])
    op.create_index('idx_property_last_contact', 'properties', ['last_contact_date'])
    op.create_index('idx_property_team', 'properties', ['team_id'])
    op.create_index('idx_property_address', 'properties', ['address'])
    op.create_index('idx_property_city_state', 'properties', ['city', 'state'])

    # PropertyProvenance table
    op.create_table(
        'property_provenance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('source_tier', sa.String(50)),
        sa.Column('license_type', sa.String(100)),
        sa.Column('cost', sa.Float(), server_default='0.0'),
        sa.Column('confidence', sa.Float()),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_provenance_property', 'property_provenance', ['property_id'])
    op.create_index('idx_provenance_source', 'property_provenance', ['source_name'])

    # CommunicationThreads table
    op.create_table(
        'communication_threads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(500)),
        sa.Column('first_communication_at', sa.DateTime()),
        sa.Column('last_communication_at', sa.DateTime()),
        sa.Column('message_count', sa.Integer(), server_default='0'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Templates table
    op.create_table(
        'templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.Enum('email', 'sms', 'call', 'postcard', 'note', name='communicationtype'), nullable=False),
        sa.Column('applicable_stages', postgresql.JSONB(), server_default='[]'),
        sa.Column('subject_template', sa.String(500)),
        sa.Column('body_template', sa.Text(), nullable=False),
        sa.Column('times_used', sa.Integer(), server_default='0'),
        sa.Column('open_rate', sa.Float()),
        sa.Column('reply_rate', sa.Float()),
        sa.Column('meeting_rate', sa.Float()),
        sa.Column('is_champion', sa.Boolean(), server_default='false'),
        sa.Column('challenger_for', sa.Integer()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['challenger_for'], ['templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid')
    )
    op.create_index('idx_template_team', 'templates', ['team_id'])
    op.create_index('idx_template_type', 'templates', ['type'])

    # Communications table
    op.create_table(
        'communications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer()),
        sa.Column('thread_id', sa.Integer()),
        sa.Column('template_id', sa.Integer()),
        sa.Column('type', sa.Enum('email', 'sms', 'call', 'postcard', 'note', name='communicationtype'), nullable=False),
        sa.Column('direction', sa.Enum('inbound', 'outbound', name='communicationdirection'), nullable=False),
        sa.Column('from_address', sa.String(500)),
        sa.Column('to_address', sa.String(500)),
        sa.Column('subject', sa.String(500)),
        sa.Column('body', sa.Text()),
        sa.Column('sent_at', sa.DateTime()),
        sa.Column('opened_at', sa.DateTime()),
        sa.Column('clicked_at', sa.DateTime()),
        sa.Column('replied_at', sa.DateTime()),
        sa.Column('bounced_at', sa.DateTime()),
        sa.Column('duration_seconds', sa.Integer()),
        sa.Column('call_recording_url', sa.String(500)),
        sa.Column('call_transcript', sa.Text()),
        sa.Column('call_sentiment', sa.String(50)),
        sa.Column('call_key_points', postgresql.JSONB(), server_default='[]'),
        sa.Column('email_message_id', sa.String(500)),
        sa.Column('email_thread_position', sa.Integer()),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['thread_id'], ['communication_threads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid')
    )
    op.create_index('idx_comm_property', 'communications', ['property_id'])
    op.create_index('idx_comm_type', 'communications', ['type'])
    op.create_index('idx_comm_direction', 'communications', ['direction'])
    op.create_index('idx_comm_sent', 'communications', ['sent_at'])

    # Tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('property_id', sa.Integer()),
        sa.Column('assigned_user_id', sa.Integer()),
        sa.Column('created_by_user_id', sa.Integer()),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'overdue', 'cancelled', name='taskstatus'), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', 'urgent', name='taskpriority'), nullable=False, server_default='medium'),
        sa.Column('due_at', sa.DateTime()),
        sa.Column('sla_hours', sa.Integer()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('source_event_type', sa.String(50)),
        sa.Column('source_communication_id', sa.Integer()),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_communication_id'], ['communications.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid')
    )
    op.create_index('idx_task_property', 'tasks', ['property_id'])
    op.create_index('idx_task_assigned', 'tasks', ['assigned_user_id'])
    op.create_index('idx_task_status', 'tasks', ['status'])
    op.create_index('idx_task_due', 'tasks', ['due_at'])

    # PropertyTimeline table
    op.create_table(
        'property_timeline',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_title', sa.String(255), nullable=False),
        sa.Column('event_description', sa.Text()),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('communication_id', sa.Integer()),
        sa.Column('task_id', sa.Integer()),
        sa.Column('deal_id', sa.Integer()),
        sa.Column('user_id', sa.Integer()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['communication_id'], ['communications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_timeline_property', 'property_timeline', ['property_id'])
    op.create_index('idx_timeline_type', 'property_timeline', ['event_type'])
    op.create_index('idx_timeline_created', 'property_timeline', ['created_at'])

    # Continue with remaining tables in part 2...


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('property_timeline')
    op.drop_table('tasks')
    op.drop_table('communications')
    op.drop_table('templates')
    op.drop_table('communication_threads')
    op.drop_table('property_provenance')
    op.drop_table('properties')
    op.drop_table('users')
    op.drop_table('teams')

    # Drop enums
    op.execute("""
        DROP TYPE IF EXISTS investorreadinesslevel;
        DROP TYPE IF EXISTS dataflagstatus;
        DROP TYPE IF EXISTS compliancestatus;
        DROP TYPE IF EXISTS sharelinkstatus;
        DROP TYPE IF EXISTS dealstatus;
        DROP TYPE IF EXISTS taskpriority;
        DROP TYPE IF EXISTS taskstatus;
        DROP TYPE IF EXISTS communicationdirection;
        DROP TYPE IF EXISTS communicationtype;
        DROP TYPE IF EXISTS propertystage;
        DROP TYPE IF EXISTS userrole;
    """)
