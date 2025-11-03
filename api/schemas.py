"""
Pydantic schemas for request/response validation.

These schemas define the API contract and handle serialization/deserialization
of data between the API and clients.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class PipelineStageEnum(str, Enum):
    PROSPECT = "prospect"
    ENRICHMENT = "enrichment"
    SCORED = "scored"
    OUTREACH = "outreach"
    CONTACT_MADE = "contact_made"
    NEGOTIATION = "negotiation"
    PACKET_SENT = "packet_sent"
    OFFER = "offer"
    WON = "won"
    LOST = "lost"
    ARCHIVED = "archived"


class CommunicationTypeEnum(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    POSTCARD = "postcard"
    NOTE = "note"


class CommunicationDirectionEnum(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class TaskPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    VIEWER = "viewer"


# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRoleEnum = UserRoleEnum.AGENT
    phone: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    id: int
    settings: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PROPERTY SCHEMAS
# ============================================================================

class PropertyBase(BaseModel):
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[EmailStr] = None


class PropertyCreate(PropertyBase):
    prospect_queue_id: Optional[int] = None
    apn: Optional[str] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    assessed_value: Optional[Decimal] = None
    current_stage: str = "prospect"


class PropertyUpdate(BaseModel):
    current_stage: Optional[str] = None
    assigned_user_id: Optional[int] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class PropertyResponse(PropertyBase):
    id: int
    current_stage: str
    assigned_user_id: Optional[int] = None
    apn: Optional[str] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    assessed_value: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    asking_price: Optional[Decimal] = None
    bird_dog_score: Optional[float] = None
    probability_close: Optional[float] = None
    expected_value: Optional[Decimal] = None
    owner_propensity_score: Optional[float] = None
    propensity_factors: Dict[str, Any] = {}
    last_contact_date: Optional[datetime] = None
    last_reply_date: Optional[datetime] = None
    total_touches: int = 0
    reply_count: int = 0
    memo_url: Optional[str] = None
    packet_url: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PropertyListResponse(BaseModel):
    """Paginated property list response"""
    items: List[PropertyResponse]
    total: int
    page: int
    page_size: int
    pages: int


class StageUpdateRequest(BaseModel):
    """Request to update property stage"""
    to_stage: str
    reason: Optional[str] = None


# ============================================================================
# COMMUNICATION SCHEMAS
# ============================================================================

class CommunicationBase(BaseModel):
    property_id: int
    type: CommunicationTypeEnum
    direction: CommunicationDirectionEnum
    subject: Optional[str] = None
    body_text: Optional[str] = None


class CommunicationCreate(CommunicationBase):
    from_address: Optional[str] = None
    to_addresses: List[str] = []
    template_id: Optional[int] = None
    metadata: Dict[str, Any] = {}


class CommunicationResponse(CommunicationBase):
    id: int
    from_address: Optional[str] = None
    to_addresses: List[str] = []
    template_id: Optional[int] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    thread_id: Optional[str] = None
    message_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailThreadResponse(BaseModel):
    """Email thread with all messages"""
    thread_id: str
    subject: str
    property_id: int
    messages: List[CommunicationResponse]
    message_count: int


# ============================================================================
# TEMPLATE SCHEMAS
# ============================================================================

class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: CommunicationTypeEnum
    subject: Optional[str] = None
    body_text: str
    body_html: Optional[str] = None


class TemplateCreate(TemplateBase):
    allowed_stages: List[str] = []
    is_active: bool = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    allowed_stages: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TemplateResponse(TemplateBase):
    id: int
    allowed_stages: List[str] = []
    send_count: int = 0
    open_count: int = 0
    reply_count: int = 0
    meeting_count: int = 0
    is_champion: bool = False
    is_active: bool = True
    created_at: datetime

    # Calculated metrics
    open_rate: Optional[float] = None
    reply_rate: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class TemplatePerformanceResponse(BaseModel):
    """Template leaderboard item"""
    template_id: int
    name: str
    type: CommunicationTypeEnum
    send_count: int
    open_rate: float
    reply_rate: float
    meeting_rate: float
    is_champion: bool


# ============================================================================
# TASK SCHEMAS
# ============================================================================

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    property_id: Optional[int] = None
    assignee_id: Optional[int] = None


class TaskCreate(TaskBase):
    priority: TaskPriorityEnum = TaskPriorityEnum.MEDIUM
    due_date: Optional[datetime] = None
    sla_hours: Optional[int] = None
    metadata: Dict[str, Any] = {}


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    due_date: Optional[datetime] = None


class TaskResponse(TaskBase):
    id: int
    status: TaskStatusEnum
    priority: TaskPriorityEnum
    due_date: Optional[datetime] = None
    sla_hours: Optional[int] = None
    completed_at: Optional[datetime] = None
    source_type: Optional[str] = None
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SMART LIST SCHEMAS
# ============================================================================

class SmartListBase(BaseModel):
    name: str
    description: Optional[str] = None
    filters: Dict[str, Any]
    icon: Optional[str] = None
    color: Optional[str] = None


class SmartListCreate(SmartListBase):
    is_shared: bool = False


class SmartListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_shared: Optional[bool] = None


class SmartListResponse(SmartListBase):
    id: int
    is_shared: bool
    property_count: int = 0
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# NEXT BEST ACTION SCHEMAS
# ============================================================================

class NextBestActionBase(BaseModel):
    property_id: int
    action_type: str
    title: str
    description: Optional[str] = None
    reasoning: Optional[str] = None


class NextBestActionCreate(NextBestActionBase):
    priority_score: float = 0.5
    signals: Dict[str, Any] = {}


class NextBestActionResponse(NextBestActionBase):
    id: int
    priority_score: float
    signals: Dict[str, Any]
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NextBestActionExecuteRequest(BaseModel):
    """Request to execute a next best action"""
    action_id: int


# ============================================================================
# DEAL SCHEMAS
# ============================================================================

class DealBase(BaseModel):
    property_id: int
    title: str
    offer_price: Optional[Decimal] = None
    assignment_fee: Optional[Decimal] = None


class DealCreate(DealBase):
    investor_name: Optional[str] = None
    investor_email: Optional[EmailStr] = None
    expected_close_date: Optional[datetime] = None


class DealUpdate(BaseModel):
    title: Optional[str] = None
    offer_price: Optional[Decimal] = None
    assignment_fee: Optional[Decimal] = None
    estimated_margin: Optional[Decimal] = None
    probability_close: Optional[float] = None
    investor_name: Optional[str] = None
    investor_email: Optional[EmailStr] = None
    expected_close_date: Optional[datetime] = None
    notes: Optional[str] = None


class DealResponse(DealBase):
    id: int
    status: str
    estimated_margin: Optional[Decimal] = None
    expected_value: Optional[Decimal] = None
    probability_close: Optional[float] = None
    probability_factors: Dict[str, Any] = {}
    investor_name: Optional[str] = None
    investor_email: Optional[str] = None
    has_packet: bool = False
    packet_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DealEconomicsRequest(BaseModel):
    """Request to calculate/update deal economics"""
    offer_price: Decimal
    assignment_fee: Decimal
    days_to_close: Optional[int] = None


class DealEconomicsResponse(BaseModel):
    """Deal economics with what-if scenarios"""
    offer_price: Decimal
    assignment_fee: Decimal
    estimated_margin: Decimal
    probability_close: float
    expected_value: Decimal
    factors: Dict[str, Any]
    scenarios: List[Dict[str, Any]] = []


# ============================================================================
# DATA FLAG SCHEMAS
# ============================================================================

class DataFlagCreate(BaseModel):
    """Report a data quality issue"""
    property_id: int
    field_name: str
    issue_type: str  # incorrect, outdated, missing
    description: Optional[str] = None
    suggested_value: Optional[str] = None


class DataFlagResponse(BaseModel):
    id: int
    property_id: int
    field_name: str
    issue_type: str
    description: Optional[str] = None
    suggested_value: Optional[str] = None
    status: str
    reported_by_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# QUICK WIN SCHEMAS
# ============================================================================

class GenerateAndSendRequest(BaseModel):
    """Quick Win #1: Generate packet and send in one action"""
    property_id: int
    template_id: int
    to_email: EmailStr
    regenerate_memo: bool = False


class GenerateAndSendResponse(BaseModel):
    success: bool
    packet_url: Optional[str] = None
    communication_id: Optional[int] = None
    sent_at: Optional[datetime] = None
    message: str


# ============================================================================
# INVESTOR SHARE SCHEMAS
# ============================================================================

class InvestorShareCreate(BaseModel):
    """Create a secure share link for investors"""
    property_id: int
    investor_email: Optional[EmailStr] = None
    requires_email: bool = False
    password: Optional[str] = None
    expires_in_days: Optional[int] = 7
    watermark_text: Optional[str] = None
    allow_download: bool = True


class InvestorShareResponse(BaseModel):
    id: int
    property_id: int
    share_url: str
    share_token: str
    investor_email: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    view_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# FILTER & QUERY SCHEMAS
# ============================================================================

class PropertyFilters(BaseModel):
    """Query filters for property list"""
    current_stage: Optional[List[str]] = None
    assigned_user_id: Optional[int] = None
    bird_dog_score_gte: Optional[float] = None
    bird_dog_score_lte: Optional[float] = None
    has_memo: Optional[bool] = None
    has_reply: Optional[bool] = None
    last_contact_days_ago_gte: Optional[int] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = None  # Full-text search


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)
    sort_by: str = "created_at"
    sort_desc: bool = True


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class PipelineStatsResponse(BaseModel):
    """Pipeline overview statistics"""
    total_properties: int
    by_stage: Dict[str, int]
    avg_days_in_stage: Dict[str, float]
    conversion_rates: Dict[str, float]


class CommunicationStatsResponse(BaseModel):
    """Communication performance statistics"""
    total_sent: int
    delivery_rate: float
    open_rate: float
    reply_rate: float
    by_type: Dict[str, int]


class UserActivityResponse(BaseModel):
    """User activity dashboard"""
    user_id: int
    properties_assigned: int
    tasks_pending: int
    tasks_overdue: int
    communications_this_week: int
    reply_rate: float
