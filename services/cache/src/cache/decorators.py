"""
Cache decorators for function memoization
"""

import functools
import hashlib
import json
from typing import Any, Callable, Optional

from .client import get_cache_client


def cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None,
):
    """
    Cache decorator for function memoization.

    Args:
        ttl: TTL in seconds (uses client default if not provided)
        key_prefix: Custom prefix for cache key (uses function name if not provided)
        key_builder: Custom function to build cache key from args/kwargs

    Usage:
        @cached(ttl=300, key_prefix="user")
        def get_user(user_id: str):
            return fetch_user_from_db(user_id)

        # With custom key builder
        @cached(key_builder=lambda user_id, tenant_id: f"{tenant_id}:{user_id}")
        def get_user(user_id: str, tenant_id: str):
            return fetch_user_from_db(user_id, tenant_id)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache = get_cache_client()

            # Build cache key
            if key_builder:
                # Use custom key builder
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default: hash function name + args + kwargs
                prefix = key_prefix or func.__name__
                key_data = {
                    "args": args,
                    "kwargs": kwargs,
                }
                key_hash = hashlib.md5(
                    json.dumps(key_data, sort_keys=True, default=str).encode()
                ).hexdigest()
                cache_key = f"{prefix}:{key_hash}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Compute value
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, ttl=ttl)

            return result

        # Add cache control methods
        wrapper.cache_clear = lambda: get_cache_client().delete_pattern(
            f"{key_prefix or func.__name__}:*"
        )
        wrapper.cache_key = lambda *args, **kwargs: (
            key_builder(*args, **kwargs)
            if key_builder
            else f"{key_prefix or func.__name__}:{hashlib.md5(json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str).encode()).hexdigest()}"
        )

        return wrapper

    return decorator


def cached_property_list(tenant_id: str, filters: dict = None):
    """
    Build cache key for property list query.

    Args:
        tenant_id: Tenant ID
        filters: Query filters

    Returns:
        Cache key string
    """
    filters_str = json.dumps(filters or {}, sort_keys=True)
    filters_hash = hashlib.md5(filters_str.encode()).hexdigest()
    return f"properties:list:{tenant_id}:{filters_hash}"


def cached_property_detail(property_id: str):
    """
    Build cache key for property detail.

    Args:
        property_id: Property ID

    Returns:
        Cache key string
    """
    return f"property:detail:{property_id}"


def cached_property_score(property_id: str):
    """
    Build cache key for property score.

    Args:
        property_id: Property ID

    Returns:
        Cache key string
    """
    return f"property:score:{property_id}"


def cached_timeline(property_id: str):
    """
    Build cache key for property timeline.

    Args:
        property_id: Property ID

    Returns:
        Cache key string
    """
    return f"property:timeline:{property_id}"


def cache_aside(
    cache_key: str,
    fetch_func: Callable,
    ttl: Optional[int] = None,
):
    """
    Cache-aside pattern implementation.

    Args:
        cache_key: Cache key
        fetch_func: Function to fetch data if not in cache
        ttl: TTL in seconds

    Returns:
        Cached or freshly fetched data

    Usage:
        user = cache_aside(
            cache_key=f"user:{user_id}",
            fetch_func=lambda: fetch_user_from_db(user_id),
            ttl=300,
        )
    """
    cache = get_cache_client()

    # Try cache first
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        return cached_value

    # Fetch from source
    result = fetch_func()

    # Store in cache
    cache.set(cache_key, result, ttl=ttl)

    return result


def cache_through(
    cache_key: str,
    value: Any,
    persist_func: Callable,
    ttl: Optional[int] = None,
):
    """
    Cache-through (write-through) pattern implementation.

    Args:
        cache_key: Cache key
        value: Value to write
        persist_func: Function to persist data to source
        ttl: TTL in seconds

    Returns:
        The persisted value

    Usage:
        user = cache_through(
            cache_key=f"user:{user_id}",
            value=user_data,
            persist_func=lambda: save_user_to_db(user_data),
            ttl=300,
        )
    """
    cache = get_cache_client()

    # Persist to source
    result = persist_func()

    # Update cache
    cache.set(cache_key, result, ttl=ttl)

    return result
