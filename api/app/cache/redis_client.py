"""Redis client and connection management"""

import os
import json
import redis
from typing import Optional, Any
from datetime import timedelta

# Redis connection pool
_redis_client: Optional[redis.Redis] = None

def get_redis() -> redis.Redis:
    """Get Redis client with connection pooling"""
    global _redis_client
    
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            max_connections=50
        )
    
    return _redis_client

class CacheManager:
    """Cache manager for provenance queries"""
    
    def __init__(self, redis_client: redis.Redis = None):
        self.redis = redis_client or get_redis()
        self.default_ttl = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache with TTL"""
        try:
            ttl = ttl or self.default_ttl
            self.redis.setex(key, ttl, json.dumps(value))
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def delete(self, pattern: str):
        """Delete keys matching pattern"""
        try:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
        except Exception as e:
            print(f"Cache delete error: {e}")
    
    def flush_tenant(self, tenant_id: str):
        """Flush all cache for a tenant"""
        self.delete(f"tenant:{tenant_id}:*")
