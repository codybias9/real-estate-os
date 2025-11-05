"""Audit logging middleware."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import json

from ..database import SessionLocal
from ..models import AuditLog


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests and changes for audit purposes.

    Tracks:
    - User actions
    - Resource modifications
    - Request details
    - IP addresses
    """

    def __init__(self, app, log_read_operations: bool = False):
        """
        Initialize audit log middleware.

        Args:
            app: FastAPI application
            log_read_operations: Whether to log GET requests (default: False)
        """
        super().__init__(app)
        self.log_read_operations = log_read_operations
        self.logged_methods = {"POST", "PUT", "PATCH", "DELETE"}
        if log_read_operations:
            self.logged_methods.add("GET")

    async def dispatch(self, request: Request, call_next):
        """Process request with audit logging."""
        # Only log specified methods
        if request.method not in self.logged_methods:
            return await call_next(request)

        # Get request details
        user_id = getattr(request.state, "user_id", None)
        organization_id = getattr(request.state, "organization_id", None)
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")

        # Process request
        start_time = datetime.utcnow()
        response = await call_next(request)
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Only log successful operations (2xx status codes)
        if 200 <= response.status_code < 300:
            # Extract action and resource from path
            action, resource_type, resource_id = self._parse_request_path(
                request.url.path, request.method
            )

            # Log to database asynchronously
            self._create_audit_log(
                organization_id=organization_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=str(request.url.path),
                request_method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.

        Args:
            request: FastAPI request

        Returns:
            Client IP address
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _parse_request_path(
        self, path: str, method: str
    ) -> tuple[str, str, int | None]:
        """
        Parse request path to extract action, resource type, and ID.

        Args:
            path: Request URL path
            method: HTTP method

        Returns:
            Tuple of (action, resource_type, resource_id)
        """
        parts = path.strip("/").split("/")

        # Default action based on method
        action_map = {
            "POST": "create",
            "GET": "read",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        action = action_map.get(method, "unknown")

        # Extract resource type
        resource_type = "unknown"
        resource_id = None

        # Parse path (e.g., /api/v1/properties/123)
        if len(parts) >= 3:
            resource_type = parts[2]  # e.g., "properties"

            # Extract ID if present
            if len(parts) >= 4 and parts[3].isdigit():
                resource_id = int(parts[3])

        return action, resource_type, resource_id

    def _create_audit_log(
        self,
        organization_id: int | None,
        user_id: int | None,
        action: str,
        resource_type: str,
        resource_id: int | None,
        ip_address: str,
        user_agent: str,
        request_path: str,
        request_method: str,
        status_code: int,
        duration_ms: float,
    ):
        """
        Create audit log entry in database.

        Args:
            organization_id: Organization ID
            user_id: User ID
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource ID
            ip_address: Client IP address
            user_agent: User agent string
            request_path: Request path
            request_method: HTTP method
            status_code: Response status code
            duration_ms: Request duration in milliseconds
        """
        db = SessionLocal()

        try:
            metadata = {
                "request_path": request_path,
                "request_method": request_method,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }

            audit_log = AuditLog(
                organization_id=organization_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=json.dumps(metadata),
            )

            db.add(audit_log)
            db.commit()

        except Exception as e:
            print(f"Audit log creation error: {e}")
            db.rollback()

        finally:
            db.close()


def create_audit_log_entry(
    db,
    organization_id: int | None,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | None,
    changes: dict | None = None,
    metadata: dict | None = None,
):
    """
    Manually create an audit log entry.

    Args:
        db: Database session
        organization_id: Organization ID
        user_id: User ID
        action: Action performed
        resource_type: Type of resource
        resource_id: Resource ID
        changes: Dictionary of changes (before/after)
        metadata: Additional metadata
    """
    try:
        audit_log = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=json.dumps(changes) if changes else None,
            metadata=json.dumps(metadata) if metadata else None,
        )

        db.add(audit_log)
        db.commit()

    except Exception as e:
        print(f"Manual audit log creation error: {e}")
        db.rollback()
