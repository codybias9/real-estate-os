"""
Cache Service

Redis-based caching with decorators, TTL, and invalidation strategies.
"""

from .client import CacheClient, get_cache_client
from .decorators import (
    cached,
    cached_property_list,
    cached_property_detail,
    cached_property_score,
    cached_timeline,
    cache_aside,
    cache_through,
)
from .invalidation import (
    CacheInvalidator,
    get_cache_invalidator,
    invalidate_property,
    invalidate_property_list,
    invalidate_property_score,
    invalidate_timeline,
    invalidate_tenant,
    invalidate_all,
    handle_cache_event,
    EventDrivenInvalidator,
    get_event_invalidator,
)

__all__ = [
    "CacheClient",
    "get_cache_client",
    "cached",
    "cached_property_list",
    "cached_property_detail",
    "cached_property_score",
    "cached_timeline",
    "cache_aside",
    "cache_through",
    "CacheInvalidator",
    "get_cache_invalidator",
    "invalidate_property",
    "invalidate_property_list",
    "invalidate_property_score",
    "invalidate_timeline",
    "invalidate_tenant",
    "invalidate_all",
    "handle_cache_event",
    "EventDrivenInvalidator",
    "get_event_invalidator",
]
