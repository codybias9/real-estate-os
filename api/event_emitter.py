"""Centralized event emitter for SSE real-time events."""
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import secrets
import json


class EventEmitter:
    """
    Centralized event emitter for SSE events.

    This class manages event broadcasting to active SSE connections.
    Events are queued and delivered to connected clients.
    """

    def __init__(self):
        # Event queue for each active connection
        self.connection_queues: Dict[str, asyncio.Queue] = {}
        # Global event history for debugging
        self.event_history: List[Dict[str, Any]] = []
        self.max_history = 100

    def register_connection(self, connection_id: str) -> asyncio.Queue:
        """Register a new SSE connection and return its event queue."""
        queue = asyncio.Queue(maxsize=100)
        self.connection_queues[connection_id] = queue
        return queue

    def unregister_connection(self, connection_id: str):
        """Unregister an SSE connection."""
        if connection_id in self.connection_queues:
            del self.connection_queues[connection_id]

    async def emit(
        self,
        event_type: str,
        data: Dict[str, Any],
        target_user: Optional[str] = None
    ):
        """
        Emit an event to all connected clients (or specific user).

        Args:
            event_type: Type of event (e.g., 'property_updated')
            data: Event data payload
            target_user: Optional user email to target specific user
        """
        event = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "id": secrets.token_hex(8),
            "target_user": target_user
        }

        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Format as SSE message
        sse_message = f"event: {event_type}\ndata: {json.dumps(data)}\nid: {event['id']}\n\n"

        # Queue event for all active connections
        # (In production, would filter by target_user and permissions)
        for conn_id, queue in list(self.connection_queues.items()):
            try:
                # Non-blocking put - drop if queue is full
                queue.put_nowait(sse_message)
            except asyncio.QueueFull:
                # Log warning in production
                pass
            except Exception:
                # Connection may have been removed
                pass

    def emit_sync(
        self,
        event_type: str,
        data: Dict[str, Any],
        target_user: Optional[str] = None
    ):
        """
        Synchronous wrapper for emit() - schedules emission on event loop.

        Use this from non-async route handlers.
        """
        try:
            # Try to get the running event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the coroutine
                asyncio.create_task(self.emit(event_type, data, target_user))
            else:
                # If no loop is running, run it
                loop.run_until_complete(self.emit(event_type, data, target_user))
        except RuntimeError:
            # No event loop - this is fine, events just won't be delivered
            # (happens during testing or if SSE is not active)
            pass

    def get_active_connections_count(self) -> int:
        """Get count of active SSE connections."""
        return len(self.connection_queues)

    def get_event_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent event history."""
        return self.event_history[-limit:]


# Global singleton instance
event_emitter = EventEmitter()


# Convenience functions for common events

def emit_property_updated(
    property_id: str,
    field_updated: str,
    old_value: Any,
    new_value: Any,
    updated_by: str
):
    """Emit a property_updated event."""
    event_emitter.emit_sync(
        event_type="property_updated",
        data={
            "property_id": property_id,
            "field_updated": field_updated,
            "old_value": old_value,
            "new_value": new_value,
            "updated_by": updated_by,
            "timestamp": datetime.now().isoformat()
        }
    )


def emit_deal_stage_changed(
    deal_id: str,
    property_id: str,
    old_stage: str,
    new_stage: str,
    changed_by: str
):
    """Emit a deal_stage_changed event."""
    event_emitter.emit_sync(
        event_type="deal_stage_changed",
        data={
            "deal_id": deal_id,
            "property_id": property_id,
            "old_stage": old_stage,
            "new_stage": new_stage,
            "changed_by": changed_by,
            "timestamp": datetime.now().isoformat()
        }
    )


def emit_lead_created(
    lead_id: str,
    contact_name: str,
    source: str,
    property_id: Optional[str] = None
):
    """Emit a lead_created event."""
    event_emitter.emit_sync(
        event_type="lead_created",
        data={
            "lead_id": lead_id,
            "property_id": property_id,
            "contact_name": contact_name,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
    )


def emit_email_received(
    thread_id: str,
    property_id: str,
    from_email: str,
    subject: str
):
    """Emit an email_received event."""
    event_emitter.emit_sync(
        event_type="email_received",
        data={
            "thread_id": thread_id,
            "property_id": property_id,
            "from_email": from_email,
            "subject": subject,
            "timestamp": datetime.now().isoformat()
        }
    )


def emit_job_completed(
    job_id: str,
    job_type: str,
    items_processed: int,
    duration_seconds: float
):
    """Emit a job_completed event."""
    event_emitter.emit_sync(
        event_type="job_completed",
        data={
            "job_id": job_id,
            "job_type": job_type,
            "items_processed": items_processed,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now().isoformat()
        }
    )


def emit_notification(
    title: str,
    message: str,
    priority: str = "normal",
    target_user: Optional[str] = None
):
    """Emit a notification event."""
    event_emitter.emit_sync(
        event_type="notification",
        data={
            "title": title,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        },
        target_user=target_user
    )
