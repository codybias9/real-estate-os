"""
Database connection and session management with tenant context support.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text, event
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import logging

from api.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for models
Base = declarative_base()

# Create async engine
engine = create_async_engine(
    settings.database_url_async,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions in FastAPI endpoints.

    Usage:
        @app.get("/properties")
        async def list_properties(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Set the tenant context for Row-Level Security (RLS).

    This sets the PostgreSQL session variable 'app.tenant_id' which is used
    by RLS policies to filter data to the current tenant.

    Args:
        session: SQLAlchemy async session
        tenant_id: UUID of the tenant (from JWT token)

    Example:
        await set_tenant_context(db, "11111111-1111-1111-1111-111111111111")
        # All subsequent queries will only see this tenant's data
    """
    try:
        await session.execute(
            text("SET app.tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        logger.debug(f"Set tenant context: {tenant_id}")
    except Exception as e:
        logger.error(f"Failed to set tenant context: {e}")
        raise


async def clear_tenant_context(session: AsyncSession) -> None:
    """
    Clear the tenant context (set to NULL).

    This should be called at the end of a request to prevent context leakage.
    Note: With connection pooling, we always set tenant context at start of request,
    so this is mostly defensive.
    """
    try:
        await session.execute(text("SET app.tenant_id = ''"))
        logger.debug("Cleared tenant context")
    except Exception as e:
        logger.error(f"Failed to clear tenant context: {e}")
        raise


async def get_current_tenant_context(session: AsyncSession) -> Optional[str]:
    """
    Get the current tenant context (for debugging/verification).

    Returns:
        Current tenant_id or None if not set
    """
    try:
        result = await session.execute(
            text("SELECT current_setting('app.tenant_id', true)")
        )
        tenant_id = result.scalar()
        return tenant_id if tenant_id else None
    except Exception:
        return None


@asynccontextmanager
async def get_db_with_tenant(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with tenant context already set.

    This is a convenience context manager for background tasks where you
    already know the tenant_id and don't need to extract it from JWT.

    Usage:
        async with get_db_with_tenant(tenant_id) as db:
            properties = await db.execute(
                select(Property).where(Property.status == "active")
            )
            # RLS automatically filters to tenant_id

    Args:
        tenant_id: UUID of the tenant

    Yields:
        AsyncSession with tenant context set
    """
    async with AsyncSessionLocal() as session:
        try:
            await set_tenant_context(session, tenant_id)
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error (tenant {tenant_id}): {e}")
            raise
        finally:
            await clear_tenant_context(session)
            await session.close()


async def init_db() -> None:
    """
    Initialize database (create tables if not exist).

    Note: In production, we use Alembic migrations instead.
    This is primarily for development/testing.
    """
    async with engine.begin() as conn:
        # Create extensions if not exist
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "postgis"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized")


async def close_db() -> None:
    """
    Close database connections (cleanup on shutdown).
    """
    await engine.dispose()
    logger.info("Database connections closed")


# Event listener to log SQL queries in debug mode
if settings.debug:
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        logger.debug(f"SQL: {statement}")
        if parameters:
            logger.debug(f"Parameters: {parameters}")
