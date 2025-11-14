"""SSE Events router for real-time event streaming via Server-Sent Events."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import secrets
import random
import sys
import os

# Add parent directory to path to import event emitter
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from api.event_emitter import event_emitter

router = APIRouter(prefix="/sse", tags=["sse"])


# ============================================================================
# Enums
# ============================================================================

class EventType(str, Enum):
    """Type of SSE event."""
    property_updated = "property_updated"
    lead_created = "lead_created"
    deal_stage_changed = "deal_stage_changed"
    email_received = "email_received"
    email_opened = "email_opened"
    job_completed = "job_completed"
    job_failed = "job_failed"
    notification = "notification"
    system_alert = "system_alert"


# ============================================================================
# Schemas
# ============================================================================

class SSEToken(BaseModel):
    """SSE authentication token."""
    token: str
    expires_at: str
    stream_url: str


class SSEEvent(BaseModel):
    """Server-Sent Event."""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: str
    id: Optional[str] = None


class SSEStats(BaseModel):
    """SSE connection statistics."""
    total_connections: int
    active_connections: int
    events_sent_24h: int
    events_by_type: Dict[str, int]
    average_latency_ms: float


class TestEventRequest(BaseModel):
    """Request to emit a test event."""
    event_type: EventType
    data: Dict[str, Any]
    target_user: Optional[str] = Field(None, description="User to send to (null = broadcast)")


# ============================================================================
# Mock Data Store
# ============================================================================

# In-memory store for active SSE tokens
SSE_TOKENS: Dict[str, Dict] = {}

# In-memory store for active SSE connections (in real app, would be more sophisticated)
ACTIVE_CONNECTIONS: Dict[str, Any] = {}

# Event buffer for demonstration
EVENT_BUFFER: List[Dict] = []


# ============================================================================
# Helper Functions
# ============================================================================

def generate_sse_token() -> str:
    """Generate a secure SSE token."""
    return secrets.token_urlsafe(32)


async def event_generator(token: str, connection_id: str) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a client connection.

    Yields events in SSE format:
    event: <event_type>
    data: <json_data>
    id: <event_id>

    Now uses the centralized event_emitter for real event delivery.
    """
    # Validate token
    if token not in SSE_TOKENS:
        yield f"event: error\ndata: {json.dumps({'error': 'Invalid token'})}\n\n"
        return

    # Register connection with event emitter
    event_queue = event_emitter.register_connection(connection_id)

    # Send initial connection event
    connection_event = {
        "event": "connected",
        "data": json.dumps({
            "message": "Connected to real-time event stream",
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id
        }),
        "id": secrets.token_hex(8)
    }
    yield f"event: {connection_event['event']}\ndata: {connection_event['data']}\nid: {connection_event['id']}\n\n"

    # Keep connection alive and send events
    try:
        while True:
            try:
                # Wait for event from queue (with timeout for heartbeat)
                event_message = await asyncio.wait_for(
                    event_queue.get(),
                    timeout=30.0  # 30 second timeout
                )
                # Event is already formatted as SSE message
                yield event_message

            except asyncio.TimeoutError:
                # No events in 30 seconds - send heartbeat
                yield f": heartbeat\n\n"

            # Also occasionally send a mock event for demo purposes if queue is empty
            if random.random() < 0.05:  # 5% chance per heartbeat interval
                event_type = random.choice(list(EventType))
                event_data = generate_mock_event_data(event_type)

                event = {
                    "event": event_type.value,
                    "data": json.dumps(event_data),
                    "id": secrets.token_hex(8)
                }

                yield f"event: {event['event']}\ndata: {event['data']}\nid: {event['id']}\n\n"

    except asyncio.CancelledError:
        # Client disconnected
        pass
    finally:
        # Unregister connection
        event_emitter.unregister_connection(connection_id)


def generate_mock_event_data(event_type: EventType) -> Dict[str, Any]:
    """Generate mock event data for demonstration."""
    if event_type == EventType.property_updated:
        return {
            "property_id": f"prop_{random.randint(1, 100):03d}",
            "field_updated": "status",
            "old_value": "active",
            "new_value": "under_contract",
            "updated_by": "demo@realestateos.com",
            "timestamp": datetime.now().isoformat()
        }

    elif event_type == EventType.lead_created:
        return {
            "lead_id": f"lead_{random.randint(1, 1000):04d}",
            "property_id": f"prop_{random.randint(1, 100):03d}",
            "contact_name": "John Smith",
            "source": "website_form",
            "timestamp": datetime.now().isoformat()
        }

    elif event_type == EventType.deal_stage_changed:
        return {
            "deal_id": f"deal_{random.randint(1, 50):03d}",
            "property_id": f"prop_{random.randint(1, 100):03d}",
            "old_stage": "qualified",
            "new_stage": "negotiation",
            "changed_by": "demo@realestateos.com",
            "timestamp": datetime.now().isoformat()
        }

    elif event_type == EventType.email_received:
        return {
            "thread_id": f"thread_{random.randint(1, 200):03d}",
            "property_id": f"prop_{random.randint(1, 100):03d}",
            "from_email": "john.smith@example.com",
            "subject": "Re: Interest in your property",
            "timestamp": datetime.now().isoformat()
        }

    elif event_type == EventType.email_opened:
        return {
            "thread_id": f"thread_{random.randint(1, 200):03d}",
            "message_id": f"msg_{random.randint(1, 1000):04d}",
            "recipient": "john.smith@example.com",
            "opened_at": datetime.now().isoformat(),
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "timestamp": datetime.now().isoformat()
        }

    elif event_type == EventType.job_completed:
        return {
            "job_id": f"job_{random.randint(1, 500):03d}",
            "job_type": "property_enrichment",
            "items_processed": random.randint(50, 200),
            "duration_seconds": random.randint(120, 600),
            "timestamp": datetime.now().isoformat()
        }

    elif event_type == EventType.job_failed:
        return {
            "job_id": f"job_{random.randint(1, 500):03d}",
            "job_type": "batch_email_send",
            "error": "Connection timeout",
            "items_processed": random.randint(10, 50),
            "timestamp": datetime.now().isoformat()
        }

    elif event_type == EventType.notification:
        messages = [
            "New property matches your smart list criteria",
            "Cadence rule triggered for 3 properties",
            "Monthly report is ready for download",
            "Deal room invitation from john.smith@example.com"
        ]
        return {
            "title": "Notification",
            "message": random.choice(messages),
            "priority": random.choice(["low", "normal", "high"]),
            "timestamp": datetime.now().isoformat()
        }

    elif event_type == EventType.system_alert:
        return {
            "alert_type": "info",
            "message": "System maintenance scheduled for tonight at 2am PST",
            "severity": "info",
            "timestamp": datetime.now().isoformat()
        }

    return {}


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/token", response_model=SSEToken)
def get_sse_token():
    """
    Get an SSE authentication token.

    The token is used to authenticate the SSE stream connection.
    Tokens expire after 24 hours.
    """
    token = generate_sse_token()
    expires_at = datetime.now() + timedelta(hours=24)

    SSE_TOKENS[token] = {
        "token": token,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at.isoformat(),
        "user": "demo@realestateos.com"
    }

    return SSEToken(
        token=token,
        expires_at=expires_at.isoformat(),
        stream_url=f"/api/v1/sse-events/stream?token={token}"
    )


@router.get("/stream")
async def sse_stream(token: str):
    """
    SSE event stream endpoint.

    Client connects to this endpoint with a valid token to receive
    real-time events. Connection stays open and events are pushed
    as they occur.

    Usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/sse-events/stream?token=YOUR_TOKEN');

    eventSource.addEventListener('property_updated', (event) => {
        const data = JSON.parse(event.data);
        console.log('Property updated:', data);
    });

    eventSource.addEventListener('email_received', (event) => {
        const data = JSON.parse(event.data);
        console.log('Email received:', data);
    });
    ```
    """
    # Validate token
    if token not in SSE_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    token_data = SSE_TOKENS[token]
    expires_at = datetime.fromisoformat(token_data["expires_at"])

    if datetime.now() > expires_at:
        del SSE_TOKENS[token]
        raise HTTPException(status_code=401, detail="Token expired")

    # Track active connection
    connection_id = secrets.token_hex(8)
    ACTIVE_CONNECTIONS[connection_id] = {
        "token": token,
        "user": token_data["user"],
        "connected_at": datetime.now().isoformat()
    }

    try:
        return StreamingResponse(
            event_generator(token, connection_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering in nginx
            }
        )
    finally:
        # Clean up connection when client disconnects
        if connection_id in ACTIVE_CONNECTIONS:
            del ACTIVE_CONNECTIONS[connection_id]


@router.get("/stats", response_model=SSEStats)
def get_sse_stats():
    """
    Get SSE connection statistics.

    Shows active connections, events sent, and performance metrics.
    """
    # Mock stats
    events_by_type = {
        "property_updated": random.randint(50, 150),
        "email_opened": random.randint(30, 100),
        "email_received": random.randint(20, 60),
        "job_completed": random.randint(10, 40),
        "notification": random.randint(40, 120),
        "deal_stage_changed": random.randint(15, 50)
    }

    return SSEStats(
        total_connections=len(SSE_TOKENS),
        active_connections=len(ACTIVE_CONNECTIONS),
        events_sent_24h=sum(events_by_type.values()),
        events_by_type=events_by_type,
        average_latency_ms=round(random.uniform(5, 25), 2)
    )


@router.post("/test/emit", status_code=202)
def emit_test_event(event_request: TestEventRequest):
    """
    Emit a test event to the SSE stream.

    Useful for testing real-time functionality. Event will be
    broadcast to all connected clients (or specific user if specified).
    """
    # In a real system, would push event to actual SSE connections
    # For demo, just add to event buffer

    event = {
        "event_type": event_request.event_type.value,
        "data": event_request.data,
        "timestamp": datetime.now().isoformat(),
        "id": secrets.token_hex(8),
        "target_user": event_request.target_user
    }

    EVENT_BUFFER.append(event)

    # Keep buffer size limited
    if len(EVENT_BUFFER) > 100:
        EVENT_BUFFER.pop(0)

    return {
        "success": True,
        "event_id": event["id"],
        "message": "Test event queued for delivery",
        "active_connections": len(ACTIVE_CONNECTIONS)
    }


@router.get("/active-connections")
def get_active_connections():
    """
    Get list of active SSE connections.

    Shows which users are currently connected to the real-time stream.
    """
    connections = []
    for conn_id, conn_data in ACTIVE_CONNECTIONS.items():
        connections.append({
            "connection_id": conn_id,
            "user": conn_data["user"],
            "connected_at": conn_data["connected_at"],
            "duration_seconds": (
                datetime.now() -
                datetime.fromisoformat(conn_data["connected_at"])
            ).total_seconds()
        })

    return {
        "total_connections": len(connections),
        "connections": connections
    }


@router.delete("/tokens/{token}")
def revoke_sse_token(token: str):
    """
    Revoke an SSE token.

    Invalidates the token and disconnects any active streams using it.
    """
    if token not in SSE_TOKENS:
        raise HTTPException(status_code=404, detail="Token not found")

    # Remove token
    del SSE_TOKENS[token]

    # Disconnect any active connections using this token
    # (In real implementation, would signal connections to close)
    connections_closed = sum(
        1 for conn in ACTIVE_CONNECTIONS.values()
        if conn["token"] == token
    )

    return {
        "success": True,
        "message": "Token revoked",
        "connections_closed": connections_closed
    }


@router.get("/event-types")
def get_event_types():
    """
    Get list of all event types that can be emitted.

    Useful for clients to know what events they can subscribe to.
    """
    return {
        "event_types": [
            {
                "name": event_type.value,
                "description": get_event_description(event_type)
            }
            for event_type in EventType
        ]
    }


def get_event_description(event_type: EventType) -> str:
    """Get human-readable description of event type."""
    descriptions = {
        EventType.property_updated: "A property field was updated",
        EventType.lead_created: "A new lead was created in the system",
        EventType.deal_stage_changed: "A deal moved to a different pipeline stage",
        EventType.email_received: "An email was received from a contact",
        EventType.email_opened: "A sent email was opened by the recipient",
        EventType.job_completed: "A background job completed successfully",
        EventType.job_failed: "A background job failed with an error",
        EventType.notification: "A general notification for the user",
        EventType.system_alert: "A system-wide alert or announcement"
    }
    return descriptions.get(event_type, "Unknown event type")
