"""Communications router for email threads, batch sends, and outreach management."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import random

router = APIRouter(prefix="/communications", tags=["communications"])


# ============================================================================
# Enums
# ============================================================================

class MessageDirection(str, Enum):
    """Direction of a message."""
    outbound = "outbound"
    inbound = "inbound"


class MessageStatus(str, Enum):
    """Status of an outbound message."""
    draft = "draft"
    queued = "queued"
    sent = "sent"
    delivered = "delivered"
    opened = "opened"
    clicked = "clicked"
    replied = "replied"
    bounced = "bounced"
    failed = "failed"


class ThreadStatus(str, Enum):
    """Status of an email thread."""
    active = "active"
    paused = "paused"
    closed = "closed"


# ============================================================================
# Schemas
# ============================================================================

class EmailThreadCreate(BaseModel):
    """Request to start a new email thread."""
    property_id: str = Field(..., description="Property this thread is related to")
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    template_id: Optional[str] = Field(
        None,
        description="Template to use for initial email"
    )
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    variables: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Variables for template substitution"
    )
    scheduled_send: Optional[str] = Field(
        None,
        description="ISO datetime to schedule send (null = send immediately)"
    )


class Message(BaseModel):
    """Individual message in a thread."""
    id: str
    thread_id: str
    direction: MessageDirection
    from_email: str
    from_name: Optional[str]
    to_email: str
    to_name: Optional[str]
    subject: str
    body: str
    status: MessageStatus
    sent_at: Optional[str]
    delivered_at: Optional[str]
    opened_at: Optional[str]
    clicked_at: Optional[str]
    replied_at: Optional[str]
    created_at: str


class EmailThread(BaseModel):
    """Email thread with a property owner."""
    id: str
    property_id: str
    recipient_email: str
    recipient_name: Optional[str]
    subject: str
    status: ThreadStatus
    message_count: int
    last_message_at: str
    last_message_direction: MessageDirection
    opened: bool
    replied: bool
    created_at: str
    created_by: str


class ThreadWithMessages(BaseModel):
    """Email thread with full message history."""
    thread: EmailThread
    messages: List[Message]


class SendTestEmailRequest(BaseModel):
    """Request to send a test email."""
    template_id: Optional[str] = Field(
        None,
        description="Template ID to test (optional)"
    )
    to_email: EmailStr
    subject: str
    body: str
    variables: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Variables for template substitution"
    )


class SendTestEmailResponse(BaseModel):
    """Response from sending a test email."""
    success: bool
    message: str
    preview_subject: str
    preview_body: str
    sent_at: Optional[str]


class BatchEmailRecipient(BaseModel):
    """Individual recipient for batch email."""
    property_id: str
    email: EmailStr
    name: Optional[str]
    variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom variables for this recipient"
    )


class BatchEmailRequest(BaseModel):
    """Request to send batch emails."""
    template_id: str
    recipients: List[BatchEmailRecipient] = Field(..., min_items=1)
    global_variables: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Variables applied to all recipients"
    )
    scheduled_send: Optional[str] = Field(
        None,
        description="ISO datetime to schedule batch send"
    )
    respect_cadence_rules: bool = Field(
        default=True,
        description="Whether to respect cadence/frequency rules"
    )


class BatchEmailResponse(BaseModel):
    """Response from batch email send."""
    batch_id: str
    total_recipients: int
    emails_queued: int
    emails_skipped: int
    skipped_reasons: Dict[str, int] = Field(
        description="Count of emails skipped by reason"
    )
    estimated_send_time: str
    status: str


class ReplyToThreadRequest(BaseModel):
    """Request to reply to an existing thread."""
    body: str = Field(..., min_length=1)
    template_id: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None


# ============================================================================
# Mock Data Store
# ============================================================================

EMAIL_THREADS: Dict[str, Dict] = {
    "thread_001": {
        "id": "thread_001",
        "property_id": "prop_001",
        "recipient_email": "john.smith@example.com",
        "recipient_name": "John Smith",
        "subject": "Interest in your property at 1234 Market St",
        "status": "active",
        "message_count": 3,
        "last_message_at": "2025-11-10T14:30:00",
        "last_message_direction": "inbound",
        "opened": True,
        "replied": True,
        "created_at": "2025-11-05T09:00:00",
        "created_by": "demo@realestateos.com"
    },
    "thread_002": {
        "id": "thread_002",
        "property_id": "prop_002",
        "recipient_email": "jane.doe@example.com",
        "recipient_name": "Jane Doe",
        "subject": "Following up: 5678 Mission St",
        "status": "active",
        "message_count": 2,
        "last_message_at": "2025-11-11T11:15:00",
        "last_message_direction": "outbound",
        "opened": True,
        "replied": False,
        "created_at": "2025-11-08T10:00:00",
        "created_by": "demo@realestateos.com"
    },
    "thread_003": {
        "id": "thread_003",
        "property_id": "prop_003",
        "recipient_email": "bob.johnson@example.com",
        "recipient_name": "Bob Johnson",
        "subject": "Interest in your property at 9012 Valencia St",
        "status": "closed",
        "message_count": 1,
        "last_message_at": "2025-10-20T16:00:00",
        "last_message_direction": "outbound",
        "opened": False,
        "replied": False,
        "created_at": "2025-10-20T16:00:00",
        "created_by": "demo@realestateos.com"
    }
}

MESSAGES: Dict[str, Dict] = {
    "msg_001": {
        "id": "msg_001",
        "thread_id": "thread_001",
        "direction": "outbound",
        "from_email": "demo@realestateos.com",
        "from_name": "Demo User",
        "to_email": "john.smith@example.com",
        "to_name": "John Smith",
        "subject": "Interest in your property at 1234 Market St",
        "body": "Hi John,\n\nMy name is Demo User and I'm interested in your property at 1234 Market St...",
        "status": "opened",
        "sent_at": "2025-11-05T09:00:00",
        "delivered_at": "2025-11-05T09:01:00",
        "opened_at": "2025-11-05T14:30:00",
        "clicked_at": None,
        "replied_at": "2025-11-06T10:00:00",
        "created_at": "2025-11-05T09:00:00"
    },
    "msg_002": {
        "id": "msg_002",
        "thread_id": "thread_001",
        "direction": "inbound",
        "from_email": "john.smith@example.com",
        "from_name": "John Smith",
        "to_email": "demo@realestateos.com",
        "to_name": "Demo User",
        "subject": "Re: Interest in your property at 1234 Market St",
        "body": "Hi,\n\nThanks for reaching out. I might be interested. Can you tell me more about your offer?",
        "status": "delivered",
        "sent_at": "2025-11-06T10:00:00",
        "delivered_at": "2025-11-06T10:00:00",
        "opened_at": None,
        "clicked_at": None,
        "replied_at": None,
        "created_at": "2025-11-06T10:00:00"
    },
    "msg_003": {
        "id": "msg_003",
        "thread_id": "thread_001",
        "direction": "outbound",
        "from_email": "demo@realestateos.com",
        "from_name": "Demo User",
        "to_email": "john.smith@example.com",
        "to_name": "John Smith",
        "subject": "Re: Interest in your property at 1234 Market St",
        "body": "Hi John,\n\nI'd be happy to discuss details. I'm offering $875,000 cash with a 30-day close...",
        "status": "replied",
        "sent_at": "2025-11-06T15:00:00",
        "delivered_at": "2025-11-06T15:01:00",
        "opened_at": "2025-11-06T16:30:00",
        "clicked_at": "2025-11-06T16:31:00",
        "replied_at": "2025-11-10T14:30:00",
        "created_at": "2025-11-06T15:00:00"
    }
}


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/email-thread", response_model=EmailThread, status_code=201)
def create_email_thread(thread_request: EmailThreadCreate):
    """
    Start a new email thread with a property owner.

    Creates a thread and sends the initial email. Can use a template
    or provide custom subject/body. Supports scheduled sends.
    """
    # Generate new IDs
    thread_id = f"thread_{str(len(EMAIL_THREADS) + 1).zfill(3)}"
    message_id = f"msg_{str(len(MESSAGES) + 1).zfill(3)}"

    # Determine send time
    if thread_request.scheduled_send:
        sent_at = None
        status = "queued"
    else:
        sent_at = datetime.now().isoformat()
        status = "sent"

    # Create message
    new_message = {
        "id": message_id,
        "thread_id": thread_id,
        "direction": "outbound",
        "from_email": "demo@realestateos.com",
        "from_name": "Demo User",
        "to_email": thread_request.recipient_email,
        "to_name": thread_request.recipient_name,
        "subject": thread_request.subject,
        "body": thread_request.body,
        "status": status,
        "sent_at": sent_at,
        "delivered_at": None,
        "opened_at": None,
        "clicked_at": None,
        "replied_at": None,
        "created_at": datetime.now().isoformat()
    }

    MESSAGES[message_id] = new_message

    # Create thread
    new_thread = {
        "id": thread_id,
        "property_id": thread_request.property_id,
        "recipient_email": thread_request.recipient_email,
        "recipient_name": thread_request.recipient_name,
        "subject": thread_request.subject,
        "status": "active",
        "message_count": 1,
        "last_message_at": datetime.now().isoformat(),
        "last_message_direction": "outbound",
        "opened": False,
        "replied": False,
        "created_at": datetime.now().isoformat(),
        "created_by": "demo@realestateos.com"
    }

    EMAIL_THREADS[thread_id] = new_thread

    return EmailThread(**new_thread)


@router.get("/threads", response_model=List[EmailThread])
def list_email_threads(
    property_id: Optional[str] = None,
    status: Optional[ThreadStatus] = None,
    replied: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List email threads with optional filters.

    Can filter by property, status, or whether recipient replied.
    """
    threads = list(EMAIL_THREADS.values())

    # Apply filters
    if property_id:
        threads = [t for t in threads if t["property_id"] == property_id]
    if status:
        threads = [t for t in threads if t["status"] == status.value]
    if replied is not None:
        threads = [t for t in threads if t["replied"] == replied]

    # Sort by last message (most recent first)
    threads.sort(key=lambda t: t["last_message_at"], reverse=True)

    # Pagination
    paginated = threads[offset:offset + limit]

    return [EmailThread(**t) for t in paginated]


@router.get("/threads/{thread_id}", response_model=ThreadWithMessages)
def get_email_thread(thread_id: str):
    """
    Get an email thread with full message history.

    Returns the thread metadata and all messages in chronological order.
    """
    if thread_id not in EMAIL_THREADS:
        raise HTTPException(status_code=404, detail="Email thread not found")

    thread = EMAIL_THREADS[thread_id]

    # Get all messages for this thread
    thread_messages = [
        Message(**msg)
        for msg in MESSAGES.values()
        if msg["thread_id"] == thread_id
    ]

    # Sort messages chronologically
    thread_messages.sort(key=lambda m: m.created_at)

    return ThreadWithMessages(
        thread=EmailThread(**thread),
        messages=thread_messages
    )


@router.post("/threads/{thread_id}/reply", response_model=Message, status_code=201)
def reply_to_thread(thread_id: str, reply: ReplyToThreadRequest):
    """
    Reply to an existing email thread.

    Sends a reply in the thread. Subject is automatically set to match thread.
    """
    if thread_id not in EMAIL_THREADS:
        raise HTTPException(status_code=404, detail="Email thread not found")

    thread = EMAIL_THREADS[thread_id]

    # Generate new message ID
    message_id = f"msg_{str(len(MESSAGES) + 1).zfill(3)}"

    # Create reply message
    new_message = {
        "id": message_id,
        "thread_id": thread_id,
        "direction": "outbound",
        "from_email": "demo@realestateos.com",
        "from_name": "Demo User",
        "to_email": thread["recipient_email"],
        "to_name": thread["recipient_name"],
        "subject": f"Re: {thread['subject']}",
        "body": reply.body,
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
        "delivered_at": (datetime.now() + timedelta(seconds=5)).isoformat(),
        "opened_at": None,
        "clicked_at": None,
        "replied_at": None,
        "created_at": datetime.now().isoformat()
    }

    MESSAGES[message_id] = new_message

    # Update thread
    thread["message_count"] += 1
    thread["last_message_at"] = new_message["sent_at"]
    thread["last_message_direction"] = "outbound"

    return Message(**new_message)


@router.patch("/threads/{thread_id}/status")
def update_thread_status(thread_id: str, status: ThreadStatus):
    """
    Update the status of an email thread.

    Can mark threads as active, paused, or closed.
    """
    if thread_id not in EMAIL_THREADS:
        raise HTTPException(status_code=404, detail="Email thread not found")

    EMAIL_THREADS[thread_id]["status"] = status.value

    return {"thread_id": thread_id, "status": status.value}


@router.post("/send-test", response_model=SendTestEmailResponse)
def send_test_email(test_request: SendTestEmailRequest):
    """
    Send a test email to verify template and formatting.

    Does not create a thread or count toward quotas.
    Useful for testing templates before batch sends.
    """
    # In a real system, would actually send email via provider
    # For demo, we just return a success response with preview

    return SendTestEmailResponse(
        success=True,
        message=f"Test email sent successfully to {test_request.to_email}",
        preview_subject=test_request.subject,
        preview_body=test_request.body,
        sent_at=datetime.now().isoformat()
    )


@router.post("/send-batch", response_model=BatchEmailResponse, status_code=201)
def send_batch_emails(batch_request: BatchEmailRequest):
    """
    Send batch emails to multiple recipients.

    Sends the same template to multiple recipients with personalized variables.
    Can respect cadence rules to avoid over-contacting.
    Supports scheduled batch sends.
    """
    total_recipients = len(batch_request.recipients)

    # Mock some skipped emails for demo
    emails_skipped = random.randint(0, max(1, total_recipients // 10))
    emails_queued = total_recipients - emails_skipped

    # Mock skip reasons
    skip_reasons = {}
    if emails_skipped > 0:
        skip_reasons = {
            "dnc_list": random.randint(0, emails_skipped // 2),
            "recent_contact": random.randint(0, emails_skipped // 3),
            "bounced_previously": emails_skipped - (random.randint(0, emails_skipped // 2) + random.randint(0, emails_skipped // 3))
        }

    # Generate batch ID
    batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

    # Estimate send time
    if batch_request.scheduled_send:
        estimated_send = batch_request.scheduled_send
    else:
        # Mock: 1 email per second
        estimated_send = (datetime.now() + timedelta(seconds=emails_queued)).isoformat()

    return BatchEmailResponse(
        batch_id=batch_id,
        total_recipients=total_recipients,
        emails_queued=emails_queued,
        emails_skipped=emails_skipped,
        skipped_reasons=skip_reasons,
        estimated_send_time=estimated_send,
        status="queued" if batch_request.scheduled_send else "processing"
    )


@router.get("/batches/{batch_id}")
def get_batch_status(batch_id: str):
    """
    Get status of a batch email send.

    Returns progress, delivery stats, and any errors.
    """
    # Mock batch status
    total = random.randint(50, 200)
    sent = random.randint(int(total * 0.8), total)
    delivered = random.randint(int(sent * 0.9), sent)
    opened = random.randint(int(delivered * 0.3), int(delivered * 0.5))
    clicked = random.randint(int(opened * 0.1), int(opened * 0.3))

    return {
        "batch_id": batch_id,
        "status": "completed",
        "total_recipients": total,
        "emails_sent": sent,
        "emails_delivered": delivered,
        "emails_opened": opened,
        "emails_clicked": clicked,
        "emails_bounced": total - sent,
        "emails_failed": 0,
        "open_rate": round(opened / delivered, 3) if delivered > 0 else 0,
        "click_rate": round(clicked / delivered, 3) if delivered > 0 else 0,
        "started_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        "completed_at": (datetime.now() - timedelta(minutes=30)).isoformat()
    }


@router.get("/threads/{thread_id}/messages", response_model=List[Message])
def get_thread_messages(thread_id: str):
    """
    Get all messages in a thread.

    Returns messages in chronological order.
    """
    if thread_id not in EMAIL_THREADS:
        raise HTTPException(status_code=404, detail="Email thread not found")

    # Get all messages for this thread
    thread_messages = [
        Message(**msg)
        for msg in MESSAGES.values()
        if msg["thread_id"] == thread_id
    ]

    # Sort chronologically
    thread_messages.sort(key=lambda m: m.created_at)

    return thread_messages


@router.get("/stats/overview")
def get_communications_stats():
    """
    Get overall communications statistics.

    Returns metrics about email performance, engagement, and activity.
    """
    total_threads = len(EMAIL_THREADS)
    total_messages = len(MESSAGES)

    return {
        "total_threads": total_threads,
        "active_threads": sum(1 for t in EMAIL_THREADS.values() if t["status"] == "active"),
        "total_messages_sent": total_messages,
        "messages_sent_24h": random.randint(10, 50),
        "messages_sent_7d": random.randint(50, 200),
        "average_open_rate": round(random.uniform(0.35, 0.55), 3),
        "average_reply_rate": round(random.uniform(0.12, 0.25), 3),
        "average_click_rate": round(random.uniform(0.08, 0.18), 3),
        "threads_with_replies": sum(1 for t in EMAIL_THREADS.values() if t["replied"]),
        "threads_opened": sum(1 for t in EMAIL_THREADS.values() if t["opened"])
    }
