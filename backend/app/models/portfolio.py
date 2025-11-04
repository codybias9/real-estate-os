"""Portfolio and reconciliation models."""
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, ForeignKey,
    DateTime, JSON, Index
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from .base import TimestampMixin, SoftDeleteMixin


class Portfolio(Base, TimestampMixin, SoftDeleteMixin):
    """Investment portfolio model."""
    __tablename__ = 'portfolios'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    owner_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Portfolio details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    portfolio_type = Column(String(50), nullable=False)  # rental, flip, development, mixed

    # Valuation
    total_invested = Column(Numeric(14, 2), default=0, nullable=False)
    total_value = Column(Numeric(14, 2), default=0, nullable=False)
    unrealized_gain_loss = Column(Numeric(14, 2), default=0, nullable=False)

    # Performance metrics
    total_return_pct = Column(Numeric(8, 4), nullable=True)  # Percentage
    annual_return_pct = Column(Numeric(8, 4), nullable=True)
    total_cash_flow = Column(Numeric(14, 2), default=0, nullable=False)

    # Reconciliation
    last_reconciled_at = Column(DateTime(timezone=True), nullable=True)
    reconciliation_status = Column(String(50), default='pending', nullable=False)  # pending, passed, failed

    # Metadata
    strategy = Column(Text, nullable=True)
    risk_tolerance = Column(String(20), nullable=True)  # low, medium, high
    settings = Column(JSON, default=dict)

    # Relationships
    holdings = relationship('PortfolioHolding', back_populates='portfolio', cascade='all, delete-orphan')
    reconciliations = relationship('Reconciliation', back_populates='portfolio', cascade='all, delete-orphan', order_by='Reconciliation.reconciled_at.desc()')


class PortfolioHolding(Base, TimestampMixin, SoftDeleteMixin):
    """Individual holding within a portfolio."""
    __tablename__ = 'portfolio_holdings'

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='SET NULL'), nullable=True)

    # Acquisition
    acquired_at = Column(DateTime(timezone=True), nullable=False)
    acquisition_price = Column(Numeric(12, 2), nullable=False)
    acquisition_costs = Column(Numeric(12, 2), default=0, nullable=False)
    total_invested = Column(Numeric(12, 2), nullable=False)

    # Current valuation
    current_value = Column(Numeric(12, 2), nullable=False)
    last_valuation_date = Column(DateTime(timezone=True), nullable=True)
    valuation_method = Column(String(50), nullable=True)

    # Performance
    unrealized_gain_loss = Column(Numeric(12, 2), nullable=False)
    gain_loss_pct = Column(Numeric(8, 4), nullable=True)

    # Cash flows
    total_income = Column(Numeric(12, 2), default=0, nullable=False)  # Rent, etc.
    total_expenses = Column(Numeric(12, 2), default=0, nullable=False)
    net_cash_flow = Column(Numeric(12, 2), default=0, nullable=False)

    # Disposition
    disposed_at = Column(DateTime(timezone=True), nullable=True)
    disposition_price = Column(Numeric(12, 2), nullable=True)
    realized_gain_loss = Column(Numeric(12, 2), nullable=True)

    # Status
    status = Column(String(50), default='active', nullable=False, index=True)  # active, sold, foreclosed

    # Metadata
    notes = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)

    # Relationships
    portfolio = relationship('Portfolio', back_populates='holdings')


class Reconciliation(Base, TimestampMixin):
    """Portfolio reconciliation record (±0.5% validation)."""
    __tablename__ = 'reconciliations'

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False)
    reconciled_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Reconciliation details
    reconciled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # passed, failed, warning

    # Values being reconciled
    calculated_value = Column(Numeric(14, 2), nullable=False)
    reported_value = Column(Numeric(14, 2), nullable=False)
    variance_amount = Column(Numeric(14, 2), nullable=False)
    variance_pct = Column(Numeric(8, 4), nullable=False)

    # Tolerance check (±0.5% = 0.005)
    tolerance_threshold = Column(Numeric(8, 4), default=0.005, nullable=False)
    within_tolerance = Column(Boolean, nullable=False)

    # Breakdown
    holdings_count = Column(Integer, nullable=False)
    holdings_breakdown = Column(JSON, default=list)  # Per-holding reconciliation details

    # Issues and resolution
    issues_found = Column(JSON, default=list)
    resolution_notes = Column(Text, nullable=True)

    # Relationships
    portfolio = relationship('Portfolio', back_populates='reconciliations')
