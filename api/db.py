"""
Database connection layer with tenant isolation via RLS

Sets app.tenant_id session variable from JWT claims to enforce
Row-Level Security policies.
"""

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool
from contextlib import contextmanager
from typing import Optional, Generator
import os


# Database URL
DATABASE_URL = os.getenv("DB_DSN", "postgresql://postgres:postgres@localhost:5432/real_estate_os")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def set_tenant_context(connection, tenant_id: str):
    """
    Set tenant context for RLS enforcement

    This must be called at the start of every request with the tenant_id
    from the JWT token.
    """
    connection.execute(text(f"SET app.tenant_id = '{tenant_id}'"))


def clear_tenant_context(connection):
    """Clear tenant context"""
    connection.execute(text("RESET app.tenant_id"))


@contextmanager
def get_db_with_tenant(tenant_id: str) -> Generator[Session, None, None]:
    """
    Get database session with tenant context set

    Usage:
        with get_db_with_tenant(tenant_id) as db:
            properties = db.query(Property).all()  # Automatically filtered by RLS
    """
    db = SessionLocal()
    try:
        # Set tenant context for RLS
        set_tenant_context(db.connection(), tenant_id)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        clear_tenant_context(db.connection())
        db.close()


def get_db() -> Generator[Session, None, None]:
    """
    Get database session without tenant context (for internal use only)

    WARNING: This bypasses RLS. Only use for system-level operations.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# FastAPI dependency for tenant-scoped DB access
def get_tenant_db(tenant_id: str):
    """
    FastAPI dependency for tenant-scoped database access

    Usage in FastAPI:
        @app.get("/api/v1/properties")
        def list_properties(
            tenant_id: str = Depends(get_tenant_id),
            db: Session = Depends(lambda: get_tenant_db(tenant_id))
        ):
            return db.query(Property).all()
    """
    def _get_db():
        with get_db_with_tenant(tenant_id) as db:
            yield db

    return _get_db


# Connection pool event listeners for monitoring
@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log new database connections"""
    pass  # Add logging if needed


@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkouts from pool"""
    pass  # Add logging if needed
