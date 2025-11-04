"""
Tests for cache invalidation strategies
"""

import pytest
import fakeredis
from cache.client import get_cache_client
from cache.invalidation import (
    CacheInvalidator,
    get_cache_invalidator,
    invalidate_property,
    invalidate_property_list,
    invalidate_property_score,
    invalidate_timeline,
    invalidate_tenant,
    invalidate_all,
    PropertyUpdateStrategy,
    ScoreUpdateStrategy,
    TimelineUpdateStrategy,
    EventDrivenInvalidator,
    handle_cache_event,
)


@pytest.fixture
def mock_cache():
    """Mock cache client with fake Redis"""
    cache = get_cache_client()
    cache.client = fakeredis.FakeRedis(decode_responses=True)
    cache.available = True
    # Clear before each test
    cache.flush()
    return cache


@pytest.fixture
def invalidator(mock_cache):
    """Create cache invalidator"""
    return CacheInvalidator()


class TestCacheInvalidator:
    """Tests for cache invalidator"""

    def test_invalidate_property(self, mock_cache, invalidator):
        """Test invalidating all property caches"""
        # Set up cache entries
        mock_cache.set("property:detail:prop123", {"id": "prop123"})
        mock_cache.set("property:score:prop123", {"score": 85})
        mock_cache.set("property:timeline:prop123", [])
        mock_cache.set("properties:list:tenant1:hash1", [{"id": "prop123"}])
        mock_cache.set("properties:list:tenant1:hash2", [{"id": "prop123"}])

        # Invalidate property
        deleted = invalidator.invalidate_property("prop123")
        assert deleted >= 3  # At least detail, score, timeline

        # Check property-specific caches are gone
        assert mock_cache.get("property:detail:prop123") is None
        assert mock_cache.get("property:score:prop123") is None
        assert mock_cache.get("property:timeline:prop123") is None

        # Check list caches are also invalidated
        assert mock_cache.get("properties:list:tenant1:hash1") is None
        assert mock_cache.get("properties:list:tenant1:hash2") is None

    def test_invalidate_property_list(self, mock_cache, invalidator):
        """Test invalidating property list caches for tenant"""
        # Set up cache entries
        mock_cache.set("properties:list:tenant1:hash1", [{"id": "prop1"}])
        mock_cache.set("properties:list:tenant1:hash2", [{"id": "prop2"}])
        mock_cache.set("properties:list:tenant2:hash1", [{"id": "prop3"}])

        # Invalidate tenant1 lists
        deleted = invalidator.invalidate_property_list("tenant1")
        assert deleted == 2

        # Check tenant1 caches are gone
        assert mock_cache.get("properties:list:tenant1:hash1") is None
        assert mock_cache.get("properties:list:tenant1:hash2") is None

        # Check tenant2 cache still exists
        assert mock_cache.get("properties:list:tenant2:hash1") is not None

    def test_invalidate_property_score(self, mock_cache, invalidator):
        """Test invalidating property score cache"""
        # Set up cache entries
        mock_cache.set("property:score:prop123", {"score": 85})
        mock_cache.set("property:detail:prop123", {"id": "prop123", "score": 85})

        # Invalidate score
        deleted = invalidator.invalidate_property_score("prop123")
        assert deleted == 2  # Score + detail

        # Check caches are gone
        assert mock_cache.get("property:score:prop123") is None
        assert mock_cache.get("property:detail:prop123") is None

    def test_invalidate_timeline(self, mock_cache, invalidator):
        """Test invalidating timeline cache"""
        # Set up cache entry
        mock_cache.set("property:timeline:prop123", [{"event": "created"}])

        # Invalidate timeline
        deleted = invalidator.invalidate_timeline("prop123")
        assert deleted == 1

        # Check cache is gone
        assert mock_cache.get("property:timeline:prop123") is None

    def test_invalidate_tenant(self, mock_cache, invalidator):
        """Test invalidating all tenant caches"""
        # Set up cache entries with tenant ID
        mock_cache.set("properties:list:tenant1:hash1", [])
        mock_cache.set("property:detail:prop1:tenant1", {})
        mock_cache.set("other:tenant1:data", {})
        mock_cache.set("properties:list:tenant2:hash1", [])  # Different tenant

        # Invalidate tenant1
        deleted = invalidator.invalidate_tenant("tenant1")
        assert deleted >= 3

        # Check tenant1 caches are gone
        assert mock_cache.get("properties:list:tenant1:hash1") is None
        assert mock_cache.get("property:detail:prop1:tenant1") is None
        assert mock_cache.get("other:tenant1:data") is None

        # Check tenant2 cache still exists
        assert mock_cache.get("properties:list:tenant2:hash1") is not None

    def test_invalidate_all(self, mock_cache, invalidator):
        """Test invalidating all caches"""
        # Set up multiple cache entries
        mock_cache.set("key1", "value1")
        mock_cache.set("key2", "value2")
        mock_cache.set("key3", "value3")

        # Invalidate all
        result = invalidator.invalidate_all()
        assert result is True

        # Check all caches are gone
        assert mock_cache.get("key1") is None
        assert mock_cache.get("key2") is None
        assert mock_cache.get("key3") is None

    def test_get_cache_invalidator_singleton(self, mock_cache):
        """Test global invalidator singleton"""
        inv1 = get_cache_invalidator()
        inv2 = get_cache_invalidator()

        # Should be the same instance
        assert inv1 is inv2


class TestConvenienceFunctions:
    """Tests for convenience invalidation functions"""

    def test_invalidate_property_function(self, mock_cache):
        """Test invalidate_property convenience function"""
        mock_cache.set("property:detail:prop123", {})
        mock_cache.set("property:score:prop123", {})

        deleted = invalidate_property("prop123")
        assert deleted >= 2

        assert mock_cache.get("property:detail:prop123") is None
        assert mock_cache.get("property:score:prop123") is None

    def test_invalidate_property_list_function(self, mock_cache):
        """Test invalidate_property_list convenience function"""
        mock_cache.set("properties:list:tenant1:hash1", [])
        mock_cache.set("properties:list:tenant1:hash2", [])

        deleted = invalidate_property_list("tenant1")
        assert deleted == 2

    def test_invalidate_property_score_function(self, mock_cache):
        """Test invalidate_property_score convenience function"""
        mock_cache.set("property:score:prop123", {})
        mock_cache.set("property:detail:prop123", {})

        deleted = invalidate_property_score("prop123")
        assert deleted == 2

    def test_invalidate_timeline_function(self, mock_cache):
        """Test invalidate_timeline convenience function"""
        mock_cache.set("property:timeline:prop123", [])

        deleted = invalidate_timeline("prop123")
        assert deleted == 1

    def test_invalidate_tenant_function(self, mock_cache):
        """Test invalidate_tenant convenience function"""
        mock_cache.set("tenant1:data", {})

        deleted = invalidate_tenant("tenant1")
        assert deleted >= 1

    def test_invalidate_all_function(self, mock_cache):
        """Test invalidate_all convenience function"""
        mock_cache.set("key1", "value1")
        mock_cache.set("key2", "value2")

        result = invalidate_all()
        assert result is True


class TestInvalidationStrategies:
    """Tests for invalidation strategies"""

    def test_property_update_strategy(self, mock_cache):
        """Test property update strategy"""
        strategy = PropertyUpdateStrategy()

        # Should invalidate for property events
        assert strategy.should_invalidate({"type": "property.created"}) is True
        assert strategy.should_invalidate({"type": "property.updated"}) is True
        assert strategy.should_invalidate({"type": "property.deleted"}) is True
        assert strategy.should_invalidate({"type": "property.state_changed"}) is True

        # Should not invalidate for other events
        assert strategy.should_invalidate({"type": "score.calculated"}) is False

        # Test invalidation
        mock_cache.set("property:detail:prop123", {})
        mock_cache.set("property:score:prop123", {})

        deleted = strategy.invalidate({"type": "property.updated", "property_id": "prop123"})
        assert deleted >= 2

    def test_score_update_strategy(self, mock_cache):
        """Test score update strategy"""
        strategy = ScoreUpdateStrategy()

        # Should invalidate for score events
        assert strategy.should_invalidate({"type": "score.calculated"}) is True
        assert strategy.should_invalidate({"type": "score.updated"}) is True

        # Should not invalidate for other events
        assert strategy.should_invalidate({"type": "property.updated"}) is False

        # Test invalidation
        mock_cache.set("property:score:prop123", {})

        deleted = strategy.invalidate({"type": "score.calculated", "property_id": "prop123"})
        assert deleted >= 1

    def test_timeline_update_strategy(self, mock_cache):
        """Test timeline update strategy"""
        strategy = TimelineUpdateStrategy()

        # Should invalidate for timeline events
        assert strategy.should_invalidate({"type": "timeline.comment_added"}) is True
        assert strategy.should_invalidate({"type": "timeline.note_added"}) is True
        assert strategy.should_invalidate({"type": "timeline.event_added"}) is True

        # Should not invalidate for other events
        assert strategy.should_invalidate({"type": "property.updated"}) is False

        # Test invalidation
        mock_cache.set("property:timeline:prop123", [])

        deleted = strategy.invalidate({"type": "timeline.comment_added", "property_id": "prop123"})
        assert deleted >= 1


class TestEventDrivenInvalidator:
    """Tests for event-driven invalidator"""

    def test_event_driven_invalidator(self, mock_cache):
        """Test event-driven invalidator"""
        invalidator = EventDrivenInvalidator()

        # Set up cache
        mock_cache.set("property:detail:prop123", {})
        mock_cache.set("property:score:prop123", {})
        mock_cache.set("property:timeline:prop123", [])

        # Handle property update event
        deleted = invalidator.handle_event({
            "type": "property.updated",
            "property_id": "prop123",
        })
        assert deleted >= 2

        # Check property caches are invalidated
        assert mock_cache.get("property:detail:prop123") is None

    def test_event_driven_invalidator_multiple_strategies(self, mock_cache):
        """Test event-driven invalidator with multiple matching strategies"""
        invalidator = EventDrivenInvalidator()

        # Set up cache
        mock_cache.set("property:score:prop123", {})
        mock_cache.set("property:detail:prop123", {})

        # Score update event should trigger score strategy
        deleted = invalidator.handle_event({
            "type": "score.calculated",
            "property_id": "prop123",
        })
        assert deleted >= 1

    def test_event_driven_invalidator_no_match(self, mock_cache):
        """Test event-driven invalidator with no matching strategy"""
        invalidator = EventDrivenInvalidator()

        # Unknown event type
        deleted = invalidator.handle_event({
            "type": "unknown.event",
            "property_id": "prop123",
        })
        assert deleted == 0

    def test_event_driven_invalidator_custom_strategy(self, mock_cache):
        """Test adding custom strategy to event-driven invalidator"""
        from cache.invalidation import InvalidationStrategy

        class CustomStrategy(InvalidationStrategy):
            def should_invalidate(self, event: dict) -> bool:
                return event.get("type") == "custom.event"

            def invalidate(self, event: dict) -> int:
                mock_cache.delete("custom:key")
                return 1

        invalidator = EventDrivenInvalidator()
        invalidator.add_strategy(CustomStrategy())

        # Set up cache
        mock_cache.set("custom:key", "value")

        # Handle custom event
        deleted = invalidator.handle_event({
            "type": "custom.event",
        })
        assert deleted == 1
        assert mock_cache.get("custom:key") is None

    def test_handle_cache_event_function(self, mock_cache):
        """Test handle_cache_event convenience function"""
        mock_cache.set("property:detail:prop123", {})

        deleted = handle_cache_event({
            "type": "property.updated",
            "property_id": "prop123",
        })
        assert deleted >= 1
