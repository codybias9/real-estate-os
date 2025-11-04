"""Database configuration and session management."""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Database URL from environment
DATABASE_URL = os.getenv(
    "DB_DSN",
    "postgresql://realestate:realestate@postgres:5432/realestate"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Row-level security filter injection
def apply_rls_filter(query, user, model):
    """Apply row-level security filters based on user's organization."""
    if hasattr(model, 'organization_id'):
        if user and hasattr(user, 'organization_id'):
            query = query.filter(model.organization_id == user.organization_id)
    return query
