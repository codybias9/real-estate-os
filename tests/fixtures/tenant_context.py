"""
Test Fixtures for Tenant Context

Auto-injects tenant context for database operations in tests.
Part of Wave 1.7 - Test helpers for tenant_id.
"""

import pytest
from uuid import uuid4, UUID
from typing import Generator
from sqlalchemy.orm import Session


# Default test tenant ID
DEFAULT_TEST_TENANT_ID = "10000000-0000-0000-0000-000000000001"


@pytest.fixture(scope="function")
def test_tenant_id() -> UUID:
    """
    Fixture providing a test tenant ID

    Usage:
        def test_something(test_tenant_id):
            # test_tenant_id is automatically provided
            assert test_tenant_id is not None
    """
    return UUID(DEFAULT_TEST_TENANT_ID)


@pytest.fixture(scope="function")
def random_tenant_id() -> UUID:
    """
    Fixture providing a random tenant ID for each test

    Usage:
        def test_something(random_tenant_id):
            # New UUID for each test
            pass
    """
    return uuid4()


@pytest.fixture(scope="function")
def db_with_tenant_context(db_session: Session, test_tenant_id: UUID) -> Generator[Session, None, None]:
    """
    Fixture providing a database session with tenant context already set

    Automatically sets app.current_tenant_id session variable for RLS.

    Usage:
        def test_query(db_with_tenant_context):
            # Tenant context is already set
            properties = db_with_tenant_context.query(Property).all()
            # Only returns properties for test tenant
    """
    # Set tenant context using PostgreSQL session variable
    db_session.execute(f"SET LOCAL app.current_tenant_id = '{test_tenant_id}'")

    yield db_session

    # Cleanup - reset tenant context
    db_session.execute("RESET app.current_tenant_id")


@pytest.fixture(scope="function")
def db_with_custom_tenant(db_session: Session) -> Generator:
    """
    Fixture factory for setting custom tenant context

    Usage:
        def test_multi_tenant(db_with_custom_tenant):
            # Set context for tenant A
            db_a = db_with_custom_tenant(tenant_a_id)
            properties_a = db_a.query(Property).all()

            # Set context for tenant B
            db_b = db_with_custom_tenant(tenant_b_id)
            properties_b = db_b.query(Property).all()

            # Should not overlap
            assert properties_a != properties_b
    """
    def _set_tenant(tenant_id: UUID) -> Session:
        db_session.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")
        return db_session

    yield _set_tenant

    # Cleanup
    db_session.execute("RESET app.current_tenant_id")


class TenantContextManager:
    """
    Context manager for temporarily setting tenant context

    Usage:
        def test_something(db_session):
            with TenantContextManager(db_session, tenant_id):
                # Tenant context is active
                properties = db_session.query(Property).all()
            # Context is reset
    """

    def __init__(self, session: Session, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.previous_context = None

    def __enter__(self):
        # Save previous context (if any)
        try:
            result = self.session.execute("SHOW app.current_tenant_id")
            self.previous_context = result.scalar()
        except Exception:
            self.previous_context = None

        # Set new context
        self.session.execute(f"SET LOCAL app.current_tenant_id = '{self.tenant_id}'")
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context or reset
        if self.previous_context:
            self.session.execute(f"SET LOCAL app.current_tenant_id = '{self.previous_context}'")
        else:
            self.session.execute("RESET app.current_tenant_id")


@pytest.fixture(scope="function")
def tenant_context_manager(db_session: Session):
    """
    Fixture providing TenantContextManager

    Usage:
        def test_multi_tenant(tenant_context_manager, db_session):
            with tenant_context_manager(tenant_a_id):
                props_a = db_session.query(Property).all()

            with tenant_context_manager(tenant_b_id):
                props_b = db_session.query(Property).all()
    """
    return lambda tenant_id: TenantContextManager(db_session, tenant_id)


def ensure_tenant_context(session: Session, tenant_id: UUID) -> None:
    """
    Helper function to ensure tenant context is set

    Can be called at the start of any test function.

    Usage:
        def test_something(db_session, test_tenant_id):
            ensure_tenant_context(db_session, test_tenant_id)
            # Now safe to query
            properties = db_session.query(Property).all()
    """
    session.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")


def verify_tenant_isolation(
    session: Session,
    model_class,
    tenant_a_id: UUID,
    tenant_b_id: UUID,
    create_func
) -> bool:
    """
    Helper to verify tenant isolation for a model

    Creates records for two tenants and verifies they don't see each other's data.

    Args:
        session: Database session
        model_class: SQLAlchemy model class to test
        tenant_a_id: First tenant UUID
        tenant_b_id: Second tenant UUID
        create_func: Function to create a model instance (model_class, tenant_id) -> instance

    Returns:
        True if isolation is working correctly

    Usage:
        def test_property_isolation(db_session):
            def create_property(model_class, tenant_id):
                return Property(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    canonical_address={'street': 'Test St'}
                )

            assert verify_tenant_isolation(
                db_session,
                Property,
                tenant_a_id,
                tenant_b_id,
                create_property
            )
    """
    # Create record for tenant A
    with TenantContextManager(session, tenant_a_id):
        record_a = create_func(model_class, tenant_a_id)
        session.add(record_a)
        session.commit()

        # Verify tenant A can see their record
        count_a = session.query(model_class).count()
        if count_a == 0:
            return False

    # Create record for tenant B
    with TenantContextManager(session, tenant_b_id):
        record_b = create_func(model_class, tenant_b_id)
        session.add(record_b)
        session.commit()

        # Verify tenant B can see their record
        count_b = session.query(model_class).count()
        if count_b == 0:
            return False

    # Verify tenant A still can't see tenant B's record
    with TenantContextManager(session, tenant_a_id):
        count_a_after = session.query(model_class).count()
        if count_a_after != count_a:
            return False

    # Verify tenant B can't see tenant A's record
    with TenantContextManager(session, tenant_b_id):
        count_b_after = session.query(model_class).count()
        if count_b_after != count_b:
            return False

    return True
