"""Deal and Portfolio models."""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Numeric, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import BaseModel, SoftDeleteMixin
import enum


class DealStatus(str, enum.Enum):
    """Deal status enum."""
    PROSPECTING = "prospecting"
    ANALYSIS = "analysis"
    OFFER_MADE = "offer_made"
    UNDER_CONTRACT = "under_contract"
    DUE_DILIGENCE = "due_diligence"
    FINANCING = "financing"
    CLOSING = "closing"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class TransactionType(str, enum.Enum):
    """Transaction type enum."""
    PURCHASE = "purchase"
    SALE = "sale"
    REFINANCE = "refinance"
    LEASE = "lease"
    ASSIGNMENT = "assignment"


class Deal(BaseModel, SoftDeleteMixin):
    """Deal/transaction model."""

    __tablename__ = "deals"

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True, index=True)

    # Basic Info
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(DealStatus), nullable=False, default=DealStatus.PROSPECTING, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False, index=True)

    # Financial
    purchase_price = Column(Numeric(12, 2), nullable=True)
    offer_price = Column(Numeric(12, 2), nullable=True)
    sale_price = Column(Numeric(12, 2), nullable=True)
    estimated_value = Column(Numeric(12, 2), nullable=True)
    financing_amount = Column(Numeric(12, 2), nullable=True)
    down_payment = Column(Numeric(12, 2), nullable=True)
    closing_costs = Column(Numeric(12, 2), nullable=True)
    estimated_profit = Column(Numeric(12, 2), nullable=True)
    actual_profit = Column(Numeric(12, 2), nullable=True)

    # Dates
    target_close_date = Column(DateTime(timezone=True), nullable=True)
    contract_date = Column(DateTime(timezone=True), nullable=True)
    inspection_date = Column(DateTime(timezone=True), nullable=True)
    appraisal_date = Column(DateTime(timezone=True), nullable=True)
    closing_date = Column(DateTime(timezone=True), nullable=True)

    # Parties involved
    buyer_name = Column(String(255), nullable=True)
    seller_name = Column(String(255), nullable=True)
    agent_name = Column(String(255), nullable=True)
    attorney_name = Column(String(255), nullable=True)
    lender_name = Column(String(255), nullable=True)

    # Custom fields
    custom_fields = Column(JSON, nullable=True, default=dict)
    tags = Column(JSON, nullable=True, default=list)

    # Relationships
    organization = relationship("Organization", back_populates="deals")
    property = relationship("Property")
    lead = relationship("Lead")
    assigned_to = relationship("User")
    portfolio = relationship("Portfolio", back_populates="deals")
    transactions = relationship("Transaction", back_populates="deal", cascade="all, delete-orphan")


class Transaction(BaseModel):
    """Financial transaction for a deal."""

    __tablename__ = "transactions"

    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type = Column(String(100), nullable=False, index=True)  # expense, revenue, deposit, etc.
    category = Column(String(100), nullable=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    description = Column(Text, nullable=True)
    payee = Column(String(255), nullable=True)
    reference_number = Column(String(100), nullable=True)
    metadata = Column(JSON, nullable=True)

    # Relationships
    deal = relationship("Deal", back_populates="transactions")


class Portfolio(BaseModel, SoftDeleteMixin):
    """Portfolio for grouping properties/deals."""

    __tablename__ = "portfolios"

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Metrics (can be calculated)
    total_properties = Column(Integer, default=0, nullable=False)
    total_value = Column(Numeric(15, 2), nullable=True)
    total_equity = Column(Numeric(15, 2), nullable=True)
    total_debt = Column(Numeric(15, 2), nullable=True)
    total_cash_flow = Column(Numeric(12, 2), nullable=True)

    # Custom fields
    custom_fields = Column(JSON, nullable=True, default=dict)

    # Relationships
    organization = relationship("Organization")
    created_by = relationship("User")
    deals = relationship("Deal", back_populates="portfolio")
