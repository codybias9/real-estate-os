"""
Communication Router
Email threading, Call capture, Reply drafting - bring communication into the pipeline
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from api.database import get_db
from api import schemas
from db.models import (
    Property, Communication, CommunicationType, CommunicationDirection,
    CommunicationThread, PropertyTimeline, Template
)

router = APIRouter(prefix="/communications", tags=["Communications"])

# ============================================================================
# EMAIL THREADING
# ============================================================================

@router.post("/email-thread", response_model=schemas.CommunicationResponse, status_code=201)
def create_email_thread(
    email_data: schemas.EmailThreadRequest,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Auto-ingest emails and thread them by property

    Gmail/Outlook Integration:
    - Captures email_message_id for threading
    - Groups related conversations
    - Shows in property Timeline
    - Auto-detects inbound vs outbound

    KPI: Eliminates manual log entries
    """
    # Get property
    property = db.query(Property).filter(Property.id == email_data.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Find or create thread based on subject
    thread = (
        db.query(CommunicationThread)
        .filter(
            CommunicationThread.property_id == email_data.property_id,
            CommunicationThread.subject == email_data.subject
        )
        .first()
    )

    if not thread:
        thread = CommunicationThread(
            property_id=email_data.property_id,
            subject=email_data.subject,
            first_communication_at=email_data.sent_at,
            message_count=0
        )
        db.add(thread)
        db.flush()

    # Determine direction based on from_address
    # In production, check against team email domains
    direction = (
        CommunicationDirection.OUTBOUND
        if "real-estate-os.com" in email_data.from_address.lower()
        else CommunicationDirection.INBOUND
    )

    # Create communication
    communication = Communication(
        property_id=email_data.property_id,
        user_id=user_id,
        thread_id=thread.id,
        type=CommunicationType.EMAIL,
        direction=direction,
        from_address=email_data.from_address,
        to_address=email_data.to_address,
        subject=email_data.subject,
        body=email_data.body,
        email_message_id=email_data.email_message_id,
        email_thread_position=thread.message_count + 1,
        sent_at=email_data.sent_at
    )

    db.add(communication)
    db.flush()

    # Update thread
    thread.message_count += 1
    thread.last_communication_at = email_data.sent_at

    # Update property tracking
    if direction == CommunicationDirection.INBOUND:
        property.last_reply_date = email_data.sent_at
        property.reply_count = (property.reply_count or 0) + 1

        # Auto-pause cadence on reply
        if not property.cadence_paused:
            property.cadence_paused = True
            property.cadence_pause_reason = "reply_detected"

    else:  # OUTBOUND
        property.last_contact_date = email_data.sent_at
        property.touch_count = (property.touch_count or 0) + 1

    property.updated_at = datetime.utcnow()

    # Create timeline event
    event_type = "email_received" if direction == CommunicationDirection.INBOUND else "email_sent"
    timeline_event = PropertyTimeline(
        property_id=property.id,
        event_type=event_type,
        event_title=f"Email: {email_data.subject}",
        event_description=f"{direction.value.title()} email in thread",
        communication_id=communication.id,
        user_id=user_id
    )
    db.add(timeline_event)

    db.commit()
    db.refresh(communication)

    return communication

@router.get("/threads/{property_id}", response_model=List[dict])
def get_property_threads(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all email threads for a property

    Returns threads with message counts
    """
    threads = (
        db.query(CommunicationThread)
        .filter(CommunicationThread.property_id == property_id)
        .order_by(desc(CommunicationThread.last_communication_at))
        .all()
    )

    return [
        {
            "id": thread.id,
            "subject": thread.subject,
            "message_count": thread.message_count,
            "first_communication_at": thread.first_communication_at,
            "last_communication_at": thread.last_communication_at
        }
        for thread in threads
    ]

@router.get("/threads/{thread_id}/messages", response_model=List[schemas.CommunicationResponse])
def get_thread_messages(
    thread_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all messages in a thread, in chronological order
    """
    messages = (
        db.query(Communication)
        .filter(Communication.thread_id == thread_id)
        .order_by(Communication.sent_at)
        .all()
    )

    return messages

# ============================================================================
# CALL CAPTURE + TRANSCRIPTION
# ============================================================================

@router.post("/call-capture", response_model=schemas.CommunicationResponse, status_code=201)
def capture_call(
    call_data: schemas.CallCaptureRequest,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Capture phone call with optional transcription

    Twilio Integration:
    - Logs call duration
    - Stores recording URL
    - Auto-transcribes with basic sentiment analysis
    - Extracts key points (in production, use AI)

    Features:
    - Click-to-call from property card
    - Auto-logging
    - Sentiment tracking
    - Key point extraction

    KPI: Contact attempts per lead increases; Better notes quality
    """
    # Get property
    property = db.query(Property).filter(Property.id == call_data.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Determine direction
    direction = (
        CommunicationDirection.OUTBOUND
        if "real-estate-os.com" in call_data.from_phone  # In production, check team numbers
        else CommunicationDirection.INBOUND
    )

    # Extract key points from transcript (simplified - in production use NLP)
    key_points = []
    sentiment = None

    if call_data.transcript:
        # Simple keyword extraction (in production, use AI/NLP)
        transcript_lower = call_data.transcript.lower()

        if any(word in transcript_lower for word in ["interested", "yes", "sounds good"]):
            sentiment = "positive"
            key_points.append({"type": "interest", "text": "Expressed interest"})

        if any(word in transcript_lower for word in ["not interested", "no thanks", "remove"]):
            sentiment = "negative"
            key_points.append({"type": "objection", "text": "Not interested"})

        if any(word in transcript_lower for word in ["maybe", "think about", "call back"]):
            sentiment = "neutral"
            key_points.append({"type": "consideration", "text": "Needs time to consider"})

        # Extract price mentions
        if "$" in call_data.transcript or "price" in transcript_lower:
            key_points.append({"type": "price_discussion", "text": "Discussed pricing"})

    # Create communication
    communication = Communication(
        property_id=call_data.property_id,
        user_id=user_id,
        type=CommunicationType.CALL,
        direction=direction,
        from_address=call_data.from_phone,
        to_address=call_data.to_phone,
        duration_seconds=call_data.duration_seconds,
        call_recording_url=call_data.recording_url,
        call_transcript=call_data.transcript,
        call_sentiment=sentiment,
        call_key_points=key_points,
        sent_at=datetime.utcnow()
    )

    db.add(communication)
    db.flush()

    # Update property tracking
    if direction == CommunicationDirection.INBOUND:
        property.last_reply_date = datetime.utcnow()
        property.reply_count = (property.reply_count or 0) + 1
    else:
        property.last_contact_date = datetime.utcnow()
        property.touch_count = (property.touch_count or 0) + 1

    property.updated_at = datetime.utcnow()

    # Create timeline event
    event_title = f"📞 Call ({call_data.duration_seconds}s)"
    if sentiment:
        event_title += f" - {sentiment.title()}"

    timeline_event = PropertyTimeline(
        property_id=property.id,
        event_type="call_logged",
        event_title=event_title,
        event_description=f"{direction.value.title()} call - {call_data.duration_seconds}s",
        communication_id=communication.id,
        user_id=user_id,
        extra_metadata={
            "duration_seconds": call_data.duration_seconds,
            "sentiment": sentiment,
            "key_points_count": len(key_points)
        }
    )
    db.add(timeline_event)

    db.commit()
    db.refresh(communication)

    return communication

# ============================================================================
# REPLY DRAFTING & OBJECTION HANDLING
# ============================================================================

@router.post("/draft-reply", response_model=schemas.ReplyDraftResponse)
def draft_reply(
    request: schemas.ReplyDraftRequest,
    db: Session = Depends(get_db)
):
    """
    Draft a reply from context with objection handling

    Uses property context:
    - Bird dog score reasons
    - Memo summary
    - Communication history

    Objection templates:
    - "price_too_low": Address undervaluation concerns
    - "timing": Flexible closing options
    - "tenant_in_place": Tenant buyout strategies
    - "needs_repairs": ARV-based pricing

    KPI: Time to send reply; Reply→meeting conversion
    """
    # Get property
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Build context
    context_parts = []

    if property.bird_dog_score:
        context_parts.append(f"Property score: {property.bird_dog_score:.2f}")

    if property.score_reasons:
        reasons = ", ".join([r.get("reason", "") for r in property.score_reasons[:3]])
        context_parts.append(f"Key factors: {reasons}")

    # Objection handling templates
    # Format property values safely
    assessed_value_str = f"${property.assessed_value:,.0f}" if property.assessed_value else "N/A"
    arv_str = f"${property.arv:,.0f}" if property.arv else "Competitive"
    repair_estimate_str = f"${property.repair_estimate:,.0f}" if property.repair_estimate else "Minimal"

    objection_responses = {
        "price_too_low": f"""
I understand your concern about the offer price. Let me explain our valuation:

- Current assessed value: {assessed_value_str}
- Our estimated ARV: {arv_str}
- Estimated repairs needed: {repair_estimate_str}

We base our offers on post-repair value and market comps in your area. I'd be happy to share the detailed comp analysis with you.

Would you be open to reviewing the numbers together?
""",
        "timing": f"""
I completely understand timing is important. We're flexible and can work around your schedule:

- Quick close (7-14 days) if you need to move fast
- Extended close (30-60 days) if you need time to relocate
- Rent-back option available if you need to stay temporarily

What timeline works best for you?
""",
        "tenant_in_place": f"""
Having a tenant in place isn't a problem for us - we actually purchase occupied properties regularly.

Options we can discuss:
- We can work with your current tenant
- Tenant buyout assistance if needed
- Close before lease end with agreed terms

This doesn't need to complicate the sale. What's your current lease situation?
""",
        "needs_repairs": f"""
We specifically look for properties that need work - that's our business model.

You don't need to do any repairs. We'll:
- Purchase as-is
- Handle all repairs ourselves
- Take care of any code violations

The condition is already factored into our offer. What specific repairs were you concerned about?
"""
    }

    # Generate reply
    if request.objection_type and request.objection_type in objection_responses:
        draft = objection_responses[request.objection_type]
        confidence = 0.9
    else:
        # Generic follow-up
        draft = f"""
Thank you for your interest in {property.address}.

{" ".join(context_parts)}

I'd love to discuss this opportunity further. Are you available for a brief call this week?

Best regards
"""
        confidence = 0.7

    suggested_subject = f"Re: {property.address}"
    if request.objection_type:
        suggested_subject += f" - {request.objection_type.replace('_', ' ').title()}"

    return {
        "draft": draft.strip(),
        "suggested_subject": suggested_subject,
        "confidence": confidence
    }

# ============================================================================
# COMMUNICATIONS LIST
# ============================================================================

@router.get("", response_model=List[schemas.CommunicationResponse])
def list_communications(
    property_id: Optional[int] = Query(None),
    type: Optional[schemas.CommunicationTypeEnum] = Query(None),
    direction: Optional[schemas.CommunicationDirectionEnum] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List communications with filters
    """
    query = db.query(Communication)

    if property_id:
        query = query.filter(Communication.property_id == property_id)

    if type:
        query = query.filter(Communication.type == type.value)

    if direction:
        query = query.filter(Communication.direction == direction.value)

    communications = (
        query
        .order_by(desc(Communication.sent_at))
        .limit(limit)
        .all()
    )

    return communications
