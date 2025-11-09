"""
Tests for Pipeline.State
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from state import PipelineState, PropertyState, StateTransition
from state.models import PropertyStateEnum
from state.repository import StateRepository


class TestStateTransitions:
    """Test basic state transitions"""

    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing"""
        repo = MagicMock(spec=StateRepository)
        return repo

    @pytest.fixture
    def pipeline(self, mock_repository):
        """PipelineState instance with mocked repository"""
        return PipelineState(repository=mock_repository)

    def test_initialization(self, pipeline):
        """Test PipelineState initialization"""
        assert pipeline.repository is not None
        assert len(pipeline._subscribers) == 0

    def test_handle_discovery_event_creates_state(
        self, pipeline, mock_repository, tenant_id, property_id, discovery_event
    ):
        """Test that discovery event creates initial state"""
        # Mock: no existing state
        mock_repository.get_state.return_value = None

        transition = pipeline.handle_event(
            event_id=discovery_event["event_id"],
            event_subject=discovery_event["event_subject"],
            tenant_id=tenant_id,
            payload=discovery_event["payload"],
        )

        # Verify state was created
        assert mock_repository.create_state.called
        call_args = mock_repository.create_state.call_args.kwargs
        assert call_args["property_id"] == property_id
        assert call_args["tenant_id"] == tenant_id
        assert call_args["initial_state"] == PropertyStateEnum.DISCOVERED

        # Verify transition was returned
        assert transition is not None
        assert transition.from_state == "none"
        assert transition.to_state == PropertyStateEnum.DISCOVERED.value

    def test_handle_enrichment_event_transitions_state(
        self, pipeline, mock_repository, tenant_id, property_id, enrichment_event
    ):
        """Test that enrichment event transitions from discovered to enriched"""
        # Mock: existing state = DISCOVERED
        mock_state = MagicMock()
        mock_state.current_state = PropertyStateEnum.DISCOVERED.value
        mock_repository.get_state.return_value = mock_state

        # Mock: transition returns updated state
        updated_state = MagicMock()
        updated_state.current_state = PropertyStateEnum.ENRICHED.value
        updated_state.last_transition_at = MagicMock()
        mock_repository.transition_state.return_value = updated_state

        transition = pipeline.handle_event(
            event_id=enrichment_event["event_id"],
            event_subject=enrichment_event["event_subject"],
            tenant_id=tenant_id,
            payload=enrichment_event["payload"],
        )

        # Verify transition was performed
        assert mock_repository.transition_state.called
        call_args = mock_repository.transition_state.call_args.kwargs
        assert call_args["property_id"] == property_id
        assert call_args["to_state"] == PropertyStateEnum.ENRICHED

        # Verify transition was returned
        assert transition is not None
        assert transition.from_state == PropertyStateEnum.DISCOVERED.value
        assert transition.to_state == PropertyStateEnum.ENRICHED.value

    def test_idempotent_event_handling(
        self, pipeline, mock_repository, tenant_id, property_id, enrichment_event
    ):
        """Test that duplicate events are idempotent (no transition)"""
        # Mock: already in ENRICHED state
        mock_state = MagicMock()
        mock_state.current_state = PropertyStateEnum.ENRICHED.value
        mock_repository.get_state.return_value = mock_state

        transition = pipeline.handle_event(
            event_id=enrichment_event["event_id"],
            event_subject=enrichment_event["event_subject"],
            tenant_id=tenant_id,
            payload=enrichment_event["payload"],
        )

        # Verify no transition was performed
        assert not mock_repository.transition_state.called
        assert transition is None

    def test_invalid_transition_rejected(
        self, pipeline, mock_repository, tenant_id, property_id, score_event
    ):
        """Test that invalid transitions are rejected"""
        # Mock: current state = DISCOVERED (can't go directly to SCORED)
        mock_state = MagicMock()
        mock_state.current_state = PropertyStateEnum.DISCOVERED.value
        mock_repository.get_state.return_value = mock_state

        transition = pipeline.handle_event(
            event_id=score_event["event_id"],
            event_subject=score_event["event_subject"],
            tenant_id=tenant_id,
            payload=score_event["payload"],
        )

        # Verify transition was rejected
        assert not mock_repository.transition_state.called
        assert transition is None

    def test_unknown_event_ignored(
        self, pipeline, mock_repository, tenant_id, property_id
    ):
        """Test that unknown events are ignored"""
        transition = pipeline.handle_event(
            event_id=str(uuid4()),
            event_subject="event.unknown.subject",
            tenant_id=tenant_id,
            payload={"property_id": property_id},
        )

        assert transition is None
        assert not mock_repository.get_state.called

    def test_event_without_property_id_ignored(
        self, pipeline, mock_repository, tenant_id
    ):
        """Test that events without property_id are ignored"""
        transition = pipeline.handle_event(
            event_id=str(uuid4()),
            event_subject="event.discovery.intake",
            tenant_id=tenant_id,
            payload={"apn": "123-456-789"},  # No property_id
        )

        assert transition is None

    def test_get_state(self, pipeline, mock_repository, tenant_id, property_id):
        """Test getting current state for a property"""
        # Mock: state exists
        mock_state = MagicMock()
        mock_state.current_state = PropertyStateEnum.SCORED.value
        mock_repository.get_state.return_value = mock_state

        state = pipeline.get_state(property_id, tenant_id)

        assert state == PropertyStateEnum.SCORED
        assert mock_repository.get_state.called

    def test_get_state_not_found(
        self, pipeline, mock_repository, tenant_id, property_id
    ):
        """Test getting state for non-existent property"""
        mock_repository.get_state.return_value = None

        state = pipeline.get_state(property_id, tenant_id)

        assert state is None

    def test_get_properties_by_state(self, pipeline, mock_repository, tenant_id):
        """Test querying properties by state"""
        # Mock: 3 properties in SCORED state
        mock_properties = [MagicMock(), MagicMock(), MagicMock()]
        mock_repository.get_properties_by_state.return_value = mock_properties

        properties = pipeline.get_properties_by_state(
            PropertyState.SCORED, tenant_id, limit=10
        )

        assert len(properties) == 3
        assert mock_repository.get_properties_by_state.called

    def test_get_statistics(self, pipeline, mock_repository, tenant_id):
        """Test getting state statistics"""
        # Mock: statistics
        mock_stats = {
            "discovered": 10,
            "enriched": 5,
            "scored": 3,
            "memo_generated": 1,
        }
        mock_repository.count_by_state.return_value = mock_stats

        stats = pipeline.get_statistics(tenant_id)

        assert stats["discovered"] == 10
        assert stats["scored"] == 3


class TestStateTransitionModel:
    """Test StateTransition model"""

    def test_transition_to_dict(self):
        """Test serialization to dict"""
        from datetime import datetime, timezone

        transition = StateTransition(
            property_id="prop-uuid",
            tenant_id="tenant-uuid",
            from_state="discovered",
            to_state="enriched",
            event_id="event-uuid",
            event_subject="event.enrichment.features",
            transitioned_at=datetime.now(timezone.utc),
        )

        data = transition.to_dict()

        assert data["property_id"] == "prop-uuid"
        assert data["tenant_id"] == "tenant-uuid"
        assert data["from_state"] == "discovered"
        assert data["to_state"] == "enriched"
        assert data["event_id"] == "event-uuid"
        assert "transitioned_at" in data


class TestSSEBroadcasts:
    """Test SSE subscription and broadcasts"""

    @pytest.fixture
    def pipeline(self):
        """PipelineState with mock repository"""
        repo = MagicMock(spec=StateRepository)
        return PipelineState(repository=repo)

    @pytest.mark.asyncio
    async def test_subscribe_creates_queue(self, pipeline, tenant_id):
        """Test that subscribe creates a queue"""
        queue = await pipeline.subscribe(tenant_id)

        assert isinstance(queue, asyncio.Queue)
        assert tenant_id in pipeline._subscribers
        assert queue in pipeline._subscribers[tenant_id]

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_queue(self, pipeline, tenant_id):
        """Test that unsubscribe removes queue"""
        queue = await pipeline.subscribe(tenant_id)

        await pipeline.unsubscribe(tenant_id, queue)

        assert queue not in pipeline._subscribers.get(tenant_id, set())

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_subscribers(self, pipeline, tenant_id):
        """Test that broadcasts reach subscribers"""
        # Subscribe
        queue1 = await pipeline.subscribe(tenant_id)
        queue2 = await pipeline.subscribe(tenant_id)

        # Create transition
        from datetime import datetime, timezone

        transition = StateTransition(
            property_id="prop-uuid",
            tenant_id=tenant_id,
            from_state="discovered",
            to_state="enriched",
            event_id="event-uuid",
            event_subject="event.enrichment.features",
            transitioned_at=datetime.now(timezone.utc),
        )

        # Broadcast
        await pipeline._broadcast_transition(tenant_id, transition)

        # Wait for async broadcast to complete
        await asyncio.sleep(0.01)

        # Verify both queues received transition
        assert not queue1.empty()
        assert not queue2.empty()

        received1 = await queue1.get()
        received2 = await queue2.get()

        assert received1.property_id == "prop-uuid"
        assert received2.property_id == "prop-uuid"

    @pytest.mark.asyncio
    async def test_broadcast_only_to_tenant(self, pipeline):
        """Test that broadcasts are tenant-isolated"""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        queue1 = await pipeline.subscribe(tenant1)
        queue2 = await pipeline.subscribe(tenant2)

        # Broadcast to tenant1
        from datetime import datetime, timezone

        transition = StateTransition(
            property_id="prop-uuid",
            tenant_id=tenant1,
            from_state="discovered",
            to_state="enriched",
            event_id="event-uuid",
            event_subject="event.enrichment.features",
            transitioned_at=datetime.now(timezone.utc),
        )

        await pipeline._broadcast_transition(tenant1, transition)
        await asyncio.sleep(0.01)

        # Verify only tenant1 queue received transition
        assert not queue1.empty()
        assert queue2.empty()

    @pytest.mark.asyncio
    async def test_broadcast_drops_when_queue_full(self, pipeline, tenant_id):
        """Test that broadcasts drop events when queue is full"""
        queue = await pipeline.subscribe(tenant_id)

        # Fill queue to capacity (default maxsize=100)
        for i in range(100):
            await queue.put(f"item-{i}")

        # Try to broadcast when queue is full
        from datetime import datetime, timezone

        transition = StateTransition(
            property_id="prop-uuid",
            tenant_id=tenant_id,
            from_state="discovered",
            to_state="enriched",
            event_id="event-uuid",
            event_subject="event.enrichment.features",
            transitioned_at=datetime.now(timezone.utc),
        )

        # Should not raise exception (event is dropped)
        await pipeline._broadcast_transition(tenant_id, transition)

        # Queue should still have original items
        assert queue.qsize() == 100


class TestValidTransitions:
    """Test state transition validation"""

    def test_valid_transitions_map(self):
        """Test that VALID_TRANSITIONS map is complete"""
        # All states should have an entry
        for state in PropertyStateEnum:
            assert state in PipelineState.VALID_TRANSITIONS

    def test_event_state_map(self):
        """Test that EVENT_STATE_MAP covers expected events"""
        expected_events = [
            "event.discovery.intake",
            "event.enrichment.features",
            "event.score.created",
            "event.docgen.memo",
            "event.outreach.scheduled",
            "event.outreach.sent",
            "event.outreach.response",
        ]

        for event in expected_events:
            assert event in PipelineState.EVENT_STATE_MAP

    def test_archived_is_terminal_state(self):
        """Test that archived state has no valid transitions"""
        valid_next = PipelineState.VALID_TRANSITIONS[PropertyStateEnum.ARCHIVED]
        assert len(valid_next) == 0


class TestPropertyStateAlias:
    """Test PropertyState alias"""

    def test_property_state_has_all_states(self):
        """Test that PropertyState exposes all states"""
        assert PropertyState.DISCOVERED == PropertyStateEnum.DISCOVERED
        assert PropertyState.ENRICHED == PropertyStateEnum.ENRICHED
        assert PropertyState.SCORED == PropertyStateEnum.SCORED
        assert PropertyState.MEMO_GENERATED == PropertyStateEnum.MEMO_GENERATED
        assert PropertyState.OUTREACH_PENDING == PropertyStateEnum.OUTREACH_PENDING
        assert PropertyState.CONTACTED == PropertyStateEnum.CONTACTED
        assert PropertyState.RESPONDED == PropertyStateEnum.RESPONDED
        assert PropertyState.ARCHIVED == PropertyStateEnum.ARCHIVED
