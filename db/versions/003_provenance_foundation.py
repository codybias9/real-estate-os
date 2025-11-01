"""Create provenance and multi-tenant foundation

Revision ID: 003_provenance_foundation
Revises: 002_complete_phase2_schema
Create Date: 2025-11-01 18:00:00.000000

This migration implements the Deal Genome / Provenance system with:
- Multi-tenant foundation (tenant table)
- Deterministic entity IDs (property, owner_entity)
- Field-level provenance tracking
- Score explainability
- Trust ledger (evidence events)
- RLS (Row-Level Security) policies

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_provenance_foundation'
down_revision = '002_complete_phase2_schema'
branch_labels = None
depends_on = None


def upgrade():
    # =====================================================================
    # 1. TENANCY FOUNDATION
    # =====================================================================

    op.create_table(
        'tenant',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('plan_tier', sa.String(50), nullable=False, server_default='free'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('settings', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_index('idx_tenant_slug', 'tenant', ['slug'])
    op.create_index('idx_tenant_status', 'tenant', ['status'])

    # =====================================================================
    # 2. DETERMINISTIC ENTITY IDs
    # =====================================================================

    op.create_table(
        'property',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('canonical_address', postgresql.JSONB, nullable=False),
        sa.Column('parcel', sa.String(255)),
        sa.Column('lat', sa.Float),
        sa.Column('lon', sa.Float),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE')
    )

    op.create_index('idx_property_tenant', 'property', ['tenant_id'])
    op.create_index('idx_property_parcel', 'property', ['tenant_id', 'parcel'])
    op.create_index('idx_property_location', 'property', ['tenant_id', 'lat', 'lon'])

    op.create_table(
        'owner_entity',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('identity_hash', sa.String(64)),  # For deduplication
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.CheckConstraint("type IN ('person', 'company')", name='owner_entity_type_check')
    )

    op.create_index('idx_owner_entity_tenant', 'owner_entity', ['tenant_id'])
    op.create_index('idx_owner_entity_identity', 'owner_entity', ['tenant_id', 'identity_hash'])

    op.create_table(
        'property_owner_link',
        sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(100)),  # 'owner', 'trustee', 'beneficiary', etc.
        sa.Column('confidence', sa.Numeric(5, 2)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('property_id', 'owner_entity_id'),
        sa.ForeignKeyConstraint(['property_id'], ['property.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_entity_id'], ['owner_entity.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE')
    )

    op.create_index('idx_property_owner_link_tenant', 'property_owner_link', ['tenant_id'])

    # =====================================================================
    # 3. FIELD PROVENANCE & HISTORY
    # =====================================================================

    op.create_table(
        'field_provenance',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),  # 'property', 'owner', 'deal', etc.
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_path', sa.String(255), nullable=False),  # JSON path notation (e.g., 'bedrooms', 'assessment.value')
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('source_system', sa.String(100)),  # 'census_api', 'fsbo_scraper', 'manual', etc.
        sa.Column('source_url', sa.Text),
        sa.Column('method', sa.String(50)),  # 'scrape', 'api', 'manual', 'computed'
        sa.Column('confidence', sa.Numeric(5, 2)),  # 0.00 to 1.00
        sa.Column('version', sa.Integer, nullable=False),  # Incremental version per field
        sa.Column('extracted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE')
    )

    op.create_index('idx_field_provenance_tenant', 'field_provenance', ['tenant_id'])
    op.create_index('idx_field_provenance_entity', 'field_provenance', ['tenant_id', 'entity_type', 'entity_id'])
    op.create_index('idx_field_provenance_field', 'field_provenance', ['tenant_id', 'entity_type', 'entity_id', 'field_path'])
    op.create_index('idx_field_provenance_version', 'field_provenance', ['tenant_id', 'entity_type', 'entity_id', 'field_path', 'version'])

    # =====================================================================
    # 4. SCORING & EXPLAINABILITY
    # =====================================================================

    op.create_table(
        'scorecard',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('score', sa.Numeric(5, 2), nullable=False),  # 0-100
        sa.Column('grade', sa.String(10)),  # A, B, C, D, F
        sa.Column('confidence', sa.Numeric(5, 2)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['property.id'], ondelete='CASCADE')
    )

    op.create_index('idx_scorecard_tenant', 'scorecard', ['tenant_id'])
    op.create_index('idx_scorecard_property', 'scorecard', ['tenant_id', 'property_id'])
    op.create_index('idx_scorecard_score', 'scorecard', ['tenant_id', 'score'])

    op.create_table(
        'score_explainability',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('scorecard_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shap_values', postgresql.JSONB, nullable=False),  # SHAP values for each feature
        sa.Column('drivers', postgresql.JSONB, nullable=False),  # Top positive/negative drivers
        sa.Column('counterfactuals', postgresql.JSONB),  # Minimal changes to flip grade
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['scorecard_id'], ['scorecard.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE')
    )

    op.create_index('idx_score_explainability_tenant', 'score_explainability', ['tenant_id'])

    # =====================================================================
    # 5. DEALS & PACKET TELEMETRY
    # =====================================================================

    op.create_table(
        'deal',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage', sa.String(50), nullable=False, server_default='lead'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['property.id'], ondelete='CASCADE'),
        sa.CheckConstraint("stage IN ('lead', 'qualified', 'offer', 'contract', 'closed', 'lost')", name='deal_stage_check')
    )

    op.create_index('idx_deal_tenant', 'deal', ['tenant_id'])
    op.create_index('idx_deal_property', 'deal', ['tenant_id', 'property_id'])
    op.create_index('idx_deal_stage', 'deal', ['tenant_id', 'stage'])

    op.create_table(
        'packet_event',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('meta', postgresql.JSONB, server_default='{}'),
        sa.Column('occurred_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['deal_id'], ['deal.id'], ondelete='CASCADE'),
        sa.CheckConstraint("type IN ('generated', 'opened', 'clicked', 'downloaded', 'shared')", name='packet_event_type_check')
    )

    op.create_index('idx_packet_event_tenant', 'packet_event', ['tenant_id'])
    op.create_index('idx_packet_event_deal', 'packet_event', ['tenant_id', 'deal_id'])
    op.create_index('idx_packet_event_occurred', 'packet_event', ['tenant_id', 'occurred_at'])

    # =====================================================================
    # 6. OUTREACH & COMPLIANCE
    # =====================================================================

    op.create_table(
        'contact_suppression',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('identity_hash', sa.String(64), nullable=False),  # SHA256 of contact info
        sa.Column('reason', sa.String(255)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.CheckConstraint("channel IN ('email', 'sms', 'voice', 'mail')", name='contact_suppression_channel_check')
    )

    op.create_index('idx_contact_suppression_tenant', 'contact_suppression', ['tenant_id'])
    op.create_index('idx_contact_suppression_lookup', 'contact_suppression', ['tenant_id', 'channel', 'identity_hash'])

    # =====================================================================
    # 7. TRUST LEDGER (Evidence Events)
    # =====================================================================

    op.create_table(
        'evidence_event',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_type', sa.String(50)),  # 'property', 'deal', 'offer', etc.
        sa.Column('subject_id', postgresql.UUID(as_uuid=True)),
        sa.Column('kind', sa.String(100), nullable=False),  # 'comps_rationale', 'consent', 'override', 'claim'
        sa.Column('summary', sa.Text),
        sa.Column('uri', sa.Text),  # MinIO path to supporting documents
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),  # User ID
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE')
    )

    op.create_index('idx_evidence_event_tenant', 'evidence_event', ['tenant_id'])
    op.create_index('idx_evidence_event_subject', 'evidence_event', ['tenant_id', 'subject_type', 'subject_id'])
    op.create_index('idx_evidence_event_created', 'evidence_event', ['tenant_id', 'created_at'])

    # =====================================================================
    # 8. ROW-LEVEL SECURITY (RLS) POLICIES
    # =====================================================================

    # Enable RLS on all tenant-scoped tables
    tables_with_rls = [
        'property',
        'owner_entity',
        'property_owner_link',
        'field_provenance',
        'scorecard',
        'score_explainability',
        'deal',
        'packet_event',
        'contact_suppression',
        'evidence_event'
    ]

    for table in tables_with_rls:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')

        # Create policy: users can only see their tenant's data
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        """)

    # =====================================================================
    # 9. TRIGGERS FOR UPDATED_AT
    # =====================================================================

    tables_with_updated_at = [
        'tenant',
        'property',
        'owner_entity',
        'deal'
    ]

    for table in tables_with_updated_at:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
        """)

    # =====================================================================
    # 10. CREATE DEFAULT TENANT (for migration compatibility)
    # =====================================================================

    op.execute("""
        INSERT INTO tenant (id, name, slug, plan_tier, status)
        VALUES (
            '00000000-0000-0000-0000-000000000001'::uuid,
            'Default Tenant',
            'default',
            'enterprise',
            'active'
        )
        ON CONFLICT DO NOTHING
    """)


def downgrade():
    # Drop triggers
    tables_with_updated_at = ['tenant', 'property', 'owner_entity', 'deal']
    for table in tables_with_updated_at:
        op.execute(f'DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}')

    # Drop tables in reverse dependency order
    op.drop_table('evidence_event')
    op.drop_table('contact_suppression')
    op.drop_table('packet_event')
    op.drop_table('deal')
    op.drop_table('score_explainability')
    op.drop_table('scorecard')
    op.drop_table('field_provenance')
    op.drop_table('property_owner_link')
    op.drop_table('owner_entity')
    op.drop_table('property')
    op.drop_table('tenant')
