"""Cache decorators for easy caching"""

import functools
from typing import Callable
from .redis_client import CacheManager

def cached(key_prefix: str, ttl: int = 3600):
    """Decorator to cache function results"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheManager()
            # Build cache key from function args
            cache_key = f"{key_prefix}:{':'.join(map(str, args))}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

def invalidate_cache(key_pattern: str):
    """Decorator to invalidate cache after function execution"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            cache = CacheManager()
            cache.delete(key_pattern)
            return result
        return wrapper
    return decorator
