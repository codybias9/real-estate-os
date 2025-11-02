"""
Health Check Endpoints
Provides process health and database connectivity checks
"""

import os
from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, text

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response schema"""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})

    status: str


class PingResponse(BaseModel):
    """Database ping response schema"""

    model_config = ConfigDict(json_schema_extra={"example": {"ping_count": 42}})

    ping_count: int


@router.get(
    "/healthz",
    response_model=HealthResponse,
    summary="Process Health Check",
    description="Returns OK if the process is running. Does not check external dependencies.",
    responses={
        200: {
            "description": "Process is healthy",
            "content": {"application/json": {"example": {"status": "ok"}}},
        }
    },
)
def healthz() -> Dict[str, str]:
    """
    Process health check endpoint.

    Returns a simple OK status to verify the API process is running.
    This endpoint does not verify database connectivity or other dependencies.
    """
    return {"status": "ok"}


@router.get(
    "/ping",
    response_model=PingResponse,
    summary="Database Connectivity Check",
    description="Touches the database and returns the number of pings recorded. Creates ping table if needed.",
    responses={
        200: {
            "description": "Database is accessible",
            "content": {"application/json": {"example": {"ping_count": 42}}},
        },
        500: {
            "description": "Database configuration missing or connection failed",
            "content": {
                "application/json": {
                    "example": {"detail": "DB_DSN environment variable not set"}
                }
            },
        },
    },
)
def ping() -> Dict[str, int]:
    """
    Database connectivity check endpoint.

    Creates a ping table if it doesn't exist, inserts a row, and returns
    the total count of pings. This verifies:
    - DB_DSN environment variable is configured
    - Database connection can be established
    - Database accepts writes

    Raises:
        HTTPException: 500 if DB_DSN is not set or connection fails
    """
    dsn = os.getenv("DB_DSN")
    if not dsn:
        raise HTTPException(status_code=500, detail="DB_DSN environment variable not set")

    try:
        engine = create_engine(dsn)
        with engine.begin() as conn:
            # Create ping table if it doesn't exist (idempotent)
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS ping "
                    "(id serial PRIMARY KEY, ts timestamptz DEFAULT now())"
                )
            )
            # Insert a ping record
            conn.execute(text("INSERT INTO ping DEFAULT VALUES"))
            # Get total ping count
            count = conn.execute(text("SELECT count(*) FROM ping")).scalar()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

    return {"ping_count": count}
