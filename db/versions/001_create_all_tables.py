"""Create all core tables for Real Estate OS

Revision ID: 001_create_all_tables
Revises: b81dde19348f
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_create_all_tables'
down_revision: Union[str, None] = 'b81dde19348f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""

    # Create properties table
    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('source_id', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('city', sa.String(length=255), nullable=False),
        sa.Column('state', sa.String(length=2), nullable=False),
        sa.Column('zip_code', sa.String(length=10), nullable=False),
        sa.Column('county', sa.String(length=255), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('property_type', sa.String(length=50), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('bedrooms', sa.Integer(), nullable=True),
        sa.Column('bathrooms', sa.Float(), nullable=True),
        sa.Column('sqft', sa.Integer(), nullable=True),
        sa.Column('lot_size', sa.Integer(), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('listing_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('features', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('images', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='new'),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for properties
    op.create_index('idx_property_location', 'properties', ['city', 'state', 'zip_code'])
    op.create_index('idx_property_type_status', 'properties', ['property_type', 'status'])
    op.create_index('idx_property_price_range', 'properties', ['price'])
    op.create_index(op.f('ix_properties_city'), 'properties', ['city'])
    op.create_index(op.f('ix_properties_county'), 'properties', ['county'])
    op.create_index(op.f('ix_properties_price'), 'properties', ['price'])
    op.create_index(op.f('ix_properties_property_type'), 'properties', ['property_type'])
    op.create_index(op.f('ix_properties_source'), 'properties', ['source'])
    op.create_index(op.f('ix_properties_source_id'), 'properties', ['source_id'], unique=True)
    op.create_index(op.f('ix_properties_state'), 'properties', ['state'])
    op.create_index(op.f('ix_properties_status'), 'properties', ['status'])
    op.create_index(op.f('ix_properties_zip_code'), 'properties', ['zip_code'])

    # Create property_enrichment table
    op.create_table(
        'property_enrichment',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('apn', sa.String(length=255), nullable=True),
        sa.Column('tax_assessment_value', sa.Integer(), nullable=True),
        sa.Column('tax_assessment_year', sa.Integer(), nullable=True),
        sa.Column('annual_tax_amount', sa.Integer(), nullable=True),
        sa.Column('owner_name', sa.String(length=500), nullable=True),
        sa.Column('owner_type', sa.String(length=100), nullable=True),
        sa.Column('last_sale_date', sa.Date(), nullable=True),
        sa.Column('last_sale_price', sa.Integer(), nullable=True),
        sa.Column('legal_description', sa.Text(), nullable=True),
        sa.Column('zoning', sa.String(length=100), nullable=True),
        sa.Column('land_use', sa.String(length=255), nullable=True),
        sa.Column('building_sqft', sa.Integer(), nullable=True),
        sa.Column('stories', sa.Integer(), nullable=True),
        sa.Column('units', sa.Integer(), nullable=True),
        sa.Column('parking_spaces', sa.Integer(), nullable=True),
        sa.Column('school_district', sa.String(length=255), nullable=True),
        sa.Column('elementary_school', sa.String(length=255), nullable=True),
        sa.Column('middle_school', sa.String(length=255), nullable=True),
        sa.Column('high_school', sa.String(length=255), nullable=True),
        sa.Column('school_rating', sa.Float(), nullable=True),
        sa.Column('walkability_score', sa.Integer(), nullable=True),
        sa.Column('transit_score', sa.Integer(), nullable=True),
        sa.Column('bike_score', sa.Integer(), nullable=True),
        sa.Column('crime_rate', sa.String(length=50), nullable=True),
        sa.Column('crime_index', sa.Integer(), nullable=True),
        sa.Column('median_home_value', sa.Integer(), nullable=True),
        sa.Column('appreciation_1yr', sa.Float(), nullable=True),
        sa.Column('appreciation_5yr', sa.Float(), nullable=True),
        sa.Column('median_rent', sa.Integer(), nullable=True),
        sa.Column('nearby_parks', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('nearby_shopping', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('nearby_restaurants', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('distance_to_downtown', sa.Float(), nullable=True),
        sa.Column('flood_zone', sa.String(length=50), nullable=True),
        sa.Column('earthquake_zone', sa.String(length=50), nullable=True),
        sa.Column('hoa_fees', sa.Integer(), nullable=True),
        sa.Column('enrichment_source', sa.String(length=255), nullable=True),
        sa.Column('enrichment_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_property_enrichment_property_id'), 'property_enrichment', ['property_id'], unique=True)

    # Create property_scores table
    op.create_table(
        'property_scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('total_score', sa.Integer(), nullable=False),
        sa.Column('score_breakdown', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('features', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('recommendation', sa.String(length=50), nullable=False),
        sa.Column('recommendation_reason', sa.Text(), nullable=False),
        sa.Column('risk_level', sa.String(length=50), nullable=False),
        sa.Column('risk_factors', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('scoring_method', sa.String(length=50), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('scoring_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_score_recommendation', 'property_scores', ['total_score', 'recommendation'])
    op.create_index('idx_score_risk', 'property_scores', ['risk_level', 'total_score'])
    op.create_index(op.f('ix_property_scores_property_id'), 'property_scores', ['property_id'], unique=True)
    op.create_index(op.f('ix_property_scores_recommendation'), 'property_scores', ['recommendation'])
    op.create_index(op.f('ix_property_scores_risk_level'), 'property_scores', ['risk_level'])
    op.create_index(op.f('ix_property_scores_total_score'), 'property_scores', ['total_score'])

    # Create generated_documents table
    op.create_table(
        'generated_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('file_url', sa.Text(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True, server_default='application/pdf'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('template_version', sa.String(length=50), nullable=True),
        sa.Column('generated_by', sa.String(length=255), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_document_type_status', 'generated_documents', ['document_type', 'status'])
    op.create_index(op.f('ix_generated_documents_document_type'), 'generated_documents', ['document_type'])
    op.create_index(op.f('ix_generated_documents_property_id'), 'generated_documents', ['property_id'])
    op.create_index(op.f('ix_generated_documents_status'), 'generated_documents', ['status'])

    # Create campaigns table
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('email_template', sa.Text(), nullable=False),
        sa.Column('property_ids', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('min_score', sa.Integer(), nullable=True),
        sa.Column('max_score', sa.Integer(), nullable=True),
        sa.Column('recipient_emails', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('scheduled_send_time', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('total_recipients', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('emails_sent', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('emails_delivered', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('emails_opened', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('emails_clicked', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('emails_replied', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('emails_bounced', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('emails_unsubscribed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_campaign_status', 'campaigns', ['status', 'scheduled_send_time'])
    op.create_index(op.f('ix_campaigns_status'), 'campaigns', ['status'])

    # Create outreach_logs table
    op.create_table(
        'outreach_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('recipient_email', sa.String(length=500), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('message_id', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('opened_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('clicked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('replied_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('open_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('click_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('bounce_reason', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_outreach_campaign_status', 'outreach_logs', ['campaign_id', 'status'])
    op.create_index('idx_outreach_recipient', 'outreach_logs', ['recipient_email', 'status'])
    op.create_index(op.f('ix_outreach_logs_campaign_id'), 'outreach_logs', ['campaign_id'])
    op.create_index(op.f('ix_outreach_logs_message_id'), 'outreach_logs', ['message_id'])
    op.create_index(op.f('ix_outreach_logs_property_id'), 'outreach_logs', ['property_id'])
    op.create_index(op.f('ix_outreach_logs_recipient_email'), 'outreach_logs', ['recipient_email'])
    op.create_index(op.f('ix_outreach_logs_status'), 'outreach_logs', ['status'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('outreach_logs')
    op.drop_table('campaigns')
    op.drop_table('generated_documents')
    op.drop_table('property_scores')
    op.drop_table('property_enrichment')
    op.drop_table('properties')
