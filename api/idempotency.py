"""
Idempotency Key Handler

Prevents duplicate processing of critical operations through idempotency keys.

Features:
- Client-provided or server-generated keys
- Response caching (returns same response for same key)
- TTL-based expiration (24 hours default)
- Supports POST, PUT, PATCH, DELETE
- Scoped to user/team
- Automatic cleanup of expired keys

Critical Operations (MUST use idempotency):
- Memo generation (POST /properties/{id}/memo)
- Outreach enqueue (POST /communications/send)
- Stage transitions (PATCH /properties/{id} with stage change)
- Timeline events (POST /properties/{id}/timeline)
- Payment processing (POST /payments)

Usage:
    @router.post("/properties")
    @require_idempotency
    def create_property(...):
        ...

    Or via dependency:
    def create_property(
        idempotency: IdempotencyHandler = Depends(get_idempotency_handler)
    ):
        ...
"""
import uuid
import logging
from typing import Optional, Any, Callable
from functools import wraps
from datetime import datetime, timedelta

from fastapi import Request, Response, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.database import get_db
from db.models import IdempotencyKey, User
from api.auth import get_current_user

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default TTL for idempotency keys (24 hours)
DEFAULT_TTL_HOURS = 24

# Header name for idempotency key
IDEMPOTENCY_HEADER = "Idempotency-Key"


# ============================================================================
# IDEMPOTENCY HANDLER
# ============================================================================

class IdempotencyHandler:
    """
    Handler for idempotency key management

    Provides:
    - Key extraction from headers or generation
    - Duplicate detection
    - Response caching
    - Automatic cleanup
    """

    def __init__(
        self,
        request: Request,
        db: Session,
        current_user: Optional[User] = None,
        ttl_hours: int = DEFAULT_TTL_HOURS
    ):
        self.request = request
        self.db = db
        self.current_user = current_user
        self.ttl_hours = ttl_hours

        # Endpoint identifier (set before _get_or_generate_key)
        self.endpoint = str(request.url.path)
        self.method = request.method

        # Extract key from header or generate (after method is set)
        self.key = self._get_or_generate_key()

    def _get_or_generate_key(self) -> str:
        """
        Get idempotency key from header or generate new one

        Returns:
            Idempotency key string
        """
        # Check header first
        key = self.request.headers.get(IDEMPOTENCY_HEADER)

        if key:
            return key

        # Generate key from request details
        # Format: {method}:{path}:{timestamp}:{random}
        path = self.request.url.path
        timestamp = int(datetime.utcnow().timestamp())
        random_suffix = str(uuid.uuid4())[:8]

        return f"{self.method}:{path}:{timestamp}:{random_suffix}"

    def check_existing(self) -> Optional[dict]:
        """
        Check if idempotency key already exists

        Returns:
            Cached response if exists, None otherwise
        """
        existing = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.idempotency_key == self.key,
            IdempotencyKey.endpoint == self.endpoint,
            IdempotencyKey.expires_at > datetime.utcnow()
        ).first()

        if existing:
            logger.info(
                f"Idempotency key hit: {self.key} for {self.endpoint}",
                extra={
                    "idempotency_key": self.key,
                    "endpoint": self.endpoint,
                    "cached_status": existing.response_status
                }
            )

            # Return cached response
            return {
                "status_code": existing.response_status,
                "body": existing.response_body,
                "cached": True,
                "created_at": existing.created_at.isoformat()
            }

        return None

    def store_response(
        self,
        status_code: int,
        response_body: Any,
        request_params: Optional[dict] = None
    ):
        """
        Store response for future idempotent requests

        Args:
            status_code: HTTP status code
            response_body: Response body (dict or serializable)
            request_params: Optional request parameters for debugging
        """
        try:
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(hours=self.ttl_hours)

            # Create idempotency record
            idempotency_record = IdempotencyKey(
                idempotency_key=self.key,
                endpoint=self.endpoint,
                request_method=self.method,
                request_params=request_params,
                response_status=status_code,
                response_body=response_body if isinstance(response_body, dict) else {"result": response_body},
                user_id=self.current_user.id if self.current_user else None,
                team_id=self.current_user.team_id if self.current_user else None,
                expires_at=expires_at
            )

            self.db.add(idempotency_record)
            self.db.commit()

            logger.info(
                f"Stored idempotency key: {self.key} for {self.endpoint}",
                extra={
                    "idempotency_key": self.key,
                    "endpoint": self.endpoint,
                    "status_code": status_code,
                    "expires_at": expires_at.isoformat()
                }
            )

        except IntegrityError:
            # Race condition: another request stored the key first
            # This is OK, the other request will handle it
            self.db.rollback()
            logger.warning(
                f"Race condition on idempotency key: {self.key}",
                extra={"idempotency_key": self.key, "endpoint": self.endpoint}
            )

        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Failed to store idempotency key: {str(e)}",
                extra={"idempotency_key": self.key, "endpoint": self.endpoint}
            )

    def cleanup_expired(self):
        """
        Clean up expired idempotency keys

        Should be called periodically (e.g., daily cron job)
        """
        deleted = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.expires_at < datetime.utcnow()
        ).delete()

        self.db.commit()

        logger.info(f"Cleaned up {deleted} expired idempotency keys")

        return deleted


# ============================================================================
# FASTAPI DEPENDENCIES
# ============================================================================

def get_idempotency_handler(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> IdempotencyHandler:
    """
    FastAPI dependency for idempotency handling

    Usage:
        @router.post("/properties")
        def create_property(
            data: PropertyCreate,
            idempotency: IdempotencyHandler = Depends(get_idempotency_handler)
        ):
            # Check for existing
            existing = idempotency.check_existing()
            if existing:
                return JSONResponse(
                    content=existing["body"],
                    status_code=existing["status_code"]
                )

            # Process request
            result = ...

            # Store response
            idempotency.store_response(201, result)

            return result
    """
    return IdempotencyHandler(request, db, current_user)


# ============================================================================
# DECORATORS
# ============================================================================

def require_idempotency(
    ttl_hours: int = DEFAULT_TTL_HOURS,
    extract_params: bool = True
):
    """
    Decorator to require idempotency for an endpoint

    Automatically:
    - Checks for existing idempotency key
    - Returns cached response if exists
    - Stores new response after execution
    - Handles race conditions

    Args:
        ttl_hours: TTL for idempotency keys (default 24 hours)
        extract_params: Whether to store request params (default True)

    Usage:
        @router.post("/properties")
        @require_idempotency(ttl_hours=48)
        async def create_property(property_data: PropertyCreate):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract request, db, and user from kwargs
            request: Optional[Request] = None
            db: Optional[Session] = None
            current_user: Optional[User] = None

            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, Session):
                    db = arg
                elif isinstance(arg, User):
                    current_user = arg

            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                elif isinstance(value, Session):
                    db = value
                elif isinstance(value, User):
                    current_user = value

            if not request or not db:
                # Can't enforce idempotency without request and db
                logger.warning("Idempotency decorator missing request or db, skipping")
                return await func(*args, **kwargs)

            # Create idempotency handler
            handler = IdempotencyHandler(request, db, current_user, ttl_hours)

            # Check for existing
            existing = handler.check_existing()
            if existing:
                return JSONResponse(
                    content=existing["body"],
                    status_code=existing["status_code"],
                    headers={"X-Idempotency-Cached": "true"}
                )

            # Execute function
            result = await func(*args, **kwargs)

            # Extract status code and body from result
            if isinstance(result, Response):
                # FastAPI Response object
                status_code = result.status_code
                # Try to extract body (may not be available)
                body = None
            else:
                # Assume success and serialize result
                status_code = 200
                body = result

            # Store response
            params = {}
            if extract_params:
                # Extract request params (body, query, path)
                try:
                    if request.method in ["POST", "PUT", "PATCH"]:
                        body_bytes = await request.body()
                        import json
                        params = json.loads(body_bytes) if body_bytes else {}
                except:
                    pass

            handler.store_response(status_code, body, params)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract request, db, and user from kwargs
            request: Optional[Request] = None
            db: Optional[Session] = None
            current_user: Optional[User] = None

            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, Session):
                    db = arg
                elif isinstance(arg, User):
                    current_user = arg

            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                elif isinstance(value, Session):
                    db = value
                elif isinstance(value, User):
                    current_user = value

            if not request or not db:
                logger.warning("Idempotency decorator missing request or db, skipping")
                return func(*args, **kwargs)

            # Create idempotency handler
            handler = IdempotencyHandler(request, db, current_user, ttl_hours)

            # Check for existing
            existing = handler.check_existing()
            if existing:
                return JSONResponse(
                    content=existing["body"],
                    status_code=existing["status_code"],
                    headers={"X-Idempotency-Cached": "true"}
                )

            # Execute function
            result = func(*args, **kwargs)

            # Extract status code and body
            if isinstance(result, Response):
                status_code = result.status_code
                body = None
            else:
                status_code = 200
                body = result

            # Store response
            handler.store_response(status_code, body)

            return result

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# CLEANUP JOB
# ============================================================================

def cleanup_expired_idempotency_keys(db: Session) -> int:
    """
    Clean up expired idempotency keys

    Should be called periodically (e.g., daily Celery beat task)

    Args:
        db: Database session

    Returns:
        Number of keys deleted
    """
    deleted = db.query(IdempotencyKey).filter(
        IdempotencyKey.expires_at < datetime.utcnow()
    ).delete()

    db.commit()

    logger.info(f"Cleaned up {deleted} expired idempotency keys")

    return deleted
