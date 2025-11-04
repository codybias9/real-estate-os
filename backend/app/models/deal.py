"""Deal and transaction models."""
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, ForeignKey,
    DateTime, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
import enum
from backend.app.core.database import Base
from .base import TimestampMixin, SoftDeleteMixin


class DealStageType(str, enum.Enum):
    """Deal pipeline stage enumeration."""
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CONTRACT = "contract"
    CLOSING = "closing"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class Deal(Base, TimestampMixin, SoftDeleteMixin):
    """Real estate deal/transaction model."""
    __tablename__ = 'deals'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='SET NULL'), nullable=True)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='SET NULL'), nullable=True)
    assigned_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Deal details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Current stage
    current_stage = Column(SQLEnum(DealStageType), default=DealStageType.LEAD, nullable=False, index=True)
    stage_entered_at = Column(DateTime(timezone=True), nullable=False)

    # Financial details
    deal_value = Column(Numeric(12, 2), nullable=True, index=True)
    commission_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    estimated_commission = Column(Numeric(12, 2), nullable=True)

    # Probabilities and forecasting
    probability = Column(Integer, default=0, nullable=False)  # 0-100%
    weighted_value = Column(Numeric(12, 2), nullable=True)  # deal_value * probability

    # Important dates
    expected_close_date = Column(DateTime(timezone=True), nullable=True, index=True)
    actual_close_date = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_won = Column(Boolean, nullable=True)  # None=active, True=won, False=lost
    lost_reason = Column(String(500), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, default=dict)

    # Relationships
    stage_history = relationship('DealStage', back_populates='deal', cascade='all, delete-orphan', order_by='DealStage.entered_at.desc()')
    transactions = relationship('Transaction', back_populates='deal', cascade='all, delete-orphan')


class DealStage(Base, TimestampMixin):
    """Deal pipeline stage history."""
    __tablename__ = 'deal_stages'

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey('deals.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    stage = Column(SQLEnum(DealStageType), nullable=False)
    entered_at = Column(DateTime(timezone=True), nullable=False, index=True)
    exited_at = Column(DateTime(timezone=True), nullable=True)
    duration_days = Column(Integer, nullable=True)

    # Stage details
    notes = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)

    # Relationships
    deal = relationship('Deal', back_populates='stage_history')


class Transaction(Base, TimestampMixin):
    """Financial transaction model."""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    deal_id = Column(Integer, ForeignKey('deals.id', ondelete='SET NULL'), nullable=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='SET NULL'), nullable=True)

    # Transaction details
    transaction_type = Column(String(50), nullable=False, index=True)  # purchase, sale, commission, fee
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Parties
    payer = Column(String(255), nullable=True)
    payee = Column(String(255), nullable=True)

    # Payment details
    payment_method = Column(String(50), nullable=True)  # wire, check, cash, etc.
    reference_number = Column(String(100), nullable=True)
    status = Column(String(50), default='pending', nullable=False, index=True)

    # Metadata
    description = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)

    # Relationships
    deal = relationship('Deal', back_populates='transactions')
