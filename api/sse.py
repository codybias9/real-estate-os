"""
Server-Sent Events (SSE) Infrastructure
Real-time updates for frontend clients
"""
import asyncio
import json
from typing import Dict, Set, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# SSE EVENT MANAGER
# ============================================================================

class SSEConnectionManager:
    """
    Manages SSE connections and broadcasts events to connected clients

    Supports:
    - Team-specific channels (only users in same team receive events)
    - Property-specific channels (updates for specific properties)
    - User-specific channels (personal notifications)
    """

    def __init__(self):
        # Track active connections
        # Format: {connection_id: {"queue": asyncio.Queue, "team_id": int, "user_id": int}}
        self.active_connections: Dict[str, Dict[str, Any]] = {}

        # Track subscriptions
        # Format: {channel_name: Set[connection_id]}
        self.channel_subscriptions: Dict[str, Set[str]] = {}

    async def connect(
        self,
        connection_id: str,
        team_id: int,
        user_id: int,
        channels: Optional[list] = None
    ) -> asyncio.Queue:
        """
        Register a new SSE connection

        Args:
            connection_id: Unique connection identifier
            team_id: Team ID for access control
            user_id: User ID for personal notifications
            channels: List of channels to subscribe to

        Returns:
            asyncio.Queue for sending events to this connection
        """
        queue = asyncio.Queue()

        self.active_connections[connection_id] = {
            "queue": queue,
            "team_id": team_id,
            "user_id": user_id,
            "connected_at": datetime.utcnow()
        }

        # Subscribe to default team channel
        team_channel = f"team:{team_id}"
        self._subscribe_to_channel(connection_id, team_channel)

        # Subscribe to user channel
        user_channel = f"user:{user_id}"
        self._subscribe_to_channel(connection_id, user_channel)

        # Subscribe to additional channels
        if channels:
            for channel in channels:
                self._subscribe_to_channel(connection_id, channel)

        logger.info(f"SSE connection established: {connection_id} (team: {team_id}, user: {user_id})")

        return queue

    def disconnect(self, connection_id: str):
        """
        Remove an SSE connection
        """
        if connection_id in self.active_connections:
            # Remove from all channel subscriptions
            for channel_subs in self.channel_subscriptions.values():
                channel_subs.discard(connection_id)

            # Remove connection
            del self.active_connections[connection_id]

            logger.info(f"SSE connection closed: {connection_id}")

    def _subscribe_to_channel(self, connection_id: str, channel: str):
        """
        Subscribe connection to a channel
        """
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()

        self.channel_subscriptions[channel].add(connection_id)

    async def broadcast_to_team(
        self,
        team_id: int,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Broadcast event to all connections in a team

        Args:
            team_id: Team ID
            event_type: Event type (e.g., "property_updated", "stage_changed")
            data: Event data
        """
        channel = f"team:{team_id}"
        await self.broadcast_to_channel(channel, event_type, data)

    async def broadcast_to_user(
        self,
        user_id: int,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Send event to specific user
        """
        channel = f"user:{user_id}"
        await self.broadcast_to_channel(channel, event_type, data)

    async def broadcast_to_property(
        self,
        property_id: int,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Broadcast event to all connections watching a property
        """
        channel = f"property:{property_id}"
        await self.broadcast_to_channel(channel, event_type, data)

    async def broadcast_to_channel(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Broadcast event to all connections subscribed to a channel

        Args:
            channel: Channel name
            event_type: Event type
            data: Event data
        """
        if channel not in self.channel_subscriptions:
            logger.debug(f"No subscribers for channel: {channel}")
            return

        subscribers = self.channel_subscriptions[channel]

        if not subscribers:
            return

        event = _format_sse_event(event_type, data)

        # Send to all subscribers
        dead_connections = []

        for connection_id in subscribers:
            if connection_id in self.active_connections:
                queue = self.active_connections[connection_id]["queue"]

                try:
                    await queue.put(event)
                except Exception as e:
                    logger.error(f"Failed to send event to {connection_id}: {str(e)}")
                    dead_connections.append(connection_id)

        # Clean up dead connections
        for connection_id in dead_connections:
            self.disconnect(connection_id)

        logger.debug(f"Broadcasted {event_type} to {len(subscribers)} connections on {channel}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics
        """
        return {
            "total_connections": len(self.active_connections),
            "channels": len(self.channel_subscriptions),
            "connections_per_channel": {
                channel: len(subs)
                for channel, subs in self.channel_subscriptions.items()
            }
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Single global instance shared across application
sse_manager = SSEConnectionManager()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Format data as SSE event

    SSE format:
    event: event_type
    data: json_data
    id: event_id
    (blank line)
    """
    event_id = datetime.utcnow().isoformat()

    # Ensure data is JSON-serializable
    json_data = json.dumps({
        **data,
        "timestamp": event_id
    }, default=str)

    return f"event: {event_type}\ndata: {json_data}\nid: {event_id}\n\n"


async def send_event_generator(queue: asyncio.Queue):
    """
    Async generator for SSE events

    Yields events from queue as they arrive
    """
    try:
        while True:
            # Wait for next event
            event = await queue.get()

            yield event

    except asyncio.CancelledError:
        # Connection closed by client
        pass


# ============================================================================
# EVENT EMITTERS
# ============================================================================

async def emit_property_update(property_id: int, team_id: int, data: Dict[str, Any]):
    """
    Emit property update event

    Sent to:
    - Team channel (all team members)
    - Property channel (users watching this property)
    """
    await sse_manager.broadcast_to_team(
        team_id,
        "property_updated",
        {"property_id": property_id, **data}
    )

    await sse_manager.broadcast_to_property(
        property_id,
        "property_updated",
        data
    )


async def emit_stage_change(property_id: int, team_id: int, old_stage: str, new_stage: str):
    """
    Emit pipeline stage change event
    """
    data = {
        "property_id": property_id,
        "old_stage": old_stage,
        "new_stage": new_stage
    }

    await sse_manager.broadcast_to_team(team_id, "stage_changed", data)
    await sse_manager.broadcast_to_property(property_id, "stage_changed", data)


async def emit_timeline_event(property_id: int, team_id: int, event_data: Dict[str, Any]):
    """
    Emit timeline event (new activity on property)
    """
    data = {
        "property_id": property_id,
        **event_data
    }

    await sse_manager.broadcast_to_team(team_id, "timeline_event", data)
    await sse_manager.broadcast_to_property(property_id, "timeline_event", data)


async def emit_communication_received(property_id: int, team_id: int, communication_data: Dict[str, Any]):
    """
    Emit new communication received event (email reply, SMS, call)
    """
    data = {
        "property_id": property_id,
        **communication_data
    }

    await sse_manager.broadcast_to_team(team_id, "communication_received", data)
    await sse_manager.broadcast_to_property(property_id, "communication_received", data)


async def emit_job_complete(user_id: int, job_id: str, result: Dict[str, Any]):
    """
    Emit background job completion event
    """
    data = {
        "job_id": job_id,
        "result": result
    }

    await sse_manager.broadcast_to_user(user_id, "job_complete", data)


async def emit_notification(user_id: int, notification: Dict[str, Any]):
    """
    Send notification to specific user
    """
    await sse_manager.broadcast_to_user(user_id, "notification", notification)
