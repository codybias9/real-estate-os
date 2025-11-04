"""
Pydantic schemas for API request/response validation
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, UUID4
from enum import Enum

# ============================================================================
# ENUMS
# ============================================================================

class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    VIEWER = "viewer"

class PropertyStageEnum(str, Enum):
    NEW = "new"
    OUTREACH = "outreach"
    QUALIFIED = "qualified"
    NEGOTIATION = "negotiation"
    UNDER_CONTRACT = "under_contract"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
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
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class TaskPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class DealStatusEnum(str, Enum):
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    CLOSED = "closed"
    DEAD = "dead"

class ShareLinkStatusEnum(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"

class InvestorReadinessLevelEnum(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"

# ============================================================================
# BASE SCHEMAS
# ============================================================================

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        populate_by_name = True

# ============================================================================
# AUTHENTICATION & USER SCHEMAS
# ============================================================================

class LoginRequest(BaseSchema):
    email: EmailStr
    password: str = Field(..., min_length=8)

class RegisterRequest(BaseSchema):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    team_name: Optional[str] = None
    team_id: Optional[int] = None
    role: Optional[UserRoleEnum] = None

class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseSchema):
    id: int
    email: EmailStr
    full_name: str
    role: UserRoleEnum
    team_id: int
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime

class AuthResponse(TokenResponse):
    user: UserResponse

class UpdateUserRequest(BaseSchema):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str = Field(..., min_length=8)

class RequestPasswordResetRequest(BaseSchema):
    email: EmailStr

# ============================================================================
# PROPERTY SCHEMAS
# ============================================================================

class PropertyBase(BaseSchema):
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    apn: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    owner_name: Optional[str] = None
    owner_mailing_address: Optional[str] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    lot_size: Optional[float] = None
    year_built: Optional[int] = None
    property_type: Optional[str] = None
    land_use: Optional[str] = None
    assessed_value: Optional[float] = None
    market_value_estimate: Optional[float] = None
    arv: Optional[float] = None
    repair_estimate: Optional[float] = None
    tags: Optional[List[str]] = []
    custom_fields: Optional[Dict[str, Any]] = {}

class PropertyCreate(PropertyBase):
    team_id: int
    assigned_user_id: Optional[int] = None

class PropertyUpdate(BaseSchema):
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    assigned_user_id: Optional[int] = None
    current_stage: Optional[PropertyStageEnum] = None
    bird_dog_score: Optional[float] = None
    propensity_to_sell: Optional[float] = None
    memo_url: Optional[str] = None
    packet_url: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None

class PropertyResponse(PropertyBase):
    id: int
    uuid: UUID4
    team_id: int
    assigned_user_id: Optional[int] = None
    current_stage: PropertyStageEnum
    previous_stage: Optional[PropertyStageEnum] = None
    stage_changed_at: Optional[datetime] = None
    last_contact_date: Optional[datetime] = None
    last_reply_date: Optional[datetime] = None
    touch_count: int = 0
    email_opens: int = 0
    email_clicks: int = 0
    reply_count: int = 0
    bird_dog_score: Optional[float] = None
    score_reasons: List[Dict[str, Any]] = []
    propensity_to_sell: Optional[float] = None
    propensity_signals: List[Dict[str, Any]] = []
    expected_value: Optional[float] = None
    probability_of_close: Optional[float] = None
    memo_url: Optional[str] = None
    memo_generated_at: Optional[datetime] = None
    packet_url: Optional[str] = None
    data_quality_score: float = 1.0
    is_on_dnc: bool = False
    has_opted_out: bool = False
    cadence_paused: bool = False
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

class PropertyStageChange(BaseSchema):
    new_stage: PropertyStageEnum

class PropertyFilters(BaseSchema):
    stage: Optional[PropertyStageEnum] = None
    assigned_user_id: Optional[int] = None
    bird_dog_score__gte: Optional[float] = None
    bird_dog_score__lte: Optional[float] = None
    has_memo: Optional[bool] = None
    has_reply: Optional[bool] = None
    last_contact_days_ago_gte: Optional[int] = None
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    skip: int = 0
    limit: int = 100

# ============================================================================
# COMMUNICATION SCHEMAS
# ============================================================================

class CommunicationBase(BaseSchema):
    property_id: int
    type: CommunicationTypeEnum
    direction: CommunicationDirectionEnum
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = {}

class CommunicationCreate(CommunicationBase):
    user_id: Optional[int] = None
    template_id: Optional[int] = None

class CommunicationResponse(CommunicationBase):
    id: int
    uuid: UUID4
    user_id: Optional[int] = None
    thread_id: Optional[int] = None
    template_id: Optional[int] = None
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    call_transcript: Optional[str] = None
    call_sentiment: Optional[str] = None
    call_key_points: List[Dict[str, Any]] = []
    created_at: datetime

class EmailThreadRequest(BaseSchema):
    property_id: int
    email_message_id: str
    subject: str
    from_address: str
    to_address: str
    body: str
    sent_at: datetime

class CallCaptureRequest(BaseSchema):
    property_id: int
    from_phone: str
    to_phone: str
    duration_seconds: int
    recording_url: Optional[str] = None
    transcript: Optional[str] = None

class ReplyDraftRequest(BaseSchema):
    property_id: int
    context: Optional[str] = None
    objection_type: Optional[str] = None  # "price_too_low", "timing", "tenant_in_place"

class ReplyDraftResponse(BaseSchema):
    draft: str
    suggested_subject: Optional[str] = None
    confidence: float

# ============================================================================
# TEMPLATE SCHEMAS
# ============================================================================

class TemplateBase(BaseSchema):
    name: str
    type: CommunicationTypeEnum
    applicable_stages: List[PropertyStageEnum] = []
    subject_template: Optional[str] = None
    body_template: str

class TemplateCreate(TemplateBase):
    team_id: int

class TemplateUpdate(BaseSchema):
    name: Optional[str] = None
    applicable_stages: Optional[List[PropertyStageEnum]] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    is_active: Optional[bool] = None

class TemplateResponse(TemplateBase):
    id: int
    uuid: UUID4
    team_id: int
    times_used: int = 0
    open_rate: Optional[float] = None
    reply_rate: Optional[float] = None
    meeting_rate: Optional[float] = None
    is_champion: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

class TemplatePerformance(BaseSchema):
    template_id: int
    template_name: str
    times_used: int
    open_rate: float
    reply_rate: float
    meeting_rate: float
    rank: int

# ============================================================================
# TASK SCHEMAS
# ============================================================================

class TaskBase(BaseSchema):
    title: str
    description: Optional[str] = None
    priority: TaskPriorityEnum = TaskPriorityEnum.MEDIUM
    sla_hours: Optional[int] = None

class TaskCreate(TaskBase):
    property_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    due_at: Optional[datetime] = None

class TaskUpdate(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    due_at: Optional[datetime] = None

class TaskResponse(TaskBase):
    id: int
    uuid: UUID4
    property_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    status: TaskStatusEnum
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    source_event_type: Optional[str] = None
    extra_metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

class CreateTaskFromEventRequest(BaseSchema):
    property_id: int
    communication_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    sla_hours: int = 24
    priority: TaskPriorityEnum = TaskPriorityEnum.HIGH

# ============================================================================
# NEXT BEST ACTION SCHEMAS
# ============================================================================

class NextBestActionBase(BaseSchema):
    property_id: int
    action_type: str
    action_title: str
    action_description: Optional[str] = None
    priority: float
    rule_name: Optional[str] = None
    reasoning: Optional[str] = None
    action_params: Dict[str, Any] = {}

class NextBestActionCreate(NextBestActionBase):
    pass

class NextBestActionResponse(NextBestActionBase):
    id: int
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

class GenerateNBARequest(BaseSchema):
    property_ids: Optional[List[int]] = None
    team_id: Optional[int] = None

# ============================================================================
# SMART LIST SCHEMAS
# ============================================================================

class SmartListBase(BaseSchema):
    name: str
    description: Optional[str] = None
    filters: Dict[str, Any]
    is_dynamic: bool = True

class SmartListCreate(SmartListBase):
    team_id: int

class SmartListUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class SmartListResponse(SmartListBase):
    id: int
    uuid: UUID4
    team_id: int
    created_by_user_id: Optional[int] = None
    cached_count: Optional[int] = None
    last_refreshed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# ============================================================================
# DEAL SCHEMAS
# ============================================================================

class DealBase(BaseSchema):
    property_id: int
    offer_price: Optional[float] = None
    arv: Optional[float] = None
    repair_cost: Optional[float] = None
    assignment_fee: Optional[float] = None
    expected_margin: Optional[float] = None
    probability_of_close: Optional[float] = None
    investor_id: Optional[int] = None
    notes: Optional[str] = None

class DealCreate(DealBase):
    pass

class DealUpdate(BaseSchema):
    status: Optional[DealStatusEnum] = None
    offer_price: Optional[float] = None
    arv: Optional[float] = None
    repair_cost: Optional[float] = None
    assignment_fee: Optional[float] = None
    probability_of_close: Optional[float] = None
    notes: Optional[str] = None

class DealResponse(DealBase):
    id: int
    uuid: UUID4
    status: DealStatusEnum
    expected_value: Optional[float] = None
    ev_drivers: List[Dict[str, Any]] = []
    proposed_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    dead_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class DealScenarioCreate(BaseSchema):
    deal_id: int
    name: str
    offer_price: Optional[float] = None
    arv: Optional[float] = None
    repair_cost: Optional[float] = None
    days_to_close: Optional[int] = None

class DealScenarioResponse(BaseSchema):
    id: int
    deal_id: int
    name: str
    offer_price: Optional[float] = None
    arv: Optional[float] = None
    repair_cost: Optional[float] = None
    days_to_close: Optional[int] = None
    expected_margin: Optional[float] = None
    probability_of_close: Optional[float] = None
    expected_value: Optional[float] = None
    impact_summary: Optional[str] = None
    created_at: datetime

# ============================================================================
# SHARE LINK SCHEMAS
# ============================================================================

class ShareLinkBase(BaseSchema):
    property_id: Optional[int] = None
    deal_room_id: Optional[int] = None
    password_hash: Optional[str] = None
    watermark_text: Optional[str] = None
    expires_at: Optional[datetime] = None
    max_views: Optional[int] = None
    viewer_name: Optional[str] = None
    viewer_email: Optional[EmailStr] = None

class ShareLinkCreate(ShareLinkBase):
    created_by_user_id: int

class ShareLinkResponse(ShareLinkBase):
    id: int
    uuid: UUID4
    short_code: str
    status: ShareLinkStatusEnum
    view_count: int = 0
    created_at: datetime
    last_viewed_at: Optional[datetime] = None

# ============================================================================
# DEAL ROOM SCHEMAS
# ============================================================================

class DealRoomBase(BaseSchema):
    property_id: int
    name: str
    description: Optional[str] = None

class DealRoomCreate(DealRoomBase):
    pass

class DealRoomUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    readiness_level: Optional[InvestorReadinessLevelEnum] = None

class DealRoomResponse(DealRoomBase):
    id: int
    uuid: UUID4
    readiness_level: InvestorReadinessLevelEnum
    readiness_factors: Dict[str, bool] = {}
    created_at: datetime
    updated_at: datetime

class DealRoomArtifactCreate(BaseSchema):
    deal_room_id: int
    name: str
    type: str
    file_url: str
    file_size: Optional[int] = None

class DealRoomArtifactResponse(BaseSchema):
    id: int
    deal_room_id: int
    name: str
    type: str
    file_url: str
    file_size: Optional[int] = None
    uploaded_by_user_id: Optional[int] = None
    uploaded_at: datetime

# ============================================================================
# INVESTOR SCHEMAS
# ============================================================================

class InvestorBase(BaseSchema):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    preferred_property_types: List[str] = []
    min_arv: Optional[float] = None
    max_arv: Optional[float] = None
    preferred_locations: List[str] = []
    notes: Optional[str] = None

class InvestorCreate(InvestorBase):
    team_id: int

class InvestorUpdate(BaseSchema):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    preferred_property_types: Optional[List[str]] = None
    min_arv: Optional[float] = None
    max_arv: Optional[float] = None
    notes: Optional[str] = None

class InvestorResponse(InvestorBase):
    id: int
    uuid: UUID4
    team_id: int
    deals_closed: int = 0
    avg_response_time_hours: Optional[float] = None
    created_at: datetime

class SuggestedInvestorResponse(BaseSchema):
    investor: InvestorResponse
    match_score: float
    match_reasons: List[str]

# ============================================================================
# COMPLIANCE & OPERATIONS SCHEMAS
# ============================================================================

class ComplianceCheckCreate(BaseSchema):
    property_id: int
    check_type: str
    status: str
    details: Optional[str] = None

class ComplianceCheckResponse(BaseSchema):
    id: int
    property_id: int
    check_type: str
    status: str
    details: Optional[str] = None
    checked_at: datetime

class CadenceRuleCreate(BaseSchema):
    team_id: int
    name: str
    trigger_on: str
    action_type: str
    action_params: Dict[str, Any] = {}

class CadenceRuleResponse(BaseSchema):
    id: int
    team_id: int
    name: str
    trigger_on: str
    action_type: str
    action_params: Dict[str, Any]
    is_active: bool
    created_at: datetime

class DeliverabilityMetricsResponse(BaseSchema):
    id: int
    team_id: int
    date: datetime
    emails_sent: int
    emails_delivered: int
    emails_bounced: int
    emails_opened: int
    emails_clicked: int
    bounce_rate: Optional[float] = None
    open_rate: Optional[float] = None
    click_rate: Optional[float] = None
    domain_warmup_status: Optional[str] = None
    suppression_list_size: Optional[int] = None

class BudgetTrackingResponse(BaseSchema):
    id: int
    team_id: int
    provider: str
    date: datetime
    requests_made: int
    cost: float
    monthly_cap: Optional[float] = None
    remaining_budget: Optional[float] = None
    projected_end_of_month_cost: Optional[float] = None

class DataFlagCreate(BaseSchema):
    property_id: int
    field_name: str
    issue_type: str
    description: Optional[str] = None

class DataFlagResponse(BaseSchema):
    id: int
    property_id: int
    reported_by_user_id: Optional[int] = None
    field_name: str
    issue_type: str
    description: Optional[str] = None
    status: str
    resolved_by_user_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

# ============================================================================
# PROPENSITY SCHEMAS
# ============================================================================

class PropensitySignalResponse(BaseSchema):
    id: int
    property_id: int
    signal_type: str
    signal_value: Optional[str] = None
    weight: Optional[float] = None
    reasoning: Optional[str] = None
    detected_at: datetime

class PropensityAnalysisRequest(BaseSchema):
    property_id: int

class PropensityAnalysisResponse(BaseSchema):
    property_id: int
    propensity_to_sell: float
    signals: List[PropensitySignalResponse]
    explanation: str

class ExplainableProbabilityResponse(BaseSchema):
    property_id: int
    probability_of_close: float
    score_factors: List[Dict[str, Any]]
    propensity_signals: List[Dict[str, Any]]
    explanation: str
    confidence: float

# ============================================================================
# ONBOARDING SCHEMAS
# ============================================================================

class UserOnboardingResponse(BaseSchema):
    id: int
    user_id: int
    steps_completed: List[str]
    is_complete: bool
    completed_at: Optional[datetime] = None
    persona_preset: Optional[str] = None
    created_at: datetime

class PresetTemplateResponse(BaseSchema):
    id: int
    persona: str
    name: str
    description: Optional[str] = None
    default_filters: Dict[str, Any]
    default_templates: List[Dict[str, Any]]
    dashboard_tiles: List[Dict[str, Any]]

class ApplyPresetRequest(BaseSchema):
    user_id: int
    persona: str

# ============================================================================
# OPEN DATA SCHEMAS
# ============================================================================

class OpenDataSourceResponse(BaseSchema):
    id: int
    name: str
    source_type: str
    data_types: List[str]
    coverage_areas: List[str]
    api_endpoint: Optional[str] = None
    license_type: Optional[str] = None
    cost_per_request: float
    data_quality_rating: Optional[float] = None
    freshness_days: Optional[int] = None
    is_active: bool

class EnrichPropertyRequest(BaseSchema):
    sources: Optional[List[str]] = None  # If None, use all active sources

class ProvenanceInspectorResponse(BaseSchema):
    property_id: int
    field_name: str
    current_value: Any
    source_name: str
    source_tier: str
    license_type: Optional[str] = None
    cost: float
    confidence: Optional[float] = None
    fetched_at: datetime
    expires_at: Optional[datetime] = None

# ============================================================================
# QUICK WIN SCHEMAS
# ============================================================================

class GenerateAndSendRequest(BaseSchema):
    property_id: int
    template_id: Optional[int] = None

class GenerateAndSendResponse(BaseSchema):
    property_id: int
    memo_url: str
    communication_id: int
    sent_at: datetime

class AutoAssignOnReplyRequest(BaseSchema):
    communication_id: int

class AutoAssignOnReplyResponse(BaseSchema):
    property_id: int
    assigned_user_id: int
    task_id: int
    task_title: str

# ============================================================================
# AUTOMATION & COMPLIANCE SCHEMAS
# ============================================================================

class ToggleCadenceRuleRequest(BaseSchema):
    is_active: bool

class ApplyCadenceRulesRequest(BaseSchema):
    event_type: str  # "reply_detected", "email_bounced", etc.

class RecordConsentRequest(BaseSchema):
    property_id: int
    consent_type: str  # "email", "sms", "call"
    granted: bool  # Changed from 'consented' to 'granted' to match test
    source: str  # Changed from 'consent_method' to 'source' to match test
    consent_text: Optional[str] = None
    ip_address: Optional[str] = None

class AddToDNCRequest(BaseSchema):
    phone_number: str
    reason: Optional[str] = None

class UnsubscribeRequest(BaseSchema):
    email: str
    reason: Optional[str] = None

class ValidateSendRequest(BaseSchema):
    property_id: int
    channel: str  # Changed from 'communication_type' to 'channel' to match test
    recipient: str  # Changed from 'to_address' to 'recipient' to match test

class ValidateDNSRequest(BaseSchema):
    domain: str
    dkim_selector: str = "default"

# ============================================================================
# ONBOARDING SCHEMAS (Additional)
# ============================================================================

class ApplyPresetRequest(BaseSchema):
    user_id: int
    persona: str  # "wholesaler", "fix_and_flip", etc.
    preset_name: str
    team_id: int

class CompleteChecklistStepRequest(BaseSchema):
    step: str  # Changed from 'step_name' to 'step' to match query param

# ============================================================================
# UTILITY SCHEMAS
# ============================================================================

class TimelineEvent(BaseSchema):
    id: int
    property_id: int
    event_type: str
    event_title: str
    event_description: Optional[str] = None
    extra_metadata: Dict[str, Any] = {}
    created_at: datetime

class PipelineStats(BaseSchema):
    stage: PropertyStageEnum
    count: int
    total_value: float
    avg_score: Optional[float] = None

class HealthResponse(BaseSchema):
    status: str
    features: Dict[str, bool]

class PaginatedResponse(BaseSchema):
    items: List[Any]
    total: int
    skip: int
    limit: int
