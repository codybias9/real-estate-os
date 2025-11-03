"""
Redis Caching Layer
Cache GET endpoints to reduce database load
"""
import os
import json
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
import redis
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# ============================================================================
# REDIS CONNECTION
# ============================================================================

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    # Test connection
    redis_client.ping()
    logger.info("Cache Redis connection established")
except Exception as e:
    logger.warning(f"Caching disabled - Redis not available: {str(e)}")
    redis_client = None
    CACHE_ENABLED = False

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "300"))  # 5 minutes

# Cache TTLs for different types of data
CACHE_TTLS = {
    "properties_list": 60,  # 1 minute
    "property_detail": 300,  # 5 minutes
    "property_timeline": 60,  # 1 minute
    "templates": 600,  # 10 minutes
    "pipeline_stats": 120,  # 2 minutes
    "portfolio_metrics": 600,  # 10 minutes
    "investors": 300,  # 5 minutes
    "deal_rooms": 180,  # 3 minutes
    "open_data_sources": 3600,  # 1 hour
}

# ============================================================================
# CACHE KEY GENERATION
# ============================================================================

def generate_cache_key(prefix: str, **params) -> str:
    """
    Generate cache key from prefix and parameters

    Args:
        prefix: Cache key prefix (e.g., "properties", "property_detail")
        **params: Key-value pairs to include in cache key

    Returns:
        Cache key string

    Example:
        generate_cache_key("properties", team_id=1, stage="new")
        -> "cache:properties:team_id=1:stage=new"
    """
    # Sort params for consistency
    sorted_params = sorted(params.items())

    # Build key parts
    parts = [prefix]
    for key, value in sorted_params:
        if value is not None:
            parts.append(f"{key}={value}")

    key = ":".join(parts)
    return f"cache:{key}"


def generate_cache_key_hash(prefix: str, **params) -> str:
    """
    Generate a hashed cache key for complex parameters

    Useful when parameters are very long or contain complex objects

    Args:
        prefix: Cache key prefix
        **params: Parameters to hash

    Returns:
        Hashed cache key
    """
    # Serialize params to JSON and hash
    params_json = json.dumps(params, sort_keys=True, default=str)
    params_hash = hashlib.md5(params_json.encode()).hexdigest()

    return f"cache:{prefix}:{params_hash}"


# ============================================================================
# CACHE OPERATIONS
# ============================================================================

def cache_get(key: str) -> Optional[Any]:
    """
    Get value from cache

    Args:
        key: Cache key

    Returns:
        Cached value (deserialized from JSON) or None
    """
    if not CACHE_ENABLED or not redis_client:
        return None

    try:
        value = redis_client.get(key)
        if value:
            logger.debug(f"Cache hit: {key}")
            return json.loads(value)
        else:
            logger.debug(f"Cache miss: {key}")
            return None
    except Exception as e:
        logger.error(f"Cache get error for {key}: {str(e)}")
        return None


def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    """
    Set value in cache

    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time to live in seconds

    Returns:
        True if successful
    """
    if not CACHE_ENABLED or not redis_client:
        return False

    try:
        serialized = json.dumps(value, default=str)
        redis_client.setex(key, ttl, serialized)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.error(f"Cache set error for {key}: {str(e)}")
        return False


def cache_delete(key: str) -> bool:
    """
    Delete key from cache

    Args:
        key: Cache key

    Returns:
        True if deleted
    """
    if not CACHE_ENABLED or not redis_client:
        return False

    try:
        result = redis_client.delete(key)
        logger.debug(f"Cache delete: {key}")
        return result > 0
    except Exception as e:
        logger.error(f"Cache delete error for {key}: {str(e)}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching pattern

    Args:
        pattern: Redis pattern (e.g., "cache:properties:*")

    Returns:
        Number of keys deleted
    """
    if not CACHE_ENABLED or not redis_client:
        return 0

    try:
        keys = redis_client.keys(pattern)
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"Cache pattern delete: {pattern} ({deleted} keys)")
            return deleted
        return 0
    except Exception as e:
        logger.error(f"Cache pattern delete error for {pattern}: {str(e)}")
        return 0


# ============================================================================
# CACHE INVALIDATION
# ============================================================================

def invalidate_property_cache(property_id: int, team_id: int):
    """
    Invalidate all cache entries related to a property

    Called after property update/delete
    """
    patterns = [
        f"cache:property_detail:property_id={property_id}*",
        f"cache:property_timeline:property_id={property_id}*",
        f"cache:properties:team_id={team_id}*",  # Invalidate list cache
        f"cache:pipeline_stats:team_id={team_id}*"
    ]

    for pattern in patterns:
        cache_delete_pattern(pattern)


def invalidate_team_cache(team_id: int):
    """
    Invalidate all cache entries for a team

    Called after team-wide changes
    """
    cache_delete_pattern(f"cache:*team_id={team_id}*")


def invalidate_template_cache(team_id: int):
    """
    Invalidate template cache for a team
    """
    cache_delete_pattern(f"cache:templates:team_id={team_id}*")


# ============================================================================
# CACHE DECORATORS
# ============================================================================

def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorator to cache function results

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds (uses default if None)

    Usage:
        @cached("properties_list", ttl=60)
        def get_properties(team_id: int, stage: str):
            # Expensive database query
            return properties

    The function's arguments are automatically used as cache key parameters
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not CACHE_ENABLED:
                return func(*args, **kwargs)

            # Generate cache key from function arguments
            cache_params = {}

            # Get function signature
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Build cache key from arguments
            for param_name, param_value in bound_args.arguments.items():
                # Skip Session, Request, and other non-cacheable params
                if param_name in ['db', 'request', 'current_user']:
                    continue

                cache_params[param_name] = param_value

            # Generate cache key
            cache_key = generate_cache_key(prefix, **cache_params)

            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            cache_ttl = ttl or CACHE_TTLS.get(prefix, DEFAULT_TTL)
            cache_set(cache_key, result, cache_ttl)

            return result

        return wrapper
    return decorator


def cache_response(
    key_prefix: str,
    ttl: Optional[int] = None,
    vary_on: Optional[list] = None
):
    """
    Decorator specifically for FastAPI endpoints

    Args:
        key_prefix: Cache key prefix
        ttl: Time to live
        vary_on: List of parameter names to vary cache on

    Usage:
        @router.get("/properties")
        @cache_response("properties_list", ttl=60, vary_on=["team_id", "stage"])
        def list_properties(
            team_id: int,
            stage: Optional[str] = None,
            db: Session = Depends(get_db)
        ):
            return properties
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not CACHE_ENABLED:
                return await func(*args, **kwargs)

            # Build cache key
            cache_params = {}

            if vary_on:
                for param_name in vary_on:
                    if param_name in kwargs:
                        cache_params[param_name] = kwargs[param_name]

            cache_key = generate_cache_key(key_prefix, **cache_params)

            # Try cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute
            result = await func(*args, **kwargs)

            # Cache
            cache_ttl = ttl or CACHE_TTLS.get(key_prefix, DEFAULT_TTL)
            cache_set(cache_key, result, cache_ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not CACHE_ENABLED:
                return func(*args, **kwargs)

            # Build cache key
            cache_params = {}

            if vary_on:
                for param_name in vary_on:
                    if param_name in kwargs:
                        cache_params[param_name] = kwargs[param_name]

            cache_key = generate_cache_key(key_prefix, **cache_params)

            # Try cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute
            result = func(*args, **kwargs)

            # Cache
            cache_ttl = ttl or CACHE_TTLS.get(key_prefix, DEFAULT_TTL)
            cache_set(cache_key, result, cache_ttl)

            return result

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# CACHE WARMING
# ============================================================================

def warm_cache_for_team(team_id: int):
    """
    Pre-populate cache with common queries for a team

    Called when team logs in or at scheduled intervals
    """
    # This would call common endpoints to populate cache
    # Implementation depends on your usage patterns
    pass


# ============================================================================
# CACHE STATS
# ============================================================================

def get_cache_stats() -> dict:
    """
    Get cache statistics

    Returns:
        Dict with cache info
    """
    if not redis_client:
        return {"enabled": False}

    try:
        info = redis_client.info("stats")

        return {
            "enabled": True,
            "keys": redis_client.dbsize(),
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)),
            "memory_used": info.get("used_memory_human"),
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}")
        return {"enabled": True, "error": str(e)}


# ============================================================================
# CACHE + ETAG INTEGRATION
# ============================================================================

def cache_response_with_etag(
    key_prefix: str,
    ttl: Optional[int] = None,
    vary_on: Optional[list] = None
):
    """
    Decorator combining cache and ETag support

    Provides both server-side caching (Redis) and client-side caching (ETag)

    Args:
        key_prefix: Cache key prefix
        ttl: Time to live
        vary_on: List of parameter names to vary cache on

    Usage:
        @router.get("/properties")
        @cache_response_with_etag("properties_list", ttl=60, vary_on=["team_id", "stage"])
        def list_properties(
            request: Request,
            team_id: int,
            stage: Optional[str] = None,
            db: Session = Depends(get_db)
        ):
            return properties

    Flow:
    1. Check If-None-Match header (client-side cache) -> 304 if match
    2. Check Redis cache (server-side cache) -> return if hit
    3. Execute function and cache result
    4. Return with ETag header
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            from fastapi import Request
            from api.etag import generate_etag, check_etag_match
            from fastapi.responses import Response, JSONResponse

            if not CACHE_ENABLED:
                return await func(*args, **kwargs)

            # Find request in kwargs
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break

            # Build cache key
            cache_params = {}
            if vary_on:
                for param_name in vary_on:
                    if param_name in kwargs:
                        cache_params[param_name] = kwargs[param_name]

            cache_key = generate_cache_key(key_prefix, **cache_params)

            # Generate ETag from cache key (consistent across requests)
            etag = generate_etag(cache_key)

            # Check client-side cache (ETag)
            if request and check_etag_match(request, etag):
                logger.debug(f"ETag match - returning 304 for {cache_key}")
                return Response(status_code=304, headers={"ETag": etag})

            # Check server-side cache (Redis)
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return JSONResponse(content=cached_value, headers={"ETag": etag})

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            cache_ttl = ttl or CACHE_TTLS.get(key_prefix, DEFAULT_TTL)
            cache_set(cache_key, result, cache_ttl)

            # Return with ETag
            return JSONResponse(content=result, headers={"ETag": etag})

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            from fastapi import Request
            from api.etag import generate_etag, check_etag_match
            from fastapi.responses import Response, JSONResponse

            if not CACHE_ENABLED:
                return func(*args, **kwargs)

            # Find request in kwargs
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break

            # Build cache key
            cache_params = {}
            if vary_on:
                for param_name in vary_on:
                    if param_name in kwargs:
                        cache_params[param_name] = kwargs[param_name]

            cache_key = generate_cache_key(key_prefix, **cache_params)

            # Generate ETag from cache key
            etag = generate_etag(cache_key)

            # Check client-side cache (ETag)
            if request and check_etag_match(request, etag):
                logger.debug(f"ETag match - returning 304 for {cache_key}")
                return Response(status_code=304, headers={"ETag": etag})

            # Check server-side cache (Redis)
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return JSONResponse(content=cached_value, headers={"ETag": etag})

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            cache_ttl = ttl or CACHE_TTLS.get(key_prefix, DEFAULT_TTL)
            cache_set(cache_key, result, cache_ttl)

            # Return with ETag
            return JSONResponse(content=result, headers={"ETag": etag})

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
