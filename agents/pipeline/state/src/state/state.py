"""
Pipeline.State - Property state machine and SSE broadcasts

Single-Writer Pattern: Only this agent updates property states
"""

import asyncio
from collections import defaultdict
from typing import Optional, Dict, Set
from uuid import UUID
from datetime import datetime

from .models import PropertyStateEnum
from .repository import StateRepository


class StateTransition:
    """
    State transition event for SSE broadcasts.

    Sent to subscribers when a property changes state.
    """

    def __init__(
        self,
        property_id: str,
        tenant_id: str,
        from_state: str,
        to_state: str,
        event_id: str,
        event_subject: str,
        transitioned_at: datetime,
    ):
        self.property_id = property_id
        self.tenant_id = tenant_id
        self.from_state = from_state
        self.to_state = to_state
        self.event_id = event_id
        self.event_subject = event_subject
        self.transitioned_at = transitioned_at

    def to_dict(self) -> dict:
        """Serialize to dict for SSE"""
        return {
            "property_id": self.property_id,
            "tenant_id": self.tenant_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "event_id": self.event_id,
            "event_subject": self.event_subject,
            "transitioned_at": self.transitioned_at.isoformat(),
        }


class PropertyState:
    """Alias for PropertyStateEnum"""

    # Re-export enum values for convenience
    DISCOVERED = PropertyStateEnum.DISCOVERED
    ENRICHED = PropertyStateEnum.ENRICHED
    SCORED = PropertyStateEnum.SCORED
    MEMO_GENERATED = PropertyStateEnum.MEMO_GENERATED
    OUTREACH_PENDING = PropertyStateEnum.OUTREACH_PENDING
    CONTACTED = PropertyStateEnum.CONTACTED
    RESPONDED = PropertyStateEnum.RESPONDED
    ARCHIVED = PropertyStateEnum.ARCHIVED


class PipelineState:
    """
    Property state machine with SSE broadcast support.

    Features:
    - Tracks property lifecycle states
    - Validates state transitions
    - Broadcasts state changes via SSE
    - Maintains transition history
    - Single-writer pattern for state updates
    """

    # Valid state transitions (from_state → [valid_to_states])
    VALID_TRANSITIONS = {
        PropertyStateEnum.DISCOVERED: [PropertyStateEnum.ENRICHED, PropertyStateEnum.ARCHIVED],
        PropertyStateEnum.ENRICHED: [PropertyStateEnum.SCORED, PropertyStateEnum.ARCHIVED],
        PropertyStateEnum.SCORED: [PropertyStateEnum.MEMO_GENERATED, PropertyStateEnum.ARCHIVED],
        PropertyStateEnum.MEMO_GENERATED: [PropertyStateEnum.OUTREACH_PENDING, PropertyStateEnum.ARCHIVED],
        PropertyStateEnum.OUTREACH_PENDING: [PropertyStateEnum.CONTACTED, PropertyStateEnum.ARCHIVED],
        PropertyStateEnum.CONTACTED: [PropertyStateEnum.RESPONDED, PropertyStateEnum.ARCHIVED],
        PropertyStateEnum.RESPONDED: [PropertyStateEnum.ARCHIVED],
        PropertyStateEnum.ARCHIVED: [],  # Terminal state
    }

    # Event subject → target state mapping
    EVENT_STATE_MAP = {
        "event.discovery.intake": PropertyStateEnum.DISCOVERED,
        "event.enrichment.features": PropertyStateEnum.ENRICHED,
        "event.score.created": PropertyStateEnum.SCORED,
        "event.docgen.memo": PropertyStateEnum.MEMO_GENERATED,
        "event.outreach.scheduled": PropertyStateEnum.OUTREACH_PENDING,
        "event.outreach.sent": PropertyStateEnum.CONTACTED,
        "event.outreach.response": PropertyStateEnum.RESPONDED,
    }

    def __init__(self, repository: StateRepository):
        """
        Initialize state machine.

        Args:
            repository: StateRepository for persistence
        """
        self.repository = repository

        # SSE subscribers: tenant_id → set of queues
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)

    def handle_event(
        self,
        event_id: str,
        event_subject: str,
        tenant_id: str,
        payload: dict,
    ) -> Optional[StateTransition]:
        """
        Handle incoming event and update property state.

        Args:
            event_id: Event UUID
            event_subject: Event subject (e.g., "event.discovery.intake")
            tenant_id: Tenant UUID
            payload: Event payload

        Returns:
            StateTransition if state changed, None otherwise

        Example:
            >>> pipeline = PipelineState(repository)
            >>> transition = pipeline.handle_event(
            ...     event_id="event-uuid",
            ...     event_subject="event.discovery.intake",
            ...     tenant_id="tenant-uuid",
            ...     payload={"property_id": "prop-uuid", "apn": "123-456-789"}
            ... )
        """
        # Determine target state from event subject
        target_state = self.EVENT_STATE_MAP.get(event_subject)
        if not target_state:
            # Unknown event, ignore
            return None

        property_id = payload.get("property_id")
        if not property_id:
            # No property_id in payload, ignore
            return None

        # Get current state
        current_state_model = self.repository.get_state(property_id, tenant_id)

        if current_state_model is None:
            # No state exists, create initial state
            if target_state == PropertyStateEnum.DISCOVERED:
                self.repository.create_state(
                    property_id=property_id,
                    tenant_id=tenant_id,
                    initial_state=target_state,
                    event_id=event_id,
                    event_subject=event_subject,
                    context={"initial_event": event_id},
                )

                transition = StateTransition(
                    property_id=property_id,
                    tenant_id=tenant_id,
                    from_state="none",
                    to_state=target_state.value,
                    event_id=event_id,
                    event_subject=event_subject,
                    transitioned_at=datetime.utcnow(),
                )

                # Broadcast transition (only if event loop is running)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._broadcast_transition(tenant_id, transition))
                except RuntimeError:
                    # No event loop running, skip broadcast (sync context)
                    pass

                return transition
            else:
                # Unexpected: receiving non-discovery event for new property
                # Create state anyway (out-of-order events)
                self.repository.create_state(
                    property_id=property_id,
                    tenant_id=tenant_id,
                    initial_state=target_state,
                    event_id=event_id,
                    event_subject=event_subject,
                    context={"out_of_order": True},
                )
                return None

        # State exists, check if transition is valid
        current_state = PropertyStateEnum(current_state_model.current_state)

        if current_state == target_state:
            # Already in target state, idempotent (ignore)
            return None

        # Validate transition
        valid_next_states = self.VALID_TRANSITIONS.get(current_state, [])
        if target_state not in valid_next_states:
            # Invalid transition, log warning but don't block
            # (could be out-of-order events or replay)
            return None

        # Perform transition
        updated_state = self.repository.transition_state(
            property_id=property_id,
            tenant_id=tenant_id,
            to_state=target_state,
            event_id=event_id,
            event_subject=event_subject,
            event_payload=payload,
            reason=f"Event: {event_subject}",
        )

        transition = StateTransition(
            property_id=property_id,
            tenant_id=tenant_id,
            from_state=current_state.value,
            to_state=target_state.value,
            event_id=event_id,
            event_subject=event_subject,
            transitioned_at=updated_state.last_transition_at,
        )

        # Broadcast transition (only if event loop is running)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_transition(tenant_id, transition))
        except RuntimeError:
            # No event loop running, skip broadcast (sync context)
            pass

        return transition

    def get_state(self, property_id: str, tenant_id: str) -> Optional[PropertyStateEnum]:
        """
        Get current state for a property.

        Args:
            property_id: Property UUID
            tenant_id: Tenant UUID

        Returns:
            PropertyStateEnum if found, None otherwise
        """
        state_model = self.repository.get_state(property_id, tenant_id)
        if state_model:
            return PropertyStateEnum(state_model.current_state)
        return None

    def get_properties_by_state(
        self, state: PropertyStateEnum, tenant_id: str, limit: int = 100
    ) -> list:
        """
        Get all properties in a specific state.

        Args:
            state: Target state
            tenant_id: Tenant UUID
            limit: Maximum number of properties

        Returns:
            List of property state models
        """
        return self.repository.get_properties_by_state(state, tenant_id, limit)

    def get_statistics(self, tenant_id: str) -> dict:
        """
        Get state statistics for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict with counts per state
        """
        return self.repository.count_by_state(tenant_id)

    # SSE Subscription Management

    async def subscribe(self, tenant_id: str) -> asyncio.Queue:
        """
        Subscribe to state transitions for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Queue that will receive StateTransition events

        Example:
            >>> queue = await pipeline.subscribe("tenant-uuid")
            >>> while True:
            ...     transition = await queue.get()
            ...     print(f"Property {transition.property_id} → {transition.to_state}")
        """
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[tenant_id].add(queue)
        return queue

    async def unsubscribe(self, tenant_id: str, queue: asyncio.Queue):
        """
        Unsubscribe from state transitions.

        Args:
            tenant_id: Tenant UUID
            queue: Queue to remove
        """
        if tenant_id in self._subscribers:
            self._subscribers[tenant_id].discard(queue)

    async def _broadcast_transition(self, tenant_id: str, transition: StateTransition):
        """
        Broadcast transition to all subscribers for a tenant.

        Args:
            tenant_id: Tenant UUID
            transition: StateTransition event
        """
        if tenant_id not in self._subscribers:
            return

        # Send to all queues for this tenant
        for queue in list(self._subscribers[tenant_id]):
            try:
                # Non-blocking put, drop if queue is full
                queue.put_nowait(transition)
            except asyncio.QueueFull:
                # Queue is full, drop event
                # (subscriber is too slow)
                pass
