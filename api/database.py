"""
Database connection and session management
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional
from contextlib import contextmanager

# Get database URL from environment
DATABASE_URL = os.getenv("DB_DSN", "postgresql://postgres:postgres@localhost:5432/real_estate_os")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes to get a database session

    Usage in routes:
        @app.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """
    Context manager for database sessions

    Usage:
        with get_db_context() as db:
            # use db
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize the database (create all tables)
    Note: In production, use Alembic migrations instead
    """
    from db.models import Base
    Base.metadata.create_all(bind=engine)


def set_current_user_for_rls(db: Session, user_id: int):
    """
    Set the current user ID in the database session for Row-Level Security

    This must be called before any queries that rely on RLS policies

    Args:
        db: SQLAlchemy session
        user_id: The current user's ID

    Example:
        @app.get("/properties")
        def get_properties(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
            set_current_user_for_rls(db, current_user.id)
            properties = db.query(Property).all()  # RLS automatically filters by team
    """
    db.execute(text("SELECT set_config('app.current_user_id', :user_id, false)"), {"user_id": str(user_id)})


def get_db_with_rls(user_id: Optional[int] = None) -> Generator[Session, None, None]:
    """
    Get a database session with RLS context set

    Args:
        user_id: User ID to set for RLS (if None, RLS policies won't filter)

    Usage:
        @app.get("/properties")
        def get_properties(
            db: Session = Depends(lambda: get_db_with_rls(current_user.id)),
            current_user: User = Depends(get_current_user)
        ):
            properties = db.query(Property).all()  # Automatically filtered by team
    """
    db = SessionLocal()
    try:
        if user_id is not None:
            set_current_user_for_rls(db, user_id)
        yield db
    finally:
        db.close()
