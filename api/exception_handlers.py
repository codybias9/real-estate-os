"""Exception handlers for FastAPI application."""

import traceback
from typing import Union

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError as PydanticValidationError

from .exceptions import RealEstateOSException
from .config import settings


async def real_estate_os_exception_handler(
    request: Request, exc: RealEstateOSException
) -> JSONResponse:
    """Handle custom Real Estate OS exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []

    if isinstance(exc, RequestValidationError):
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
    else:
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": {
                    "errors": errors
                }
            }
        },
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    error_message = "Database operation failed"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Handle specific SQLAlchemy exceptions
    if isinstance(exc, IntegrityError):
        status_code = status.HTTP_409_CONFLICT
        error_message = "Database integrity constraint violated"

        # Extract constraint details if available
        if exc.orig and hasattr(exc.orig, 'args'):
            error_details = str(exc.orig.args[0]) if exc.orig.args else ""
            if "duplicate key" in error_details.lower():
                error_message = "Resource already exists"
            elif "foreign key" in error_details.lower():
                error_message = "Related resource not found"
            elif "null value" in error_details.lower():
                error_message = "Required field is missing"

    # Log the full error for debugging
    if settings.DEBUG:
        print(f"SQLAlchemy Error: {str(exc)}")
        traceback.print_exc()

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": "DatabaseError",
                "message": error_message,
                "details": {
                    "database_error": str(exc) if settings.DEBUG else "Database operation failed"
                }
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    # Log the full error
    print(f"Unhandled exception: {str(exc)}")
    traceback.print_exc()

    # Don't expose internal errors in production
    error_message = str(exc) if settings.DEBUG else "An internal server error occurred"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": error_message,
                "details": {
                    "trace": traceback.format_exc() if settings.DEBUG else None
                }
            }
        },
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    from fastapi.exceptions import HTTPException

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "HTTPException",
                    "message": exc.detail,
                    "details": {}
                }
            },
        )

    return await generic_exception_handler(request, exc)


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    from fastapi.exceptions import HTTPException

    # Custom exceptions
    app.add_exception_handler(RealEstateOSException, real_estate_os_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)

    # Database errors
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Catch-all for unhandled exceptions
    app.add_exception_handler(Exception, generic_exception_handler)

    return app
