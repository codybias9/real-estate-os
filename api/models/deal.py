"""Deal and portfolio models."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Numeric, Enum as SQLEnum, Date, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from ..database import Base


class DealType(str, Enum):
    """Deal type enum."""
    BUY = "buy"
    SELL = "sell"
    LEASE = "lease"
    WHOLESALE = "wholesale"
    FLIP = "flip"
    RENTAL = "rental"


class DealStage(str, Enum):
    """Deal stage enum."""
    LEAD = "lead"
    QUALIFIED = "qualified"
    CONTRACT = "contract"
    INSPECTION = "inspection"
    FINANCING = "financing"
    CLOSING = "closing"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class TransactionType(str, Enum):
    """Transaction type enum."""
    PURCHASE = "purchase"
    SALE = "sale"
    LEASE = "lease"
    COMMISSION = "commission"
    EXPENSE = "expense"
    INCOME = "income"


# Association table for Portfolio and Property many-to-many relationship
portfolio_properties = Table(
    "portfolio_properties",
    Base.metadata,
    Column("portfolio_id", Integer, ForeignKey("portfolios.id"), primary_key=True),
    Column("property_id", Integer, ForeignKey("properties.id"), primary_key=True),
    Column("added_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


class Deal(Base):
    """Deal model for tracking real estate transactions."""

    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Deal Details
    deal_type = Column(SQLEnum(DealType), nullable=False, index=True)
    stage = Column(SQLEnum(DealStage), default=DealStage.LEAD, nullable=False, index=True)
    value = Column(Numeric(12, 2), nullable=False)
    commission_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    probability = Column(Integer, default=50, nullable=False)  # 0-100
    expected_close_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON object

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="deals")
    property = relationship("Property", back_populates="deals")
    lead = relationship("Lead", back_populates="deals")
    transactions = relationship("Transaction", back_populates="deal", cascade="all, delete-orphan")


class Transaction(Base):
    """Transaction model for financial records."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)

    # Transaction Details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=True)
    transaction_date = Column(Date, nullable=False, index=True)
    metadata = Column(Text, nullable=True)  # JSON object

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    deal = relationship("Deal", back_populates="transactions")


class Portfolio(Base):
    """Portfolio model for grouping properties."""

    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Portfolio Details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON object

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="portfolios")
    properties = relationship("Property", secondary=portfolio_properties, back_populates="portfolios")
