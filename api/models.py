"""
Pydantic models for API request/response validation.
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID


# ============================================================================
# Enums
# ============================================================================

class PropertyType(str, Enum):
    """Property types."""
    RESIDENTIAL = "residential"
    MULTIFAMILY = "multifamily"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    LAND = "land"
    MIXED_USE = "mixed_use"


class PropertyStatus(str, Enum):
    """Property status."""
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    ARCHIVED = "archived"


class ProspectStatus(str, Enum):
    """Prospect status."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    NEGOTIATING = "negotiating"
    WON = "won"
    LOST = "lost"


class OfferStatus(str, Enum):
    """Offer status."""
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ============================================================================
# Authentication Models
# ============================================================================

class LoginRequest(BaseModel):
    """Login request."""
    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    tenant_id: UUID
    user_id: UUID
    roles: List[str]


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request."""
    refresh_token: str


# ============================================================================
# Property Models
# ============================================================================

class PropertyBase(BaseModel):
    """Base property fields."""
    address: str = Field(..., min_length=5, max_length=500)
    property_type: PropertyType
    bedrooms: Optional[int] = Field(None, ge=0, le=100)
    bathrooms: Optional[float] = Field(None, ge=0, le=100)
    sqft: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    description: Optional[str] = Field(None, max_length=5000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PropertyCreate(PropertyBase):
    """Create property request."""
    pass


class PropertyUpdate(BaseModel):
    """Update property request (all fields optional)."""
    address: Optional[str] = Field(None, min_length=5, max_length=500)
    property_type: Optional[PropertyType] = None
    bedrooms: Optional[int] = Field(None, ge=0, le=100)
    bathrooms: Optional[float] = Field(None, ge=0, le=100)
    sqft: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    status: Optional[PropertyStatus] = None
    description: Optional[str] = Field(None, max_length=5000)
    metadata: Optional[Dict[str, Any]] = None


class PropertyResponse(PropertyBase):
    """Property response."""
    id: UUID
    tenant_id: UUID
    status: PropertyStatus
    address_normalized: Optional[str]
    hazards: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # For SQLAlchemy models


class PropertyListResponse(BaseModel):
    """Paginated property list response."""
    items: List[PropertyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Prospect Models
# ============================================================================

class ProspectBase(BaseModel):
    """Base prospect fields."""
    property_id: UUID
    source: str = Field(..., max_length=100)
    owner_name: Optional[str] = Field(None, max_length=255)
    owner_email: Optional[EmailStr] = None
    owner_phone: Optional[str] = Field(None, max_length=50)
    motivation_score: Optional[float] = Field(None, ge=0, le=1)
    notes: Optional[str] = Field(None, max_length=5000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProspectCreate(ProspectBase):
    """Create prospect request."""
    pass


class ProspectUpdate(BaseModel):
    """Update prospect request."""
    status: Optional[ProspectStatus] = None
    owner_name: Optional[str] = Field(None, max_length=255)
    owner_email: Optional[EmailStr] = None
    owner_phone: Optional[str] = Field(None, max_length=50)
    motivation_score: Optional[float] = Field(None, ge=0, le=1)
    notes: Optional[str] = Field(None, max_length=5000)
    metadata: Optional[Dict[str, Any]] = None


class ProspectResponse(ProspectBase):
    """Prospect response."""
    id: UUID
    tenant_id: UUID
    status: ProspectStatus
    enriched_at: Optional[datetime]
    last_contacted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProspectListResponse(BaseModel):
    """Paginated prospect list response."""
    items: List[ProspectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Offer Models
# ============================================================================

class OfferBase(BaseModel):
    """Base offer fields."""
    property_id: UUID
    prospect_id: Optional[UUID] = None
    offer_price: float = Field(..., ge=0)
    earnest_money: Optional[float] = Field(None, ge=0)
    closing_days: int = Field(..., ge=1, le=365)
    contingencies: Optional[List[str]] = Field(default_factory=list)
    terms: Optional[Dict[str, Any]] = Field(default_factory=dict)
    notes: Optional[str] = Field(None, max_length=5000)


class OfferCreate(OfferBase):
    """Create offer request."""
    pass


class OfferUpdate(BaseModel):
    """Update offer request."""
    status: Optional[OfferStatus] = None
    offer_price: Optional[float] = Field(None, ge=0)
    earnest_money: Optional[float] = Field(None, ge=0)
    closing_days: Optional[int] = Field(None, ge=1, le=365)
    contingencies: Optional[List[str]] = None
    terms: Optional[Dict[str, Any]] = None
    notes: Optional[str] = Field(None, max_length=5000)


class OfferResponse(OfferBase):
    """Offer response."""
    id: UUID
    tenant_id: UUID
    status: OfferStatus
    sent_at: Optional[datetime]
    responded_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OfferListResponse(BaseModel):
    """Paginated offer list response."""
    items: List[OfferResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# ML Valuation Models
# ============================================================================

class ValuationRequest(BaseModel):
    """Valuation request for ML models."""
    property_id: UUID
    model: str = Field("comp-critic", pattern="^(comp-critic|dcf|ensemble)$")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CompDetail(BaseModel):
    """Comparable property detail."""
    property_id: UUID
    address: str
    distance_miles: float
    similarity_score: float
    sale_price: float
    sale_date: datetime
    adjustments: Dict[str, float]
    adjusted_price: float


class ValuationResponse(BaseModel):
    """Valuation response."""
    property_id: UUID
    model: str
    estimated_value: float
    confidence_score: float
    value_range_low: float
    value_range_high: float
    comparables: Optional[List[CompDetail]] = None
    methodology: str
    generated_at: datetime
    metadata: Dict[str, Any]


# ============================================================================
# Analytics Models
# ============================================================================

class PortfolioSummary(BaseModel):
    """Portfolio summary statistics."""
    total_properties: int
    total_value: float
    total_equity: float
    average_cap_rate: Optional[float]
    occupancy_rate: Optional[float]
    properties_by_type: Dict[str, int]
    properties_by_status: Dict[str, int]
    recent_acquisitions: int  # Last 30 days


class MarketMetrics(BaseModel):
    """Market metrics for a geography."""
    market_name: str
    median_price: float
    price_change_pct_1y: float
    days_on_market: float
    inventory_level: str  # "high", "balanced", "low"
    demand_score: float
    updated_at: datetime


class PipelineMetrics(BaseModel):
    """Deal pipeline metrics."""
    total_prospects: int
    qualified_prospects: int
    active_negotiations: int
    offers_sent: int
    offers_accepted: int
    conversion_rate: float
    average_days_to_close: float
    pipeline_value: float


# ============================================================================
# Health Check Models
# ============================================================================

class ServiceHealth(BaseModel):
    """Individual service health status."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Overall health check response."""
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    environment: str
    timestamp: datetime
    services: List[ServiceHealth]


# ============================================================================
# Error Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail."""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    errors: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
