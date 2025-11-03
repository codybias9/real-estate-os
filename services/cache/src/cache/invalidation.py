"""
Cache invalidation strategies
"""

from typing import List, Optional

from .client import get_cache_client


class CacheInvalidator:
    """
    Cache invalidation manager.

    Provides strategies for invalidating cache entries
    when data changes.
    """

    def __init__(self):
        self.cache = get_cache_client()

    def invalidate_property(self, property_id: str) -> int:
        """
        Invalidate all cache entries for a property.

        Args:
            property_id: Property ID

        Returns:
            Number of keys deleted
        """
        deleted = 0

        # Delete property detail
        deleted += 1 if self.cache.delete(f"property:detail:{property_id}") else 0

        # Delete property score
        deleted += 1 if self.cache.delete(f"property:score:{property_id}") else 0

        # Delete property timeline
        deleted += 1 if self.cache.delete(f"property:timeline:{property_id}") else 0

        # Delete property list caches (all tenant queries)
        deleted += self.cache.delete_pattern("properties:list:*")

        return deleted

    def invalidate_property_list(self, tenant_id: str) -> int:
        """
        Invalidate property list caches for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Number of keys deleted
        """
        return self.cache.delete_pattern(f"properties:list:{tenant_id}:*")

    def invalidate_property_score(self, property_id: str) -> int:
        """
        Invalidate property score cache.

        Args:
            property_id: Property ID

        Returns:
            Number of keys deleted
        """
        deleted = 0
        deleted += 1 if self.cache.delete(f"property:score:{property_id}") else 0
        # Also invalidate detail since it may include score
        deleted += 1 if self.cache.delete(f"property:detail:{property_id}") else 0
        return deleted

    def invalidate_timeline(self, property_id: str) -> int:
        """
        Invalidate timeline cache.

        Args:
            property_id: Property ID

        Returns:
            Number of keys deleted
        """
        return 1 if self.cache.delete(f"property:timeline:{property_id}") else 0

    def invalidate_tenant(self, tenant_id: str) -> int:
        """
        Invalidate all cache entries for a tenant.

        Use with caution - this is expensive!

        Args:
            tenant_id: Tenant ID

        Returns:
            Number of keys deleted
        """
        # This is a broad invalidation - use sparingly
        return self.cache.delete_pattern(f"*{tenant_id}*")

    def invalidate_all(self) -> bool:
        """
        Invalidate all cache entries.

        Use with extreme caution - only for maintenance!

        Returns:
            True if successful
        """
        return self.cache.flush()


# Global invalidator instance
_invalidator: Optional[CacheInvalidator] = None


def get_cache_invalidator() -> CacheInvalidator:
    """
    Get global cache invalidator instance.

    Returns:
        CacheInvalidator instance
    """
    global _invalidator

    if _invalidator is None:
        _invalidator = CacheInvalidator()

    return _invalidator


# Convenience functions
def invalidate_property(property_id: str) -> int:
    """Invalidate all cache entries for a property."""
    return get_cache_invalidator().invalidate_property(property_id)


def invalidate_property_list(tenant_id: str) -> int:
    """Invalidate property list caches for a tenant."""
    return get_cache_invalidator().invalidate_property_list(tenant_id)


def invalidate_property_score(property_id: str) -> int:
    """Invalidate property score cache."""
    return get_cache_invalidator().invalidate_property_score(property_id)


def invalidate_timeline(property_id: str) -> int:
    """Invalidate timeline cache."""
    return get_cache_invalidator().invalidate_timeline(property_id)


def invalidate_tenant(tenant_id: str) -> int:
    """Invalidate all cache entries for a tenant."""
    return get_cache_invalidator().invalidate_tenant(tenant_id)


def invalidate_all() -> bool:
    """Invalidate all cache entries."""
    return get_cache_invalidator().invalidate_all()


class InvalidationStrategy:
    """
    Base class for invalidation strategies.

    Implement custom strategies by subclassing.
    """

    def should_invalidate(self, event: dict) -> bool:
        """
        Determine if cache should be invalidated for this event.

        Args:
            event: Event data

        Returns:
            True if cache should be invalidated
        """
        raise NotImplementedError

    def invalidate(self, event: dict) -> int:
        """
        Invalidate cache based on event.

        Args:
            event: Event data

        Returns:
            Number of keys deleted
        """
        raise NotImplementedError


class PropertyUpdateStrategy(InvalidationStrategy):
    """
    Invalidate cache when property is updated.
    """

    def should_invalidate(self, event: dict) -> bool:
        return event.get("type") in [
            "property.created",
            "property.updated",
            "property.deleted",
            "property.state_changed",
        ]

    def invalidate(self, event: dict) -> int:
        property_id = event.get("property_id")
        if not property_id:
            return 0

        return invalidate_property(property_id)


class ScoreUpdateStrategy(InvalidationStrategy):
    """
    Invalidate cache when score is updated.
    """

    def should_invalidate(self, event: dict) -> bool:
        return event.get("type") in ["score.calculated", "score.updated"]

    def invalidate(self, event: dict) -> int:
        property_id = event.get("property_id")
        if not property_id:
            return 0

        return invalidate_property_score(property_id)


class TimelineUpdateStrategy(InvalidationStrategy):
    """
    Invalidate cache when timeline is updated.
    """

    def should_invalidate(self, event: dict) -> bool:
        return event.get("type") in [
            "timeline.comment_added",
            "timeline.note_added",
            "timeline.event_added",
        ]

    def invalidate(self, event: dict) -> int:
        property_id = event.get("property_id")
        if not property_id:
            return 0

        return invalidate_timeline(property_id)


class EventDrivenInvalidator:
    """
    Event-driven cache invalidator.

    Listens to domain events and invalidates cache accordingly.
    """

    def __init__(self):
        self.strategies: List[InvalidationStrategy] = [
            PropertyUpdateStrategy(),
            ScoreUpdateStrategy(),
            TimelineUpdateStrategy(),
        ]

    def add_strategy(self, strategy: InvalidationStrategy):
        """Add custom invalidation strategy."""
        self.strategies.append(strategy)

    def handle_event(self, event: dict) -> int:
        """
        Handle domain event and invalidate cache if needed.

        Args:
            event: Domain event

        Returns:
            Total number of keys deleted
        """
        total_deleted = 0

        for strategy in self.strategies:
            if strategy.should_invalidate(event):
                deleted = strategy.invalidate(event)
                total_deleted += deleted

        return total_deleted


# Global event-driven invalidator
_event_invalidator: Optional[EventDrivenInvalidator] = None


def get_event_invalidator() -> EventDrivenInvalidator:
    """
    Get global event-driven invalidator.

    Returns:
        EventDrivenInvalidator instance
    """
    global _event_invalidator

    if _event_invalidator is None:
        _event_invalidator = EventDrivenInvalidator()

    return _event_invalidator


def handle_cache_event(event: dict) -> int:
    """
    Handle domain event for cache invalidation.

    Usage:
        # In your event handler
        handle_cache_event({
            "type": "property.updated",
            "property_id": "123",
        })

    Args:
        event: Domain event

    Returns:
        Number of keys invalidated
    """
    return get_event_invalidator().handle_event(event)
