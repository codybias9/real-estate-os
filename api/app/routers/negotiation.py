"""Negotiation Brain Router
Intelligent outreach with NLP, send-time optimization, and bandits
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

from ..database import get_db
from ..auth.hybrid_dependencies import get_current_user
from ..auth.models import User
import sys
sys.path.append('/home/user/real-estate-os')
from ml.negotiation.reply_classifier import ReplyClassifier, ReplyIntent
from ml.negotiation.contact_policy import ContactPolicyEngine, ContactChannel, ContactOutcome, create_default_policy
from ml.negotiation.bandits import SendTimeOptimizer, TemplateSelector, SequenceSelector, ContextFeatures

router = APIRouter(
    prefix="/negotiation",
    tags=["negotiation"]
)


# ============================================================================
# Models
# ============================================================================

class ChannelEnum(str, Enum):
    """Contact channels"""
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"
    DIRECT_MAIL = "direct_mail"


class IntentEnum(str, Enum):
    """Reply intents"""
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    COUNTER_OFFER = "counter_offer"
    REQUEST_INFO = "request_info"
    CALLBACK_LATER = "callback_later"
    AUTO_REPLY = "auto_reply"
    IRRELEVANT = "irrelevant"
    UNKNOWN = "unknown"


class ClassifyReplyRequest(BaseModel):
    """Request to classify a reply"""
    message: str
    lead_id: str
    property_id: str


class ClassifyReplyResponse(BaseModel):
    """Reply classification result"""
    intent: IntentEnum
    confidence: float
    matched_patterns: List[str]
    sentiment: str
    urgency: str
    next_action: str


class CheckContactRequest(BaseModel):
    """Request to check if contact is allowed"""
    lead_id: str
    channel: ChannelEnum
    timezone: str = "America/New_York"


class CheckContactResponse(BaseModel):
    """Contact check result"""
    allowed: bool
    outcome: str
    reason: Optional[str] = None
    next_allowed_time: Optional[str] = None


class SelectSendTimeResponse(BaseModel):
    """Send time selection result"""
    selected_hour: int
    best_hours: List[dict]


class SelectTemplateRequest(BaseModel):
    """Request to select message template"""
    template_ids: List[str]


class SelectTemplateResponse(BaseModel):
    """Template selection result"""
    selected_template_id: str
    template_performance: List[dict]


class SelectSequenceRequest(BaseModel):
    """Request to select message sequence"""
    lead_id: str
    property_id: str

    # Context
    lead_responded_before: bool = False
    lead_interest_score: float = 0.0
    days_since_last_contact: int = 999
    property_type: str = "unknown"
    price_range: str = "medium"
    market_regime: str = "warm"


class SelectSequenceResponse(BaseModel):
    """Sequence selection result"""
    selected_sequence: str
    sequence_performance: dict


class RecordOutcomeRequest(BaseModel):
    """Request to record outreach outcome"""
    lead_id: str
    property_id: str
    channel: ChannelEnum
    replied: bool
    send_hour: Optional[int] = None
    template_id: Optional[str] = None
    sequence_id: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/classify-reply", response_model=ClassifyReplyResponse)
async def classify_reply(
    request: ClassifyReplyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Classify seller reply using NLP

    Args:
        request: Reply text and context
        user: Current authenticated user
        db: Database session

    Returns:
        Classification result with intent, sentiment, urgency
    """

    classifier = ReplyClassifier()

    # TODO: Load conversation context from database
    context = {
        "lead_id": request.lead_id,
        "property_id": request.property_id
    }

    result = classifier.classify(request.message, context)

    return ClassifyReplyResponse(
        intent=IntentEnum(result.intent.value),
        confidence=result.confidence,
        matched_patterns=result.matched_patterns,
        sentiment=result.sentiment,
        urgency=result.urgency,
        next_action=result.next_action
    )


@router.post("/check-contact", response_model=CheckContactResponse)
async def check_contact(
    request: CheckContactRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if contact is allowed under policy rules

    Args:
        request: Contact check request
        user: Current authenticated user
        db: Database session

    Returns:
        Contact check result
    """

    # Create policy engine with default policy
    policy = create_default_policy()
    engine = ContactPolicyEngine(policy)

    # TODO: Load lead contact history from database

    # Check if contact is allowed
    channel = ContactChannel(request.channel.value)
    outcome, reason = engine.can_contact(
        lead_id=request.lead_id,
        channel=channel,
        user_id=str(user.user_id),
        lead_timezone=request.timezone
    )

    allowed = (outcome == ContactOutcome.ALLOWED)

    # Get next allowed time if blocked
    next_allowed_time = None
    if not allowed:
        next_time = engine.get_next_allowed_contact_time(
            lead_id=request.lead_id,
            channel=channel,
            user_id=str(user.user_id),
            timezone=request.timezone
        )
        if next_time:
            next_allowed_time = next_time.isoformat()

    return CheckContactResponse(
        allowed=allowed,
        outcome=outcome.value,
        reason=reason,
        next_allowed_time=next_allowed_time
    )


@router.get("/select-send-time", response_model=SelectSendTimeResponse)
async def select_send_time(
    user: User = Depends(get_current_user)
):
    """Select optimal send time using Thompson Sampling

    Args:
        user: Current authenticated user

    Returns:
        Selected hour and top performing hours
    """

    # TODO: Load optimizer state from database per tenant
    optimizer = SendTimeOptimizer()

    # Select send time
    selected_hour = optimizer.select_send_time()

    # Get best hours
    best_hours_list = optimizer.get_best_hours(top_n=3)
    best_hours = [
        {"hour": hour, "expected_reply_rate": rate}
        for hour, rate in best_hours_list
    ]

    return SelectSendTimeResponse(
        selected_hour=selected_hour,
        best_hours=best_hours
    )


@router.post("/select-template", response_model=SelectTemplateResponse)
async def select_template(
    request: SelectTemplateRequest,
    user: User = Depends(get_current_user)
):
    """Select message template using Thompson Sampling

    Args:
        request: Template selection request
        user: Current authenticated user

    Returns:
        Selected template and performance stats
    """

    # TODO: Load selector state from database per tenant
    selector = TemplateSelector(request.template_ids)

    # Select template
    selected_template_id = selector.select_template()

    # Get performance stats
    template_performance = selector.get_template_performance()

    return SelectTemplateResponse(
        selected_template_id=selected_template_id,
        template_performance=template_performance
    )


@router.post("/select-sequence", response_model=SelectSequenceResponse)
async def select_sequence(
    request: SelectSequenceRequest,
    user: User = Depends(get_current_user)
):
    """Select message sequence using contextual bandit

    Args:
        request: Sequence selection request with context
        user: Current authenticated user

    Returns:
        Selected sequence and expected performance
    """

    # Build context features
    context = ContextFeatures(
        lead_responded_before=request.lead_responded_before,
        lead_interest_score=request.lead_interest_score,
        days_since_last_contact=request.days_since_last_contact,
        property_type=request.property_type,
        price_range=request.price_range,
        market_regime=request.market_regime,
        day_of_week=datetime.now().weekday(),
        is_weekend=datetime.now().weekday() >= 5
    )

    # TODO: Load selector state from database per tenant
    selector = SequenceSelector()

    # Select sequence
    selected_sequence = selector.select_sequence(context)

    # Get performance for all sequences
    sequence_performance = selector.get_sequence_performance(context)

    return SelectSequenceResponse(
        selected_sequence=selected_sequence,
        sequence_performance=sequence_performance
    )


@router.post("/record-outcome")
async def record_outcome(
    request: RecordOutcomeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record outcome of outreach attempt

    This updates all bandit models with observed results

    Args:
        request: Outcome record request
        user: Current authenticated user
        db: Database session

    Returns:
        Success confirmation
    """

    # TODO: Load optimizer/selector states from database

    # Update send-time optimizer
    if request.send_hour is not None:
        optimizer = SendTimeOptimizer()
        optimizer.record_outcome(request.send_hour, request.replied)

    # Update template selector
    if request.template_id is not None:
        # TODO: Get template IDs from database
        selector = TemplateSelector([request.template_id])
        selector.record_outcome(request.template_id, request.replied)

    # Update sequence selector
    if request.sequence_id is not None:
        # TODO: Load context from database
        context = ContextFeatures()
        selector = SequenceSelector()
        selector.record_outcome(request.sequence_id, context, request.replied)

    # Update contact policy engine
    policy = create_default_policy()
    engine = ContactPolicyEngine(policy)
    channel = ContactChannel(request.channel.value)
    outcome = ContactOutcome.ALLOWED if request.replied else ContactOutcome.ALLOWED

    engine.record_contact_attempt(
        lead_id=request.lead_id,
        channel=channel,
        user_id=str(user.user_id),
        outcome=outcome
    )

    # TODO: Store updated states to database

    return {
        "success": True,
        "lead_id": request.lead_id,
        "replied": request.replied
    }


@router.post("/opt-out/{lead_id}")
async def opt_out_lead(
    lead_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Opt out a lead from all future contact

    Args:
        lead_id: Lead identifier
        user: Current authenticated user
        db: Database session

    Returns:
        Confirmation
    """

    # Update policy engine
    policy = create_default_policy()
    engine = ContactPolicyEngine(policy)
    engine.mark_opt_out(lead_id)

    # TODO: Update database with opt-out status

    return {
        "success": True,
        "lead_id": lead_id,
        "opted_out": True,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/performance/send-times")
async def get_send_time_performance(
    user: User = Depends(get_current_user)
):
    """Get send time performance analysis

    Args:
        user: Current authenticated user

    Returns:
        Hourly performance stats
    """

    # TODO: Load optimizer state from database
    optimizer = SendTimeOptimizer()

    performance = optimizer.get_hourly_performance()

    return {
        "hourly_performance": performance,
        "best_hours": optimizer.get_best_hours(top_n=5)
    }


@router.get("/performance/templates")
async def get_template_performance(
    template_ids: List[str],
    user: User = Depends(get_current_user)
):
    """Get template performance analysis

    Args:
        template_ids: Template IDs to analyze
        user: Current authenticated user

    Returns:
        Template performance stats
    """

    # TODO: Load selector state from database
    selector = TemplateSelector(template_ids)

    performance = selector.get_template_performance()

    return {
        "template_performance": performance
    }
