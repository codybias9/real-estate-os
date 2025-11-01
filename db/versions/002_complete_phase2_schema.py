"""Complete Phase 2-8 schema with all tables

Revision ID: 002_complete_phase2
Revises: b81dde19348f
Create Date: 2025-11-01

This migration adds all required tables for the real estate automation platform:
- property_enrichment: Enriched property data from various APIs
- property_scores: ML model scores and embeddings
- action_packets: Generated investment packets (PDFs)
- email_queue: Outbound email tracking
- ml_models: ML model registry and versioning
- user_accounts: User authentication and management
- tenants: Multi-tenant support
- audit_log: System audit trail
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_complete_phase2'
down_revision = 'b81dde19348f'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================
    # Table: property_enrichment
    # ========================================
    op.create_table(
        'property_enrichment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('prospect_id', sa.Integer(), nullable=False),
        sa.Column('apn', sa.String(255), nullable=True),
        sa.Column('square_footage', sa.Integer(), nullable=True),
        sa.Column('bedrooms', sa.Integer(), nullable=True),
        sa.Column('bathrooms', sa.Numeric(3, 1), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('assessed_value', sa.Numeric(12, 2), nullable=True),
        sa.Column('market_value', sa.Numeric(12, 2), nullable=True),
        sa.Column('last_sale_date', sa.Date(), nullable=True),
        sa.Column('last_sale_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('zoning', sa.String(100), nullable=True),
        sa.Column('lot_size_sqft', sa.Integer(), nullable=True),
        sa.Column('property_type', sa.String(50), nullable=True),
        sa.Column('owner_name', sa.String(255), nullable=True),
        sa.Column('owner_mailing_address', sa.Text(), nullable=True),
        sa.Column('tax_amount_annual', sa.Numeric(10, 2), nullable=True),
        sa.Column('source_api', sa.String(100), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospect_queue.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('prospect_id', name='unique_prospect_enrichment')
    )

    # Indexes for property_enrichment
    op.create_index('idx_property_enrichment_prospect', 'property_enrichment', ['prospect_id'])
    op.create_index('idx_property_enrichment_apn', 'property_enrichment', ['apn'])

    # ========================================
    # Table: property_scores
    # ========================================
    op.create_table(
        'property_scores',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('prospect_id', sa.Integer(), nullable=False),
        sa.Column('enrichment_id', sa.Integer(), nullable=True),
        sa.Column('bird_dog_score', sa.Numeric(5, 2), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('feature_vector', postgresql.JSONB(), nullable=True),  # Store as JSONB for now
        sa.Column('feature_importance', postgresql.JSONB(), nullable=True),
        sa.Column('score_breakdown', postgresql.JSONB(), nullable=True),
        sa.Column('confidence_level', sa.Numeric(5, 2), nullable=True),
        sa.Column('qdrant_point_id', sa.String(100), nullable=True),  # Reference to Qdrant vector
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospect_queue.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['enrichment_id'], ['property_enrichment.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('prospect_id', name='unique_prospect_score')
    )

    # Indexes for property_scores
    op.create_index('idx_property_scores_prospect', 'property_scores', ['prospect_id'])
    op.create_index('idx_property_scores_score', 'property_scores', ['bird_dog_score'], postgresql_ops={'bird_dog_score': 'DESC'})
    op.create_index('idx_property_scores_model', 'property_scores', ['model_version'])

    # ========================================
    # Table: ml_models
    # ========================================
    op.create_table(
        'ml_models',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=True),  # lightgbm, neural_net, etc.
        sa.Column('model_path', sa.String(500), nullable=False),  # MinIO path
        sa.Column('training_date', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('metrics', postgresql.JSONB(), nullable=True),  # accuracy, precision, recall
        sa.Column('hyperparameters', postgresql.JSONB(), nullable=True),
        sa.Column('feature_names', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.UniqueConstraint('model_name', 'model_version', name='unique_model_version')
    )

    # Indexes for ml_models
    op.create_index('idx_ml_models_active', 'ml_models', ['is_active'], postgresql_where=sa.text('is_active = true'))
    op.create_index('idx_ml_models_name', 'ml_models', ['model_name'])

    # ========================================
    # Table: action_packets
    # ========================================
    op.create_table(
        'action_packets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('prospect_id', sa.Integer(), nullable=False),
        sa.Column('score_id', sa.Integer(), nullable=True),
        sa.Column('packet_path', sa.String(500), nullable=False),  # MinIO path
        sa.Column('packet_url', sa.Text(), nullable=True),  # Pre-signed URL
        sa.Column('packet_type', sa.String(50), default='investor_memo'),
        sa.Column('generated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('template_version', sa.String(50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospect_queue.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['score_id'], ['property_scores.id'], ondelete='CASCADE')
    )

    # Indexes for action_packets
    op.create_index('idx_action_packets_prospect', 'action_packets', ['prospect_id'])
    op.create_index('idx_action_packets_score', 'action_packets', ['score_id'])
    op.create_index('idx_action_packets_generated', 'action_packets', ['generated_at'])

    # ========================================
    # Table: email_queue
    # ========================================
    op.create_table(
        'email_queue',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('packet_id', sa.Integer(), nullable=True),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('recipient_name', sa.String(255), nullable=True),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),  # pending, sent, failed, bounced
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('opened_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('clicked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('sendgrid_message_id', sa.String(255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['packet_id'], ['action_packets.id'], ondelete='CASCADE')
    )

    # Indexes for email_queue
    op.create_index('idx_email_queue_status', 'email_queue', ['status'])
    op.create_index('idx_email_queue_recipient', 'email_queue', ['recipient_email'])
    op.create_index('idx_email_queue_packet', 'email_queue', ['packet_id'])
    op.create_index('idx_email_queue_created', 'email_queue', ['created_at'])

    # ========================================
    # Table: user_accounts (Phase 8)
    # ========================================
    op.create_table(
        'user_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('organization', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), default='user'),  # admin, user, viewer
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('password_reset_token', sa.String(255), nullable=True),
        sa.Column('password_reset_expires', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('last_login', sa.TIMESTAMP(timezone=True), nullable=True)
    )

    # Indexes for user_accounts
    op.create_index('idx_user_accounts_email', 'user_accounts', ['email'])
    op.create_index('idx_user_accounts_active', 'user_accounts', ['is_active'])

    # ========================================
    # Table: tenants (Phase 8)
    # ========================================
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_name', sa.String(255), nullable=False, unique=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('plan_tier', sa.String(50), default='free'),  # free, professional, enterprise
        sa.Column('status', sa.String(50), default='active'),  # active, suspended, deleted
        sa.Column('settings', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['owner_id'], ['user_accounts.id'], ondelete='SET NULL')
    )

    # Indexes for tenants
    op.create_index('idx_tenants_slug', 'tenants', ['slug'])
    op.create_index('idx_tenants_status', 'tenants', ['status'])

    # ========================================
    # Table: audit_log
    # ========================================
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL')
    )

    # Indexes for audit_log
    op.create_index('idx_audit_log_user', 'audit_log', ['user_id'])
    op.create_index('idx_audit_log_tenant', 'audit_log', ['tenant_id'])
    op.create_index('idx_audit_log_created', 'audit_log', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_audit_log_action', 'audit_log', ['action'])

    # ========================================
    # Additional Table: email_campaigns (for Phase 6)
    # ========================================
    op.create_table(
        'email_campaigns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), default='draft'),  # draft, scheduled, sending, sent, failed
        sa.Column('scheduled_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('total_recipients', sa.Integer(), default=0),
        sa.Column('emails_sent', sa.Integer(), default=0),
        sa.Column('emails_opened', sa.Integer(), default=0),
        sa.Column('emails_clicked', sa.Integer(), default=0),
        sa.Column('emails_bounced', sa.Integer(), default=0),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by'], ['user_accounts.id'], ondelete='SET NULL')
    )

    # Indexes for email_campaigns
    op.create_index('idx_email_campaigns_status', 'email_campaigns', ['status'])
    op.create_index('idx_email_campaigns_scheduled', 'email_campaigns', ['scheduled_at'])

    # ========================================
    # Create triggers for updated_at columns
    # ========================================
    # Trigger already exists for prospect_queue from previous migration

    # Trigger for property_enrichment
    op.execute("""
        CREATE TRIGGER update_property_enrichment_updated_at
        BEFORE UPDATE ON property_enrichment
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Trigger for email_queue
    op.execute("""
        CREATE TRIGGER update_email_queue_updated_at
        BEFORE UPDATE ON email_queue
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Trigger for tenants
    op.execute("""
        CREATE TRIGGER update_tenants_updated_at
        BEFORE UPDATE ON tenants
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Trigger for email_campaigns
    op.execute("""
        CREATE TRIGGER update_email_campaigns_updated_at
        BEFORE UPDATE ON email_campaigns
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_email_campaigns_updated_at ON email_campaigns;")
    op.execute("DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants;")
    op.execute("DROP TRIGGER IF EXISTS update_email_queue_updated_at ON email_queue;")
    op.execute("DROP TRIGGER IF EXISTS update_property_enrichment_updated_at ON property_enrichment;")

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('audit_log')
    op.drop_table('email_campaigns')
    op.drop_table('email_queue')
    op.drop_table('action_packets')
    op.drop_table('property_scores')
    op.drop_table('ml_models')
    op.drop_table('property_enrichment')
    op.drop_table('tenants')
    op.drop_table('user_accounts')
