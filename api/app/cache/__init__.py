"""Redis caching layer for Real Estate OS

Provides:
- Redis connection pooling
- Read-through cache for provenance queries
- Cache invalidation on updates
- TTL management
"""

from .redis_client import get_redis, CacheManager
from .decorators import cached, invalidate_cache

__all__ = [
    'get_redis',
    'CacheManager',
    'cached',
    'invalidate_cache',
]
