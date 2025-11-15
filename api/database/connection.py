"""Database connection management for API."""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager


# Get database connection string from environment
DB_DSN = os.getenv("DB_DSN", "postgresql://realestate:dev_password@db:5432/realestate_db")

# Create engine
engine = create_engine(DB_DSN, pool_pre_ping=True, pool_size=10, max_overflow=20)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Use with FastAPI Depends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database session.
    Use with 'with' statement.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
