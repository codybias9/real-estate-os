"""
Server-Sent Events Router
Real-time event streams for frontend clients
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
import uuid
import asyncio

from api.auth import get_current_user
from api.sse import sse_manager, send_event_generator
from db.models import User

router = APIRouter(prefix="/sse", tags=["Real-Time Events"])

# ============================================================================
# SSE ENDPOINTS
# ============================================================================

@router.get("/stream")
async def sse_stream(
    channels: Optional[str] = Query(None, description="Comma-separated list of channels to subscribe to"),
    current_user: User = Depends(get_current_user)
):
    """
    Establish Server-Sent Events connection

    Returns a persistent HTTP connection that streams real-time events

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
    const eventSource = new EventSource('/api/v1/sse/stream', {
        headers: {
            'Authorization': 'Bearer ' + token
        }
    });

    eventSource.addEventListener('property_updated', (event) => {
        const data = JSON.parse(event.data);
        console.log('Property updated:', data);
    });

    eventSource.addEventListener('stage_changed', (event) => {
        const data = JSON.parse(event.data);
        // Update UI with new stage
    });
    ```

    ## Channels

    By default, you're subscribed to:
    - Your team channel (all team events)
    - Your user channel (personal notifications)

    Optional channels:
    - `property:123` - Events for specific property
    - `pipeline` - All pipeline changes
    - `communications` - All communication events

    Args:
        channels: Additional channels to subscribe to
        current_user: Authenticated user (from JWT token)

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
        Async generator for streaming events
        """
        try:
            async for event in send_event_generator(queue):
                yield event

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
