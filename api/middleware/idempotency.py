"""Idempotency middleware for preventing duplicate requests."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime, timedelta
import json
import hashlib

from ..database import SessionLocal
from ..models import IdempotencyKey


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle idempotent requests using idempotency keys.

    Idempotency keys prevent duplicate requests from being processed multiple times.
    Clients can provide an 'Idempotency-Key' header with a unique identifier.
    If the same key is used within the expiration window, the cached response is returned.
    """

    def __init__(self, app, expire_hours: int = 24):
        """
        Initialize idempotency middleware.

        Args:
            app: FastAPI application
            expire_hours: How many hours to keep idempotency keys (default: 24)
        """
        super().__init__(app)
        self.expire_hours = expire_hours
        self.idempotent_methods = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        """Process request with idempotency check."""
        # Only apply to modifying methods
        if request.method not in self.idempotent_methods:
            return await call_next(request)

        # Get idempotency key from header
        idempotency_key = request.headers.get("Idempotency-Key")

        # If no key provided, process normally
        if not idempotency_key:
            return await call_next(request)

        # Get user ID from request state (set by auth dependency)
        user_id = getattr(request.state, "user_id", None)
        organization_id = getattr(request.state, "organization_id", None)

        # Check database for existing key
        db = SessionLocal()
        try:
            existing = db.query(IdempotencyKey).filter(
                IdempotencyKey.key == idempotency_key,
                IdempotencyKey.user_id == user_id,
                IdempotencyKey.expires_at > datetime.utcnow(),
            ).first()

            if existing:
                # Return cached response
                return JSONResponse(
                    status_code=existing.response_status,
                    content=json.loads(existing.response_body) if existing.response_body else {},
                    headers={"X-Idempotency-Replay": "true"},
                )

            # Read request body for storage
            body = await request.body()
            body_str = body.decode("utf-8") if body else ""

            # Process request
            response = await call_next(request)

            # Read response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # Store idempotency key
            expires_at = datetime.utcnow() + timedelta(hours=self.expire_hours)

            idempotency_record = IdempotencyKey(
                key=idempotency_key,
                organization_id=organization_id,
                user_id=user_id,
                request_path=str(request.url.path),
                request_method=request.method,
                request_body=body_str,
                response_status=response.status_code,
                response_body=response_body.decode("utf-8"),
                expires_at=expires_at,
            )

            db.add(idempotency_record)
            db.commit()

            # Return response with body
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        except Exception as e:
            # On error, process request normally
            print(f"Idempotency middleware error: {e}")
            return await call_next(request)

        finally:
            db.close()


def generate_idempotency_key(request_data: dict) -> str:
    """
    Generate an idempotency key from request data.

    Args:
        request_data: Request data to hash

    Returns:
        Idempotency key (SHA-256 hash)
    """
    data_str = json.dumps(request_data, sort_keys=True)
    return hashlib.sha256(data_str.encode()).hexdigest()
