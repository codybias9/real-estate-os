"""Deal and Portfolio schemas."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
from decimal import Decimal


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


# Deal Schemas
class DealBase(BaseModel):
    """Base deal schema."""
    property_id: int
    lead_id: Optional[int] = None
    deal_type: DealType
    stage: DealStage = DealStage.LEAD
    value: Decimal = Field(..., ge=0)
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    probability: int = Field(50, ge=0, le=100)
    expected_close_date: Optional[date] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DealCreate(DealBase):
    """Deal creation schema."""
    pass


class DealUpdate(BaseModel):
    """Deal update schema."""
    lead_id: Optional[int] = None
    deal_type: Optional[DealType] = None
    stage: Optional[DealStage] = None
    value: Optional[Decimal] = Field(None, ge=0)
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    probability: Optional[int] = Field(None, ge=0, le=100)
    expected_close_date: Optional[date] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DealResponse(DealBase):
    """Deal response schema."""
    id: int
    organization_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DealListResponse(BaseModel):
    """Deal list response."""
    items: List[DealResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DealStats(BaseModel):
    """Deal statistics."""
    total_deals: int
    total_value: Decimal
    avg_deal_value: Decimal
    won_deals: int
    lost_deals: int
    win_rate: float
    by_stage: Dict[str, int]
    by_type: Dict[str, int]


# Transaction Schemas
class TransactionBase(BaseModel):
    """Base transaction schema."""
    deal_id: int
    transaction_type: TransactionType
    amount: Decimal
    description: Optional[str] = None
    transaction_date: date
    metadata: Optional[Dict[str, Any]] = None


class TransactionCreate(TransactionBase):
    """Transaction creation schema."""
    pass


class TransactionUpdate(BaseModel):
    """Transaction update schema."""
    transaction_type: Optional[TransactionType] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    transaction_date: Optional[date] = None
    metadata: Optional[Dict[str, Any]] = None


class TransactionResponse(TransactionBase):
    """Transaction response schema."""
    id: int
    organization_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Transaction list response."""
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Portfolio Schemas
class PortfolioBase(BaseModel):
    """Base portfolio schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PortfolioCreate(PortfolioBase):
    """Portfolio creation schema."""
    property_ids: Optional[List[int]] = []


class PortfolioUpdate(BaseModel):
    """Portfolio update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PortfolioResponse(PortfolioBase):
    """Portfolio response schema."""
    id: int
    organization_id: int
    created_by: int
    property_count: int = 0
    total_value: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioDetailResponse(PortfolioResponse):
    """Portfolio detail response with properties."""
    properties: List[Dict[str, Any]] = []


class PortfolioListResponse(BaseModel):
    """Portfolio list response."""
    items: List[PortfolioResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PortfolioStats(BaseModel):
    """Portfolio statistics."""
    total_portfolios: int
    total_properties: int
    total_value: Decimal
    avg_portfolio_value: Decimal
