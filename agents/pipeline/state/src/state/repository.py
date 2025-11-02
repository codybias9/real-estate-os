"""
Repository for property state persistence
"""

import os
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import create_engine, and_, text
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, PropertyStateModel, StateTransitionModel, PropertyStateEnum


class StateRepository:
    """
    Repository for property state operations.

    Provides state tracking, transition logging, and history queries.
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

    def get_state(
        self, property_id: str, tenant_id: str
    ) -> Optional[PropertyStateModel]:
        """
        Get current state for a property.

        Args:
            property_id: Property UUID
            tenant_id: Tenant UUID

        Returns:
            PropertyStateModel if found, None otherwise
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)
            try:
                return (
                    session.query(PropertyStateModel)
                    .filter(
                        and_(
                            PropertyStateModel.property_id == property_id,
                            PropertyStateModel.tenant_id == tenant_id,
                        )
                    )
                    .first()
                )
            finally:
                self.reset_tenant_context(session)

    def create_state(
        self,
        property_id: str,
        tenant_id: str,
        initial_state: PropertyStateEnum = PropertyStateEnum.DISCOVERED,
        event_id: Optional[str] = None,
        event_subject: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> PropertyStateModel:
        """
        Create initial state for a property.

        Args:
            property_id: Property UUID
            tenant_id: Tenant UUID
            initial_state: Initial state (default: DISCOVERED)
            event_id: Event ID that created this state
            event_subject: Event subject
            context: Additional context data

        Returns:
            Created PropertyStateModel
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                state = PropertyStateModel(
                    tenant_id=tenant_id,
                    property_id=property_id,
                    current_state=initial_state.value,
                    last_event_id=event_id,
                    last_event_subject=event_subject,
                    last_transition_at=datetime.now(timezone.utc),
                    context=context or {},
                )

                session.add(state)
                session.commit()
                session.refresh(state)

                return state
            finally:
                self.reset_tenant_context(session)

    def transition_state(
        self,
        property_id: str,
        tenant_id: str,
        to_state: PropertyStateEnum,
        event_id: str,
        event_subject: str,
        event_payload: Optional[dict] = None,
        reason: Optional[str] = None,
    ) -> PropertyStateModel:
        """
        Transition property to new state and log transition.

        Args:
            property_id: Property UUID
            tenant_id: Tenant UUID
            to_state: Target state
            event_id: Event ID that triggered transition
            event_subject: Event subject
            event_payload: Event payload for audit
            reason: Human-readable transition reason

        Returns:
            Updated PropertyStateModel

        Raises:
            ValueError: If property state not found
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                # Get current state
                state = (
                    session.query(PropertyStateModel)
                    .filter(
                        and_(
                            PropertyStateModel.property_id == property_id,
                            PropertyStateModel.tenant_id == tenant_id,
                        )
                    )
                    .first()
                )

                if not state:
                    raise ValueError(
                        f"Property state not found for {property_id}"
                    )

                from_state = state.current_state

                # Create transition record
                transition = StateTransitionModel(
                    property_state_id=state.id,
                    from_state=from_state,
                    to_state=to_state.value,
                    event_id=event_id,
                    event_subject=event_subject,
                    event_payload=event_payload,
                    reason=reason,
                    transitioned_at=datetime.now(timezone.utc),
                )

                session.add(transition)

                # Update current state
                state.current_state = to_state.value
                state.last_event_id = event_id
                state.last_event_subject = event_subject
                state.last_transition_at = datetime.now(timezone.utc)
                state.updated_at = datetime.now(timezone.utc)

                session.commit()
                session.refresh(state)

                return state
            finally:
                self.reset_tenant_context(session)

    def get_transitions(
        self, property_id: str, tenant_id: str, limit: int = 100
    ) -> List[StateTransitionModel]:
        """
        Get transition history for a property.

        Args:
            property_id: Property UUID
            tenant_id: Tenant UUID
            limit: Maximum number of transitions to return

        Returns:
            List of StateTransitionModel (newest first)
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                # First get the property state
                state = (
                    session.query(PropertyStateModel)
                    .filter(
                        and_(
                            PropertyStateModel.property_id == property_id,
                            PropertyStateModel.tenant_id == tenant_id,
                        )
                    )
                    .first()
                )

                if not state:
                    return []

                # Get transitions
                return (
                    session.query(StateTransitionModel)
                    .filter(StateTransitionModel.property_state_id == state.id)
                    .order_by(StateTransitionModel.transitioned_at.desc())
                    .limit(limit)
                    .all()
                )
            finally:
                self.reset_tenant_context(session)

    def get_properties_by_state(
        self, state: PropertyStateEnum, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> List[PropertyStateModel]:
        """
        Get all properties in a specific state.

        Args:
            state: Target state
            tenant_id: Tenant UUID
            limit: Maximum number of properties to return
            offset: Number of properties to skip

        Returns:
            List of PropertyStateModel
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                return (
                    session.query(PropertyStateModel)
                    .filter(
                        and_(
                            PropertyStateModel.current_state == state.value,
                            PropertyStateModel.tenant_id == tenant_id,
                        )
                    )
                    .order_by(PropertyStateModel.last_transition_at.desc())
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
            finally:
                self.reset_tenant_context(session)

    def count_by_state(self, tenant_id: str) -> dict[str, int]:
        """
        Count properties in each state for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict mapping state name to count
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                results = (
                    session.query(
                        PropertyStateModel.current_state,
                        PropertyStateModel.id,
                    )
                    .filter(PropertyStateModel.tenant_id == tenant_id)
                    .all()
                )

                counts = {}
                for state, _ in results:
                    counts[state] = counts.get(state, 0) + 1

                return counts
            finally:
                self.reset_tenant_context(session)
