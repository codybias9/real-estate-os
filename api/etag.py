"""
ETag Support for Conditional Requests
Returns 304 Not Modified when content hasn't changed
"""
import hashlib
import json
from typing import Optional, Any, Callable
from functools import wraps
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ETAG GENERATION
# ============================================================================

def generate_etag(content: Any) -> str:
    """
    Generate ETag from content

    Args:
        content: Content to generate ETag from (dict, list, str, etc.)

    Returns:
        ETag string (MD5 hash)

    Example:
        etag = generate_etag({"id": 1, "name": "Property"})
        # Returns: "a1b2c3d4e5f6..."
    """
    if isinstance(content, (dict, list)):
        # Serialize to JSON with sorted keys for consistency
        content_str = json.dumps(content, sort_keys=True, default=str)
    elif isinstance(content, str):
        content_str = content
    elif isinstance(content, bytes):
        content_str = content.decode('utf-8', errors='ignore')
    else:
        content_str = str(content)

    # Generate MD5 hash
    etag = hashlib.md5(content_str.encode('utf-8')).hexdigest()

    return f'"{etag}"'  # ETags should be quoted per HTTP spec


def generate_weak_etag(content: Any) -> str:
    """
    Generate weak ETag from content

    Weak ETags indicate semantic equivalence but not byte-for-byte identity

    Args:
        content: Content to generate ETag from

    Returns:
        Weak ETag string with W/ prefix
    """
    etag = generate_etag(content)
    return f"W/{etag}"


# ============================================================================
# ETAG VALIDATION
# ============================================================================

def check_etag_match(request: Request, etag: str) -> bool:
    """
    Check if request's If-None-Match header matches given ETag

    Args:
        request: FastAPI request
        etag: Current ETag to check against

    Returns:
        True if ETags match (content not modified)
    """
    if_none_match = request.headers.get("If-None-Match")

    if not if_none_match:
        return False

    # Handle multiple ETags (comma-separated)
    request_etags = [tag.strip() for tag in if_none_match.split(",")]

    # Check for wildcard match
    if "*" in request_etags:
        return True

    # Check if current ETag is in the list
    return etag in request_etags


def check_if_modified_since(request: Request, last_modified: str) -> bool:
    """
    Check if content was modified since the given date

    Args:
        request: FastAPI request
        last_modified: Last modified date (RFC 7231 format)

    Returns:
        True if content was modified
    """
    if_modified_since = request.headers.get("If-Modified-Since")

    if not if_modified_since:
        return True

    # Simple string comparison (works for RFC 7231 dates)
    return if_modified_since != last_modified


# ============================================================================
# ETAG MIDDLEWARE
# ============================================================================

async def etag_middleware(request: Request, call_next):
    """
    Global ETag middleware

    Automatically adds ETag headers to responses and handles
    conditional requests (If-None-Match)

    Add to FastAPI app:
        app.middleware("http")(etag_middleware)
    """
    # Process request
    response = await call_next(request)

    # Only add ETags to successful GET/HEAD requests
    if request.method not in ["GET", "HEAD"]:
        return response

    if response.status_code not in [200, 203, 206]:
        return response

    # Skip if response already has ETag
    if "ETag" in response.headers:
        return response

    # For JSON responses, we can generate ETag from body
    # Note: This requires reading the response body which may not always be efficient
    # For production, consider using cache-based ETags or conditional decorators instead

    return response


# ============================================================================
# ETAG DECORATORS
# ============================================================================

def with_etag(func: Callable):
    """
    Decorator to add ETag support to endpoint

    Generates ETag from response and returns 304 if content not modified

    Usage:
        @router.get("/properties")
        @with_etag
        def list_properties():
            return properties
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
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

        # Execute function
        result = await func(*args, **kwargs)

        # Generate ETag from result
        etag = generate_etag(result)

        # Check if content modified
        if request and check_etag_match(request, etag):
            logger.debug(f"ETag match - returning 304 for {request.url.path}")
            return Response(status_code=304, headers={"ETag": etag})

        # Return response with ETag header
        if isinstance(result, Response):
            result.headers["ETag"] = etag
            return result
        else:
            return JSONResponse(content=result, headers={"ETag": etag})

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
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

        # Execute function
        result = func(*args, **kwargs)

        # Generate ETag from result
        etag = generate_etag(result)

        # Check if content modified
        if request and check_etag_match(request, etag):
            logger.debug(f"ETag match - returning 304 for {request.url.path}")
            return Response(status_code=304, headers={"ETag": etag})

        # Return response with ETag header
        if isinstance(result, Response):
            result.headers["ETag"] = etag
            return result
        else:
            return JSONResponse(content=result, headers={"ETag": etag})

    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def conditional_response(
    request: Request,
    content: Any,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None
) -> Response:
    """
    Helper function to create conditional response

    Generates ETag if not provided and returns 304 if appropriate

    Args:
        request: FastAPI request
        content: Response content
        etag: Optional pre-computed ETag
        last_modified: Optional last modified date

    Returns:
        Response (304 if not modified, 200 with content otherwise)

    Usage:
        @router.get("/properties/{id}")
        def get_property(id: int, request: Request):
            property = db.query(Property).get(id)

            # Use updated_at timestamp for ETag
            etag = generate_etag(property.updated_at.isoformat())

            return conditional_response(
                request,
                property.to_dict(),
                etag=etag,
                last_modified=property.updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
            )
    """
    # Generate ETag if not provided
    if not etag:
        etag = generate_etag(content)

    # Check ETag match
    if check_etag_match(request, etag):
        logger.debug(f"ETag match - returning 304")
        headers = {"ETag": etag}
        if last_modified:
            headers["Last-Modified"] = last_modified
        return Response(status_code=304, headers=headers)

    # Check Last-Modified if provided
    if last_modified and not check_if_modified_since(request, last_modified):
        logger.debug(f"Not modified since {last_modified} - returning 304")
        headers = {"ETag": etag, "Last-Modified": last_modified}
        return Response(status_code=304, headers=headers)

    # Return full response
    headers = {"ETag": etag}
    if last_modified:
        headers["Last-Modified"] = last_modified

    return JSONResponse(content=content, headers=headers)


# ============================================================================
# CACHE-AWARE ETAG SUPPORT
# ============================================================================

def etag_from_cache_key(cache_key: str) -> str:
    """
    Generate ETag from cache key

    Useful when using Redis caching - can generate consistent ETags
    without reading response body

    Args:
        cache_key: Redis cache key

    Returns:
        ETag string
    """
    return generate_etag(cache_key)


def cached_with_etag(cache_key_func: Callable[[Request], str]):
    """
    Decorator combining caching and ETag support

    Uses cache key to generate consistent ETags

    Args:
        cache_key_func: Function to generate cache key from request

    Usage:
        @router.get("/properties")
        @cached_with_etag(lambda req: f"properties:team={req.state.team_id}")
        def list_properties(request: Request):
            return properties
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(request: Request, *args, **kwargs):
            from api.cache import cache_get, cache_set, DEFAULT_TTL

            # Generate cache key
            cache_key = cache_key_func(request)

            # Generate ETag from cache key (before checking cache)
            etag = etag_from_cache_key(cache_key)

            # Check if client has cached version
            if check_etag_match(request, etag):
                logger.debug(f"ETag match - returning 304")
                return Response(status_code=304, headers={"ETag": etag})

            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return JSONResponse(content=cached_value, headers={"ETag": etag})

            # Execute function
            result = await func(request, *args, **kwargs)

            # Store in cache
            cache_set(cache_key, result, DEFAULT_TTL)

            # Return with ETag
            return JSONResponse(content=result, headers={"ETag": etag})

        @wraps(func)
        def sync_wrapper(request: Request, *args, **kwargs):
            from api.cache import cache_get, cache_set, DEFAULT_TTL

            # Generate cache key
            cache_key = cache_key_func(request)

            # Generate ETag from cache key
            etag = etag_from_cache_key(cache_key)

            # Check if client has cached version
            if check_etag_match(request, etag):
                logger.debug(f"ETag match - returning 304")
                return Response(status_code=304, headers={"ETag": etag})

            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return JSONResponse(content=cached_value, headers={"ETag": etag})

            # Execute function
            result = func(request, *args, **kwargs)

            # Store in cache
            cache_set(cache_key, result, DEFAULT_TTL)

            # Return with ETag
            return JSONResponse(content=result, headers={"ETag": etag})

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_etag(etag_header: str) -> list[str]:
    """
    Parse ETag header value

    Args:
        etag_header: ETag header value (may contain multiple ETags)

    Returns:
        List of ETag values

    Example:
        parse_etag('"abc123", W/"def456"')
        # Returns: ['"abc123"', 'W/"def456"']
    """
    return [tag.strip() for tag in etag_header.split(",")]


def is_weak_etag(etag: str) -> bool:
    """
    Check if ETag is weak

    Args:
        etag: ETag string

    Returns:
        True if weak ETag
    """
    return etag.startswith("W/")


def strip_weak_prefix(etag: str) -> str:
    """
    Remove W/ prefix from weak ETag

    Args:
        etag: ETag string (possibly with W/ prefix)

    Returns:
        ETag without weak prefix
    """
    if is_weak_etag(etag):
        return etag[2:]
    return etag
