"""
Database repository for property records with idempotency support
"""

import os
from typing import Optional, List
from datetime import datetime

from sqlalchemy import create_engine, and_, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from .models import Base, Property, Tenant
from contracts.property_record import PropertyRecord


class PropertyRepository:
    """
    Repository for property database operations.

    Provides idempotent property creation and retrieval with tenant isolation.
    """

    def __init__(self, db_dsn: Optional[str] = None):
        """
        Initialize repository with database connection.

        Args:
            db_dsn: Database connection string. If None, reads from DB_DSN env var.
        """
        self.db_dsn = db_dsn or os.getenv("DB_DSN")
        if not self.db_dsn:
            raise ValueError("DB_DSN must be provided or set in environment")

        self.engine = create_engine(self.db_dsn)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Detect if we're using PostgreSQL (for RLS support)
        self.is_postgresql = "postgresql" in self.db_dsn.lower()

    def create_tables(self):
        """Create all tables (for testing only, use Alembic in production)"""
        Base.metadata.create_all(self.engine)

    def set_tenant_context(self, session: Session, tenant_id: str):
        """
        Set the current tenant context for RLS policies (PostgreSQL only).

        Args:
            session: SQLAlchemy session
            tenant_id: UUID of the current tenant
        """
        if self.is_postgresql:
            session.execute(text(f"SET app.current_tenant_id = '{tenant_id}';"))

    def reset_tenant_context(self, session: Session):
        """Reset the tenant context (PostgreSQL only)"""
        if self.is_postgresql:
            session.execute(text("RESET app.current_tenant_id;"))

    def find_by_apn_hash(
        self, apn_hash: str, tenant_id: str
    ) -> Optional[Property]:
        """
        Find a property by APN hash within a tenant.

        Args:
            apn_hash: SHA-256 hash of the normalized APN
            tenant_id: Tenant UUID

        Returns:
            Property if found, None otherwise
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)
            try:
                return (
                    session.query(Property)
                    .filter(
                        and_(
                            Property.apn_hash == apn_hash,
                            Property.tenant_id == tenant_id,
                        )
                    )
                    .first()
                )
            finally:
                self.reset_tenant_context(session)

    def create_property(
        self, record: PropertyRecord, tenant_id: str
    ) -> tuple[Property, bool]:
        """
        Create a property record with idempotency via APN hash.

        If a property with the same apn_hash already exists for this tenant,
        returns the existing property without creating a duplicate.

        Args:
            record: Normalized PropertyRecord from Discovery.Resolver
            tenant_id: Tenant UUID

        Returns:
            Tuple of (Property, created: bool) where created indicates if new record

        Raises:
            IntegrityError: If duplicate detected but couldn't be handled
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                # Check if property already exists (idempotency check)
                if record.apn_hash:
                    existing = (
                        session.query(Property)
                        .filter(
                            and_(
                                Property.apn_hash == record.apn_hash,
                                Property.tenant_id == tenant_id,
                            )
                        )
                        .first()
                    )
                    if existing:
                        return (existing, False)

                # Create new property
                prop = Property(
                    tenant_id=tenant_id,
                    apn=record.apn,
                    apn_hash=record.apn_hash,
                    street=record.address.line1 if record.address else None,
                    city=record.address.city if record.address else None,
                    state=record.address.state if record.address else None,
                    zip_code=record.address.zip if record.address else None,
                    latitude=record.geo.lat if record.geo else None,
                    longitude=record.geo.lng if record.geo else None,
                    owner_name=record.owner.name if record.owner else None,
                    owner_type=record.owner.type if record.owner else None,
                    bedrooms=(
                        record.attrs.beds if record.attrs else None
                    ),
                    bathrooms=(
                        record.attrs.baths if record.attrs else None
                    ),
                    square_feet=(
                        record.attrs.sqft if record.attrs else None
                    ),
                    year_built=(
                        record.attrs.year_built if record.attrs else None
                    ),
                    lot_size=(
                        record.attrs.lot_sqft if record.attrs else None
                    ),
                    status="discovered",
                    extra_metadata={
                        "source": record.source,
                        "source_id": record.source_id,
                        "url": record.url,
                        "discovered_at": record.discovered_at.isoformat(),
                        "provenance": (
                            [
                                {
                                    "field": p.field,
                                    "source": p.source,
                                    "confidence": p.confidence,
                                    "fetched_at": p.fetched_at.isoformat(),
                                }
                                for p in record.provenance
                            ]
                            if record.provenance
                            else []
                        ),
                    },
                )

                session.add(prop)
                session.commit()
                session.refresh(prop)

                return (prop, True)

            except IntegrityError as e:
                session.rollback()
                # Race condition: another transaction inserted the same property
                # Retry the find
                existing = (
                    session.query(Property)
                    .filter(
                        and_(
                            Property.apn_hash == record.apn_hash,
                            Property.tenant_id == tenant_id,
                        )
                    )
                    .first()
                )
                if existing:
                    return (existing, False)
                raise e
            finally:
                self.reset_tenant_context(session)

    def get_properties_by_tenant(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> List[Property]:
        """
        Get properties for a tenant with pagination.

        Args:
            tenant_id: Tenant UUID
            limit: Maximum number of properties to return
            offset: Number of properties to skip

        Returns:
            List of Property objects
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)
            try:
                return (
                    session.query(Property)
                    .filter(Property.tenant_id == tenant_id)
                    .order_by(Property.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
            finally:
                self.reset_tenant_context(session)

    def update_property_score(
        self, property_id: str, tenant_id: str, score: int, score_reasons: list
    ) -> Optional[Property]:
        """
        Update the score for a property.

        Args:
            property_id: Property UUID
            tenant_id: Tenant UUID
            score: Score value (0-100)
            score_reasons: List of score reason dicts

        Returns:
            Updated Property or None if not found
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)
            try:
                prop = (
                    session.query(Property)
                    .filter(
                        and_(
                            Property.id == property_id,
                            Property.tenant_id == tenant_id,
                        )
                    )
                    .first()
                )

                if prop:
                    prop.score = score
                    prop.score_reasons = score_reasons
                    prop.status = "scored"
                    prop.updated_at = datetime.utcnow()
                    session.commit()
                    session.refresh(prop)

                return prop
            finally:
                self.reset_tenant_context(session)

    def count_properties(self, tenant_id: str) -> int:
        """
        Count total properties for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Count of properties
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)
            try:
                return (
                    session.query(Property)
                    .filter(Property.tenant_id == tenant_id)
                    .count()
                )
            finally:
                self.reset_tenant_context(session)
