"""Add email deliverability and compliance tables

Revision ID: 006_add_compliance_tables
Revises: 005_add_reconciliation_history
Create Date: 2025-01-15

Creates tables for email/communication compliance:

1. email_unsubscribes
   - CAN-SPAM compliance (10 day honor period)
   - GDPR compliance (immediate honor)
   - Permanent suppression

2. do_not_call
   - TCPA compliance (DNC requests)
   - Permanent suppression for calls/SMS

3. communication_consents
   - GDPR explicit consent tracking
   - TCPA prior express written consent
   - Full audit trail with IP, timestamp, consent text

Compliance Standards:
- CAN-SPAM Act (US)
- GDPR (EU)
- TCPA (US)
- CASL (Canada)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006_add_compliance_tables'
down_revision = '005_add_reconciliation_history'
branch_labels = None
depends_on = None


def upgrade():
    """Create compliance tables"""

    # Email unsubscribe list
    op.create_table(
        'email_unsubscribes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('unsubscribed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('reason', sa.Text()),
        sa.Column('source', sa.String(50), nullable=False, server_default='user_request'),

        sa.Index('idx_unsubscribe_email', 'email'),
    )

    # Do Not Call list
    op.create_table(
        'do_not_call',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('phone', sa.String(20), nullable=False, unique=True),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('reason', sa.Text()),
        sa.Column('source', sa.String(50), nullable=False, server_default='user_request'),

        sa.Index('idx_dnc_phone', 'phone'),
    )

    # Communication consent tracking
    op.create_table(
        'communication_consents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('consent_type', sa.String(50), nullable=False),
        sa.Column('consented', sa.Boolean(), nullable=False),
        sa.Column('consent_method', sa.String(50), nullable=False),
        sa.Column('consent_text', sa.Text()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('recorded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.Index('idx_consent_property', 'property_id'),
        sa.Index('idx_consent_type', 'consent_type'),
        sa.Index('idx_consent_recorded', 'recorded_at'),
    )


def downgrade():
    """Drop compliance tables"""
    op.drop_table('communication_consents')
    op.drop_table('do_not_call')
    op.drop_table('email_unsubscribes')
