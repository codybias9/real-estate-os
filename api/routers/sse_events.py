"""
Server-Sent Events Router
Real-time event streams for frontend clients

IMPORTANT: EventSource Authentication
Browsers' EventSource API doesn't support custom headers, so we use
query parameter tokens instead of Authorization headers.

Flow:
1. Client gets SSE token from /sse/token endpoint
2. Client connects to /sse/stream?token=<short-lived-token>
3. Token expires after 5 minutes; client must reconnect with new token
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
import uuid
import asyncio

from api.auth import get_current_user, get_current_user_from_query, create_sse_token
from api.sse import sse_manager, send_event_generator
from db.models import User

router = APIRouter(prefix="/sse-events", tags=["Real-Time Events"])

# ============================================================================
# SSE ENDPOINTS
# ============================================================================

@router.get("/token")
async def get_sse_token(current_user: User = Depends(get_current_user)):
    """
    Get a short-lived SSE token for EventSource connections

    EventSource doesn't support custom headers, so we use query parameters.
    This endpoint generates a short-lived token (5 minutes) that can be
    used to authenticate SSE connections.

    Returns:
        - token: Short-lived JWT token
        - expires_in: Token expiration time in seconds
        - stream_url: Full SSE stream URL with token

    Usage:
        ```javascript
        // Step 1: Get SSE token
        const response = await fetch('/api/v1/sse/token', {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });
        const { token, stream_url } = await response.json();

        // Step 2: Connect to SSE
        const eventSource = new EventSource(stream_url);

        eventSource.addEventListener('property_updated', (event) => {
            const data = JSON.parse(event.data);
            console.log('Property updated:', data);
        });

        // Step 3: Handle reconnection (token expires in 5 minutes)
        eventSource.onerror = async () => {
            eventSource.close();
            // Get new token and reconnect
            await reconnectSSE();
        };
        ```
    """
    token = create_sse_token(current_user.id)

    return {
        "token": token,
        "expires_in": 300,  # 5 minutes
        "stream_url": f"/api/v1/sse/stream?token={token}",
        "user_id": current_user.id,
        "team_id": current_user.team_id
    }


@router.get("/stream")
async def sse_stream(
    token: str = Query(..., description="Short-lived SSE token from /sse/token"),
    channels: Optional[str] = Query(None, description="Comma-separated list of channels to subscribe to"),
    current_user: User = Depends(get_current_user_from_query)
):
    """
    Establish Server-Sent Events connection

    Returns a persistent HTTP connection that streams real-time events

    **IMPORTANT:** This endpoint requires a short-lived SSE token in the query
    parameter because browsers' EventSource API doesn't support custom headers.
    Get a token from GET /sse/token first.

    ## Event Types

    **Property Events:**
    - `property_updated`: Property data changed
    - `stage_changed`: Property moved to different pipeline stage
    - `timeline_event`: New activity on property timeline

    **Communication Events:**
    - `communication_received`: New email/SMS/call received
    - `email_opened`: Email opened by recipient
    - `email_clicked`: Link clicked in email

    **Job Events:**
    - `job_complete`: Background job finished
    - `job_failed`: Background job failed

    **Notifications:**
    - `notification`: User notification (task assigned, mention, etc.)

    ## Usage

    ```javascript
    // Step 1: Get SSE token
    const { token, stream_url } = await fetch('/api/v1/sse/token', {
        headers: { 'Authorization': `Bearer ${accessToken}` }
    }).then(r => r.json());

    // Step 2: Connect using token in query string
    const eventSource = new EventSource(stream_url);

    eventSource.addEventListener('property_updated', (event) => {
        const data = JSON.parse(event.data);
        console.log('Property updated:', data);
    });

    eventSource.addEventListener('stage_changed', (event) => {
        const data = JSON.parse(event.data);
        // Update UI with new stage
    });

    // Step 3: Handle token expiration (5 minutes)
    eventSource.onerror = () => {
        eventSource.close();
        // Reconnect with new token
        reconnectSSE();
    };
    ```

    ## Channels

    By default, you're subscribed to:
    - Your team channel (all team events)
    - Your user channel (personal notifications)

    Optional channels:
    - `property:123` - Events for specific property
    - `pipeline` - All pipeline changes
    - `communications` - All communication events

    ## Infrastructure Notes

    For production deployment:
    - Set nginx/ingress proxy_read_timeout to 3600s or higher
    - Enable nginx keepalive: proxy_http_version 1.1 and proxy_set_header Connection ""
    - Disable buffering: X-Accel-Buffering: no (already set in response headers)
    - Implement heartbeat: server sends comment every 30s to prevent timeouts

    Args:
        token: Short-lived SSE token (get from /sse/token)
        channels: Additional channels to subscribe to
        current_user: Authenticated user (from token)

    Returns:
        StreamingResponse with text/event-stream content type
    """
    # Generate unique connection ID
    connection_id = str(uuid.uuid4())

    # Parse channels
    channel_list = []
    if channels:
        channel_list = [c.strip() for c in channels.split(",")]

    # Register connection
    queue = await sse_manager.connect(
        connection_id=connection_id,
        team_id=current_user.team_id,
        user_id=current_user.id,
        channels=channel_list
    )

    # Send initial connection event
    await queue.put(
        f"event: connected\n"
        f"data: {{'connection_id': '{connection_id}', 'user_id': {current_user.id}}}\n\n"
    )

    async def event_stream():
        """
        Async generator for streaming events with heartbeat

        Sends heartbeat comments every 30 seconds to:
        - Prevent proxy timeouts
        - Detect disconnected clients
        - Keep connection alive
        """
        import time

        last_heartbeat = time.time()
        HEARTBEAT_INTERVAL = 30  # seconds

        try:
            while True:
                # Check if heartbeat is needed
                now = time.time()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    # Send heartbeat comment (doesn't trigger event listeners)
                    yield f": heartbeat {int(now)}\n\n"
                    last_heartbeat = now

                # Try to get event with timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event
                except asyncio.TimeoutError:
                    # No event, continue loop to check heartbeat
                    continue

        except asyncio.CancelledError:
            # Client disconnected
            pass
        finally:
            # Clean up connection
            sse_manager.disconnect(connection_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/stats")
async def get_sse_stats(current_user: User = Depends(get_current_user)):
    """
    Get SSE connection statistics

    Requires admin role

    Returns:
    - Total active connections
    - Channels and subscribers
    - Connection details
    """
    from api.auth import require_admin

    # Only admins can view stats
    require_admin(current_user)

    return sse_manager.get_stats()


# ============================================================================
# TEST ENDPOINTS (Development only)
# ============================================================================

@router.post("/test/emit")
async def test_emit_event(
    event_type: str = Query(..., description="Event type to emit"),
    property_id: Optional[int] = Query(None, description="Property ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Test endpoint for emitting events

    Development only - remove in production

    Useful for testing SSE connections without triggering real events
    """
    from api.sse import emit_property_update, emit_notification

    if property_id:
        await emit_property_update(
            property_id=property_id,
            team_id=current_user.team_id,
            data={
                "test": True,
                "message": "Test event triggered manually"
            }
        )
    else:
        await emit_notification(
            user_id=current_user.id,
            notification={
                "title": "Test Notification",
                "message": "This is a test event",
                "type": event_type
            }
        )

    return {
        "success": True,
        "message": f"Test event '{event_type}' emitted"
    }
