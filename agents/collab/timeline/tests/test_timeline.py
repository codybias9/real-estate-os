"""
Tests for Collab.Timeline
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from timeline import CollabTimeline, TimelineEvent, EventType
from timeline.models import EventTypeEnum
from timeline.repository import TimelineRepository


class TestEventLogging:
    """Test timeline event logging"""

    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing"""
        repo = MagicMock(spec=TimelineRepository)
        return repo

    @pytest.fixture
    def timeline(self, mock_repository):
        """CollabTimeline instance with mocked repository"""
        return CollabTimeline(repository=mock_repository)

    def test_log_system_event(
        self, timeline, mock_repository, tenant_id, property_id
    ):
        """Test logging system event"""
        # Mock: event creation
        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_event.event_type = EventType.PROPERTY_DISCOVERED.value
        mock_event.title = "Property discovered"
        mock_event.content = "Found new property"
        mock_event.content_html = "<p>Found new property</p>"
        mock_event.is_system_event = True
        mock_event.created_at = datetime.now(timezone.utc)
        mock_repository.create_event.return_value = mock_event

        # Log event
        event = timeline.log_system_event(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type=EventType.PROPERTY_DISCOVERED,
            title="Property discovered",
            content="Found new property",
            event_source="Discovery.Resolver",
        )

        # Verify repository was called
        assert mock_repository.create_event.called
        call_args = mock_repository.create_event.call_args.kwargs
        assert call_args["tenant_id"] == tenant_id
        assert call_args["property_id"] == property_id
        assert call_args["event_type"] == EventType.PROPERTY_DISCOVERED.value
        assert call_args["is_system_event"] == True

        # Verify event was returned
        assert event is not None
        assert event.event_type == EventType.PROPERTY_DISCOVERED.value

    def test_log_system_event_with_markdown(
        self, timeline, mock_repository, tenant_id, property_id
    ):
        """Test markdown rendering for system events"""
        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_event.event_type = EventType.PROPERTY_SCORED.value
        mock_event.title = "Property scored"
        mock_event.content = "Property scored **78/100**"
        mock_event.content_html = None
        mock_event.is_system_event = True
        mock_event.created_at = datetime.now(timezone.utc)
        mock_repository.create_event.return_value = mock_event

        # Log event with markdown
        event = timeline.log_system_event(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type=EventType.PROPERTY_SCORED,
            title="Property scored",
            content="Property scored **78/100**",
            event_source="Score.Engine",
            event_data={"score": 78},
        )

        # Verify HTML was rendered (passed to repository)
        call_args = mock_repository.create_event.call_args.kwargs
        assert call_args["content_html"] is not None
        assert "<strong>" in call_args["content_html"] or "<p>" in call_args["content_html"]

    def test_add_comment(
        self, timeline, mock_repository, tenant_id, property_id, user_id, user_name
    ):
        """Test adding user comment"""
        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_event.event_type = EventType.COMMENT_ADDED.value
        mock_event.title = f"{user_name} commented"
        mock_event.content = "Great property!"
        mock_event.user_name = user_name
        mock_event.is_system_event = False
        mock_event.created_at = datetime.now(timezone.utc)
        mock_repository.create_event.return_value = mock_event

        # Add comment
        event = timeline.add_comment(
            tenant_id=tenant_id,
            property_id=property_id,
            user_id=user_id,
            user_name=user_name,
            content="Great property!",
        )

        # Verify repository was called
        assert mock_repository.create_event.called
        call_args = mock_repository.create_event.call_args.kwargs
        assert call_args["event_type"] == EventType.COMMENT_ADDED.value
        assert call_args["user_id"] == user_id
        assert call_args["user_name"] == user_name
        assert call_args["is_system_event"] == False

    def test_add_comment_with_attachments(
        self, timeline, mock_repository, tenant_id, property_id, user_id, user_name
    ):
        """Test adding comment with attachments"""
        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_event.event_type = EventType.COMMENT_ADDED.value
        mock_repository.create_event.return_value = mock_event

        attachments = ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]

        event = timeline.add_comment(
            tenant_id=tenant_id,
            property_id=property_id,
            user_id=user_id,
            user_name=user_name,
            content="Check out these photos",
            attachments=attachments,
        )

        call_args = mock_repository.create_event.call_args.kwargs
        assert call_args["attachments"] == attachments

    def test_add_note(
        self, timeline, mock_repository, tenant_id, property_id, user_id, user_name
    ):
        """Test adding user note"""
        # Mock note creation
        mock_note = MagicMock()
        mock_note.id = uuid4()
        mock_repository.create_note.return_value = mock_note

        # Mock event creation
        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_event.event_type = EventType.NOTE_ADDED.value
        mock_repository.create_event.return_value = mock_event

        # Add note
        result = timeline.add_note(
            tenant_id=tenant_id,
            property_id=property_id,
            user_id=user_id,
            user_name=user_name,
            title="Analysis Notes",
            content="# Market Analysis\n\nThis is a great area.",
        )

        # Verify note was created
        assert mock_repository.create_note.called
        note_call = mock_repository.create_note.call_args.kwargs
        assert note_call["title"] == "Analysis Notes"

        # Verify event was logged
        assert mock_repository.create_event.called
        event_call = mock_repository.create_event.call_args.kwargs
        assert event_call["event_type"] == EventType.NOTE_ADDED.value

        # Verify result
        assert "note_id" in result
        assert "event" in result

    def test_add_private_note(
        self, timeline, mock_repository, tenant_id, property_id, user_id, user_name
    ):
        """Test adding private note"""
        mock_note = MagicMock()
        mock_note.id = uuid4()
        mock_repository.create_note.return_value = mock_note

        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_repository.create_event.return_value = mock_event

        result = timeline.add_note(
            tenant_id=tenant_id,
            property_id=property_id,
            user_id=user_id,
            user_name=user_name,
            title="Private Note",
            content="Confidential analysis",
            is_private=True,
        )

        note_call = mock_repository.create_note.call_args.kwargs
        assert note_call["is_private"] == True

        event_call = mock_repository.create_event.call_args.kwargs
        assert event_call["event_data"]["is_private"] == True


class TestMarkdownRendering:
    """Test markdown rendering and sanitization"""

    @pytest.fixture
    def timeline(self):
        """CollabTimeline instance"""
        repo = MagicMock(spec=TimelineRepository)
        return CollabTimeline(repository=repo)

    def test_markdown_to_html(self, timeline, tenant_id, property_id):
        """Test markdown is converted to HTML"""
        timeline.repository.create_event.return_value = MagicMock()

        timeline.log_system_event(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type=EventType.PROPERTY_SCORED,
            title="Test",
            content="**Bold text** and *italic*",
        )

        call_args = timeline.repository.create_event.call_args.kwargs
        html = call_args["content_html"]

        assert "<strong>" in html or "<b>" in html  # Bold
        assert "<em>" in html or "<i>" in html  # Italic

    def test_html_sanitization(self, timeline, tenant_id, property_id):
        """Test that dangerous HTML is sanitized"""
        timeline.repository.create_event.return_value = MagicMock()

        # Try to inject script tag
        timeline.log_system_event(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type=EventType.COMMENT_ADDED,
            title="Test",
            content="<script>alert('xss')</script>Normal text",
        )

        call_args = timeline.repository.create_event.call_args.kwargs
        html = call_args["content_html"]

        # Script tag should be removed
        assert "<script>" not in html
        assert "Normal text" in html

    def test_allowed_html_tags(self, timeline, tenant_id, property_id):
        """Test that safe HTML tags are preserved"""
        timeline.repository.create_event.return_value = MagicMock()

        timeline.log_system_event(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type=EventType.COMMENT_ADDED,
            title="Test",
            content="[Link](https://example.com) and `code`",
        )

        call_args = timeline.repository.create_event.call_args.kwargs
        html = call_args["content_html"]

        # Links and code should be preserved
        assert "<a" in html or "href" in html  # Link
        assert "<code>" in html  # Code


class TestTimelineQueries:
    """Test timeline query operations"""

    @pytest.fixture
    def timeline(self):
        """CollabTimeline instance"""
        repo = MagicMock(spec=TimelineRepository)
        return CollabTimeline(repository=repo)

    def test_get_timeline(self, timeline, tenant_id, property_id):
        """Test getting timeline events"""
        # Mock events
        mock_events = [MagicMock(), MagicMock(), MagicMock()]
        for i, event in enumerate(mock_events):
            event.id = uuid4()
            event.event_type = f"event_{i}"
            event.title = f"Event {i}"
            event.is_system_event = True
            event.created_at = datetime.now(timezone.utc)

        timeline.repository.get_events.return_value = mock_events

        # Get timeline
        events = timeline.get_timeline(
            tenant_id=tenant_id,
            property_id=property_id,
            limit=50,
        )

        assert len(events) == 3
        assert timeline.repository.get_events.called

    def test_get_timeline_with_filters(self, timeline, tenant_id, property_id):
        """Test timeline with event type filter"""
        mock_events = [MagicMock()]
        timeline.repository.get_events.return_value = mock_events

        events = timeline.get_timeline(
            tenant_id=tenant_id,
            property_id=property_id,
            event_types=[EventType.COMMENT_ADDED, EventType.NOTE_ADDED],
            include_system=False,
        )

        # Verify filters were passed
        call_args = timeline.repository.get_events.call_args.kwargs
        assert call_args["event_types"] is not None
        assert call_args["include_system"] == False

    def test_get_statistics(self, timeline, tenant_id, property_id):
        """Test getting timeline statistics"""
        stats = {
            "property_discovered": 1,
            "property_scored": 1,
            "comment_added": 5,
            "note_added": 3,
        }
        timeline.repository.count_by_type.return_value = stats

        result = timeline.get_statistics(tenant_id, property_id)

        assert result["comment_added"] == 5
        assert result["note_added"] == 3


class TestSSEBroadcasts:
    """Test SSE subscription and broadcasts"""

    @pytest.fixture
    def timeline(self):
        """CollabTimeline with mock repository"""
        repo = MagicMock(spec=TimelineRepository)
        return CollabTimeline(repository=repo)

    @pytest.mark.asyncio
    async def test_subscribe_creates_queue(self, timeline, tenant_id, property_id):
        """Test that subscribe creates a queue"""
        queue = await timeline.subscribe(tenant_id, property_id)

        assert isinstance(queue, asyncio.Queue)
        key = (tenant_id, property_id)
        assert key in timeline._subscribers
        assert queue in timeline._subscribers[key]

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_queue(self, timeline, tenant_id, property_id):
        """Test that unsubscribe removes queue"""
        queue = await timeline.subscribe(tenant_id, property_id)

        await timeline.unsubscribe(tenant_id, property_id, queue)

        key = (tenant_id, property_id)
        assert queue not in timeline._subscribers.get(key, set())

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_subscribers(
        self, timeline, tenant_id, property_id
    ):
        """Test that broadcasts reach subscribers"""
        # Subscribe
        queue1 = await timeline.subscribe(tenant_id, property_id)
        queue2 = await timeline.subscribe(tenant_id, property_id)

        # Create mock event
        mock_event_model = MagicMock()
        mock_event_model.id = uuid4()
        mock_event_model.event_type = "test_event"
        mock_event_model.title = "Test Event"
        mock_event_model.content = "Test content"
        mock_event_model.is_system_event = True
        mock_event_model.created_at = datetime.now(timezone.utc)
        mock_event_model.event_data = {}
        mock_event_model.tags = None
        mock_event_model.user_name = None
        mock_event_model.content_html = "<p>Test content</p>"

        event = TimelineEvent(mock_event_model)

        # Broadcast
        await timeline._broadcast_event(tenant_id, property_id, event)

        # Wait for async broadcast
        await asyncio.sleep(0.01)

        # Verify both queues received event
        assert not queue1.empty()
        assert not queue2.empty()

        received1 = await queue1.get()
        received2 = await queue2.get()

        assert received1.title == "Test Event"
        assert received2.title == "Test Event"

    @pytest.mark.asyncio
    async def test_broadcast_property_isolation(self, timeline, tenant_id):
        """Test that broadcasts are property-isolated"""
        property1 = str(uuid4())
        property2 = str(uuid4())

        queue1 = await timeline.subscribe(tenant_id, property1)
        queue2 = await timeline.subscribe(tenant_id, property2)

        # Create event
        mock_event_model = MagicMock()
        mock_event_model.id = uuid4()
        mock_event_model.event_type = "test"
        mock_event_model.title = "Test"
        mock_event_model.is_system_event = True
        mock_event_model.created_at = datetime.now(timezone.utc)
        event = TimelineEvent(mock_event_model)

        # Broadcast to property1
        await timeline._broadcast_event(tenant_id, property1, event)
        await asyncio.sleep(0.01)

        # Only property1 queue should receive event
        assert not queue1.empty()
        assert queue2.empty()


class TestTimelineEvent:
    """Test TimelineEvent wrapper class"""

    def test_event_properties(self):
        """Test event property access"""
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.event_type = "property_scored"
        mock_model.title = "Property scored"
        mock_model.content = "Score: 78"
        mock_model.content_html = "<p>Score: 78</p>"
        mock_model.is_system_event = True
        mock_model.user_name = None
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.event_data = {"score": 78}
        mock_model.tags = ["investment", "high-score"]

        event = TimelineEvent(mock_model)

        assert event.event_type == "property_scored"
        assert event.title == "Property scored"
        assert event.content == "Score: 78"
        assert event.is_system_event == True

    def test_event_to_dict(self):
        """Test event serialization"""
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.event_type = "comment_added"
        mock_model.title = "User commented"
        mock_model.content = "Great property"
        mock_model.content_html = "<p>Great property</p>"
        mock_model.is_system_event = False
        mock_model.user_name = "John Doe"
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.event_data = {}
        mock_model.tags = []

        event = TimelineEvent(mock_model)
        data = event.to_dict()

        assert "id" in data
        assert data["event_type"] == "comment_added"
        assert data["title"] == "User commented"
        assert data["user_name"] == "John Doe"
        assert data["is_system_event"] == False
