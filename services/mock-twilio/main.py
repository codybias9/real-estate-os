"""
Mock Twilio Service

Simulates Twilio SMS API for development without credentials.
Stores messages in memory and writes to volume for inspection.

Endpoints:
- POST /Messages.json - Send SMS (Twilio-compatible)
- GET /Messages.json - List sent messages
- POST /webhooks/sms - Simulate inbound SMS webhook

Features:
- Twilio-compatible API responses
- Message storage with in-memory and file persistence
- Webhook simulation for testing inbound flows
- Message status transitions (queued → sent → delivered)
"""
import os
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from fastapi import FastAPI, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# ============================================================================
# CONFIGURATION
# ============================================================================

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/tmp/mock-twilio"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

WEBHOOK_URL = os.getenv("API_WEBHOOK_URL", "http://api:8000/api/v1/webhooks/twilio/sms")

# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Mock Twilio Service",
    description="Twilio-compatible mock SMS service for development",
    version="1.0.0"
)

# In-memory message storage
messages_store: List[Dict] = []

# ============================================================================
# MODELS
# ============================================================================

class MessageResponse(BaseModel):
    """Twilio-compatible message response"""
    sid: str
    account_sid: str
    from_: str
    to: str
    body: str
    status: str
    direction: str
    date_created: str
    date_updated: str
    date_sent: Optional[str] = None
    price: Optional[str] = None
    price_unit: Optional[str] = "USD"
    error_code: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        fields = {"from_": "from"}


class MessageListResponse(BaseModel):
    """Twilio-compatible message list response"""
    messages: List[MessageResponse]
    page: int = 0
    page_size: int = 50
    uri: str = "/Messages.json"


class InboundSmsRequest(BaseModel):
    """Simulate inbound SMS for webhook testing"""
    From: str
    To: str
    Body: str
    MessageSid: Optional[str] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_sid() -> str:
    """Generate Twilio-style SID (SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)"""
    return f"SM{uuid.uuid4().hex}"


def generate_account_sid() -> str:
    """Generate mock account SID"""
    return "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"


def save_message_to_file(message: Dict):
    """Save message to file for persistence and inspection"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    to_safe = message['to'].replace('+', '').replace(' ', '_')
    filename = f"{timestamp}_{to_safe}_{message['sid']}.json"

    filepath = STORAGE_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(message, f, indent=2)


async def simulate_status_transitions(message_sid: str):
    """Simulate message status transitions (queued → sent → delivered)"""
    import asyncio

    # Wait 2 seconds, then mark as sent
    await asyncio.sleep(2)
    for msg in messages_store:
        if msg['sid'] == message_sid and msg['status'] == 'queued':
            msg['status'] = 'sent'
            msg['date_sent'] = datetime.utcnow().isoformat()
            msg['date_updated'] = datetime.utcnow().isoformat()
            save_message_to_file(msg)
            break

    # Wait another 3 seconds, then mark as delivered
    await asyncio.sleep(3)
    for msg in messages_store:
        if msg['sid'] == message_sid and msg['status'] == 'sent':
            msg['status'] = 'delivered'
            msg['date_updated'] = datetime.utcnow().isoformat()
            save_message_to_file(msg)
            break


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """Health check"""
    return {
        "service": "Mock Twilio",
        "status": "operational",
        "messages_sent": len(messages_store),
        "storage_dir": str(STORAGE_DIR)
    }


@app.post("/Messages.json", response_model=MessageResponse)
async def send_message(
    background_tasks: BackgroundTasks,
    To: str = Form(...),
    From: str = Form(...),
    Body: str = Form(...),
    StatusCallback: Optional[str] = Form(None)
):
    """
    Send SMS message (Twilio-compatible endpoint)

    Form parameters:
    - To: Destination phone number (E.164 format)
    - From: Source phone number
    - Body: Message body
    - StatusCallback: Optional webhook URL for status updates
    """
    # Generate message
    message_sid = generate_sid()
    account_sid = generate_account_sid()
    now = datetime.utcnow()

    message = {
        "sid": message_sid,
        "account_sid": account_sid,
        "from": From,
        "to": To,
        "body": Body,
        "status": "queued",
        "direction": "outbound-api",
        "date_created": now.isoformat(),
        "date_updated": now.isoformat(),
        "date_sent": None,
        "price": None,
        "price_unit": "USD",
        "error_code": None,
        "error_message": None,
        "status_callback": StatusCallback
    }

    # Store message
    messages_store.append(message)
    save_message_to_file(message)

    # Schedule status transitions
    background_tasks.add_task(simulate_status_transitions, message_sid)

    print(f"📱 SMS Sent: {To} - {Body[:50]}{'...' if len(Body) > 50 else ''}")

    return MessageResponse(**message)


@app.get("/Messages.json", response_model=MessageListResponse)
def list_messages(
    PageSize: int = 50,
    Page: int = 0,
    To: Optional[str] = None,
    From: Optional[str] = None
):
    """
    List sent messages (Twilio-compatible endpoint)

    Query parameters:
    - PageSize: Number of messages per page (default 50)
    - Page: Page number (default 0)
    - To: Filter by destination phone
    - From: Filter by source phone
    """
    # Filter messages
    filtered = messages_store

    if To:
        filtered = [m for m in filtered if m['to'] == To]
    if From:
        filtered = [m for m in filtered if m['from'] == From]

    # Paginate
    start = Page * PageSize
    end = start + PageSize
    page_messages = filtered[start:end]

    return MessageListResponse(
        messages=[MessageResponse(**m) for m in page_messages],
        page=Page,
        page_size=PageSize
    )


@app.get("/Messages/{MessageSid}.json", response_model=MessageResponse)
def get_message(MessageSid: str):
    """
    Get specific message by SID (Twilio-compatible endpoint)
    """
    for message in messages_store:
        if message['sid'] == MessageSid:
            return MessageResponse(**message)

    raise HTTPException(status_code=404, detail=f"Message {MessageSid} not found")


@app.post("/webhooks/sms")
async def simulate_inbound_sms(request: InboundSmsRequest):
    """
    Simulate inbound SMS webhook

    Sends webhook to main API as if Twilio received an SMS reply.
    Used for testing inbound message handling.
    """
    import httpx

    # Generate SID if not provided
    message_sid = request.MessageSid or generate_sid()

    # Build webhook payload (Twilio format)
    webhook_payload = {
        "MessageSid": message_sid,
        "AccountSid": generate_account_sid(),
        "From": request.From,
        "To": request.To,
        "Body": request.Body,
        "NumMedia": "0",
        "FromCity": "",
        "FromState": "",
        "FromZip": "",
        "FromCountry": "US",
        "ToCity": "",
        "ToState": "",
        "ToZip": "",
        "ToCountry": "US",
        "SmsStatus": "received",
        "SmsSid": message_sid
    }

    # Store inbound message
    inbound_message = {
        "sid": message_sid,
        "account_sid": webhook_payload["AccountSid"],
        "from": request.From,
        "to": request.To,
        "body": request.Body,
        "status": "received",
        "direction": "inbound",
        "date_created": datetime.utcnow().isoformat(),
        "date_updated": datetime.utcnow().isoformat(),
        "date_sent": datetime.utcnow().isoformat(),
        "price": None,
        "price_unit": "USD",
        "error_code": None,
        "error_message": None
    }

    messages_store.append(inbound_message)
    save_message_to_file(inbound_message)

    # Send webhook to API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WEBHOOK_URL,
                data=webhook_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )

            print(f"📥 Inbound SMS webhook sent: {response.status_code}")

            return {
                "message": "Inbound SMS webhook sent",
                "message_sid": message_sid,
                "webhook_status": response.status_code,
                "webhook_url": WEBHOOK_URL
            }

    except Exception as e:
        print(f"❌ Webhook failed: {e}")
        return {
            "message": "Inbound SMS stored but webhook failed",
            "message_sid": message_sid,
            "error": str(e)
        }


@app.delete("/Messages")
def clear_messages():
    """Clear all stored messages (useful for testing)"""
    messages_store.clear()

    # Clear files
    for file in STORAGE_DIR.glob("*.json"):
        file.unlink()

    return {"message": "All messages cleared", "count": 0}


@app.get("/stats")
def get_stats():
    """Get message statistics"""
    total = len(messages_store)

    by_status = {}
    by_direction = {}

    for msg in messages_store:
        status = msg['status']
        direction = msg['direction']

        by_status[status] = by_status.get(status, 0) + 1
        by_direction[direction] = by_direction.get(direction, 0) + 1

    return {
        "total_messages": total,
        "by_status": by_status,
        "by_direction": by_direction,
        "storage_dir": str(STORAGE_DIR),
        "files_on_disk": len(list(STORAGE_DIR.glob("*.json")))
    }


# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
def startup():
    """Load messages from disk on startup"""
    print("🚀 Mock Twilio Service Starting...")
    print(f"📂 Storage directory: {STORAGE_DIR}")
    print(f"🔗 Webhook URL: {WEBHOOK_URL}")

    # Load existing messages from disk
    loaded = 0
    for file in STORAGE_DIR.glob("*.json"):
        try:
            with open(file, 'r') as f:
                message = json.load(f)
                messages_store.append(message)
                loaded += 1
        except Exception as e:
            print(f"⚠️  Failed to load {file}: {e}")

    if loaded > 0:
        print(f"✅ Loaded {loaded} messages from disk")

    print("✨ Mock Twilio ready to receive messages!")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=4010,
        reload=True,
        log_level="info"
    )
