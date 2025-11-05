"""Server-Sent Events (SSE) router for real-time updates."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator
import redis.asyncio as aioredis

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..config import settings

router = APIRouter(prefix="/sse", tags=["real-time"])

# Redis pub/sub channels
CHANNEL_PREFIX = "realestate:events:"


class SSEManager:
    """Manager for SSE connections and event broadcasting."""

    def __init__(self):
        """Initialize SSE manager."""
        self.redis_client = None
        self.active_connections: dict[int, list[asyncio.Queue]] = {}

    async def connect(self):
        """Connect to Redis."""
        if not self.redis_client:
            try:
                self.redis_client = await aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                )
            except Exception as e:
                print(f"Redis connection failed: {e}")

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()

    async def subscribe(
        self, organization_id: int, user_id: int
    ) -> AsyncGenerator[str, None]:
        """
        Subscribe to organization events.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Yields:
            SSE formatted event strings
        """
        await self.connect()

        # Create queue for this connection
        queue = asyncio.Queue()

        # Add to active connections
        if organization_id not in self.active_connections:
            self.active_connections[organization_id] = []
        self.active_connections[organization_id].append(queue)

        try:
            # Subscribe to Redis channel
            channel_name = f"{CHANNEL_PREFIX}{organization_id}"
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel_name)

            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Listen for messages
            while True:
                try:
                    # Wait for message from Redis or queue
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=30.0,
                    )

                    if message and message["type"] == "message":
                        # Forward message to client
                        yield f"data: {message['data']}\n\n"
                    else:
                        # Send heartbeat to keep connection alive
                        yield f": heartbeat\n\n"

                except asyncio.TimeoutError:
                    # Send heartbeat on timeout
                    yield f": heartbeat\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            # Cleanup
            if organization_id in self.active_connections:
                self.active_connections[organization_id].remove(queue)
                if not self.active_connections[organization_id]:
                    del self.active_connections[organization_id]

            await pubsub.unsubscribe(channel_name)
            await pubsub.close()

    async def broadcast(
        self, organization_id: int, event_type: str, data: dict
    ):
        """
        Broadcast event to all clients in an organization.

        Args:
            organization_id: Organization ID
            event_type: Event type
            data: Event data
        """
        await self.connect()

        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        channel_name = f"{CHANNEL_PREFIX}{organization_id}"

        try:
            await self.redis_client.publish(channel_name, json.dumps(event))
        except Exception as e:
            print(f"Broadcast error: {e}")


# Global SSE manager instance
sse_manager = SSEManager()


@router.get("/stream")
async def event_stream(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    SSE endpoint for real-time event streaming.

    Clients connect to this endpoint to receive real-time updates
    about changes in their organization.

    Events include:
    - property.created
    - property.updated
    - property.deleted
    - lead.created
    - lead.updated
    - lead.assigned
    - deal.created
    - deal.stage_changed
    - campaign.completed
    """
    async def event_generator():
        """Generate SSE events."""
        async for event in sse_manager.subscribe(
            current_user.organization_id, current_user.id
        ):
            if await request.is_disconnected():
                break
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )


@router.get("/status")
async def get_sse_status(current_user: User = Depends(get_current_user)):
    """Get SSE connection status."""
    org_id = current_user.organization_id
    active_connections = len(sse_manager.active_connections.get(org_id, []))

    return {
        "organization_id": org_id,
        "active_connections": active_connections,
        "redis_connected": sse_manager.redis_client is not None,
    }


# Helper functions for broadcasting events

async def broadcast_property_created(organization_id: int, property_data: dict):
    """Broadcast property.created event."""
    await sse_manager.broadcast(organization_id, "property.created", property_data)


async def broadcast_property_updated(organization_id: int, property_data: dict):
    """Broadcast property.updated event."""
    await sse_manager.broadcast(organization_id, "property.updated", property_data)


async def broadcast_property_deleted(organization_id: int, property_id: int):
    """Broadcast property.deleted event."""
    await sse_manager.broadcast(
        organization_id, "property.deleted", {"property_id": property_id}
    )


async def broadcast_lead_created(organization_id: int, lead_data: dict):
    """Broadcast lead.created event."""
    await sse_manager.broadcast(organization_id, "lead.created", lead_data)


async def broadcast_lead_updated(organization_id: int, lead_data: dict):
    """Broadcast lead.updated event."""
    await sse_manager.broadcast(organization_id, "lead.updated", lead_data)


async def broadcast_lead_assigned(
    organization_id: int, lead_id: int, assigned_to: int
):
    """Broadcast lead.assigned event."""
    await sse_manager.broadcast(
        organization_id,
        "lead.assigned",
        {"lead_id": lead_id, "assigned_to": assigned_to},
    )


async def broadcast_deal_created(organization_id: int, deal_data: dict):
    """Broadcast deal.created event."""
    await sse_manager.broadcast(organization_id, "deal.created", deal_data)


async def broadcast_deal_stage_changed(
    organization_id: int, deal_id: int, old_stage: str, new_stage: str
):
    """Broadcast deal.stage_changed event."""
    await sse_manager.broadcast(
        organization_id,
        "deal.stage_changed",
        {
            "deal_id": deal_id,
            "old_stage": old_stage,
            "new_stage": new_stage,
        },
    )


async def broadcast_campaign_completed(organization_id: int, campaign_data: dict):
    """Broadcast campaign.completed event."""
    await sse_manager.broadcast(
        organization_id, "campaign.completed", campaign_data
    )


async def broadcast_notification(
    organization_id: int, user_id: int | None, message: str, notification_type: str = "info"
):
    """
    Broadcast notification to users.

    Args:
        organization_id: Organization ID
        user_id: User ID (None for all users)
        message: Notification message
        notification_type: Type of notification (info, success, warning, error)
    """
    await sse_manager.broadcast(
        organization_id,
        "notification",
        {
            "user_id": user_id,
            "message": message,
            "type": notification_type,
        },
    )
