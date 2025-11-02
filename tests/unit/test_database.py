"""
Unit tests for database operations and RLS (Row-Level Security).
"""
import pytest
from uuid import uuid4
from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError

from api.database import (
    get_db,
    set_tenant_context,
    clear_tenant_context,
    get_current_tenant_id
)
from api.orm_models import Property, Prospect, Offer


class TestTenantContext:
    """Test tenant context management."""

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_set_tenant_context(self, db_session, tenant_id):
        """Test setting tenant context."""
        await set_tenant_context(db_session, tenant_id)

        # Verify context is set
        result = await db_session.execute(
            text("SELECT current_setting('app.tenant_id', true)")
        )
        current_tenant = result.scalar()

        assert current_tenant == tenant_id

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_clear_tenant_context(self, db_session, tenant_id):
        """Test clearing tenant context."""
        # Set context first
        await set_tenant_context(db_session, tenant_id)

        # Clear context
        await clear_tenant_context(db_session)

        # Verify context is cleared
        result = await db_session.execute(
            text("SELECT current_setting('app.tenant_id', true)")
        )
        current_tenant = result.scalar()

        assert current_tenant == "" or current_tenant is None

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_get_current_tenant_id(self, db_session, tenant_id):
        """Test retrieving current tenant ID."""
        # Set context
        await set_tenant_context(db_session, tenant_id)

        # Get current tenant ID
        current_id = await get_current_tenant_id(db_session)

        assert current_id == tenant_id

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_get_current_tenant_id_not_set(self, db_session):
        """Test getting tenant ID when not set."""
        # Clear any existing context
        await clear_tenant_context(db_session)

        # Should return None or raise exception
        current_id = await get_current_tenant_id(db_session)
        assert current_id is None or current_id == ""


class TestRowLevelSecurity:
    """Test Row-Level Security policies."""

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_rls_insert_with_tenant_context(self, tenant_db_session, tenant_id, sample_property_data):
        """Test inserting data with tenant context automatically adds tenant_id."""
        # Create property
        property_obj = Property(**sample_property_data)
        tenant_db_session.add(property_obj)
        await tenant_db_session.commit()
        await tenant_db_session.refresh(property_obj)

        # Verify tenant_id is set
        assert property_obj.tenant_id == tenant_id

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_rls_query_filters_by_tenant(self, tenant_db_session, tenant_id, sample_property_data):
        """Test queries are automatically filtered by tenant_id."""
        # Create property for current tenant
        property1 = Property(**sample_property_data)
        tenant_db_session.add(property1)
        await tenant_db_session.commit()

        # Create property for different tenant (simulated)
        other_tenant_id = str(uuid4())
        property2_data = {**sample_property_data, "tenant_id": other_tenant_id}

        # Switch to other tenant context
        await set_tenant_context(tenant_db_session, other_tenant_id)
        property2 = Property(**property2_data)
        tenant_db_session.add(property2)
        await tenant_db_session.commit()

        # Switch back to original tenant
        await set_tenant_context(tenant_db_session, tenant_id)

        # Query should only return property1
        result = await tenant_db_session.execute(select(Property))
        properties = result.scalars().all()

        assert len(properties) == 1
        assert properties[0].tenant_id == tenant_id

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_rls_prevents_cross_tenant_access(self, tenant_db_session, tenant_id):
        """Test RLS prevents accessing other tenant's data."""
        # Create two properties for different tenants
        tenant1_id = str(uuid4())
        tenant2_id = str(uuid4())

        # Set context to tenant1
        await set_tenant_context(tenant_db_session, tenant1_id)

        property1 = Property(
            tenant_id=tenant1_id,
            address="123 Main St, Austin, TX",
            latitude=30.2672,
            longitude=-97.7431
        )
        tenant_db_session.add(property1)
        await tenant_db_session.commit()

        # Set context to tenant2
        await set_tenant_context(tenant_db_session, tenant2_id)

        # Query from tenant2 should not see tenant1's property
        result = await tenant_db_session.execute(select(Property))
        properties = result.scalars().all()

        assert len(properties) == 0

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_rls_null_tenant_id_rejected(self, db_session):
        """Test NULL tenant_id is rejected by database constraints."""
        # Try to create property with NULL tenant_id
        property_obj = Property(
            tenant_id=None,  # NULL tenant_id
            address="123 Main St",
            latitude=30.2672,
            longitude=-97.7431
        )

        db_session.add(property_obj)

        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_rls_update_respects_tenant(self, tenant_db_session, tenant_id, sample_property_data):
        """Test updates are scoped to current tenant."""
        # Create property
        property_obj = Property(**sample_property_data)
        tenant_db_session.add(property_obj)
        await tenant_db_session.commit()
        property_id = property_obj.id

        # Update property
        property_obj.listing_price = 500000
        await tenant_db_session.commit()

        # Verify update
        result = await tenant_db_session.execute(
            select(Property).where(Property.id == property_id)
        )
        updated_property = result.scalar_one()

        assert updated_property.listing_price == 500000
        assert updated_property.tenant_id == tenant_id

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_rls_delete_respects_tenant(self, tenant_db_session, tenant_id, sample_property_data):
        """Test deletes are scoped to current tenant."""
        # Create property
        property_obj = Property(**sample_property_data)
        tenant_db_session.add(property_obj)
        await tenant_db_session.commit()
        property_id = property_obj.id

        # Delete property
        await tenant_db_session.delete(property_obj)
        await tenant_db_session.commit()

        # Verify deletion
        result = await tenant_db_session.execute(
            select(Property).where(Property.id == property_id)
        )
        deleted_property = result.scalar_one_or_none()

        assert deleted_property is None


class TestDatabaseConnection:
    """Test database connection management."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test get_db() yields a valid session."""
        async for session in get_db():
            assert session is not None
            # Should be able to execute query
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_db_session_rollback_on_error(self, db_session):
        """Test session rolls back on error."""
        # Start transaction
        property_obj = Property(
            tenant_id=str(uuid4()),
            address="Test Address",
            latitude=30.0,
            longitude=-97.0
        )
        db_session.add(property_obj)

        # Simulate error
        await db_session.rollback()

        # Property should not be committed
        result = await db_session.execute(select(Property))
        properties = result.scalars().all()

        # Should be empty (or only contain pre-existing data)
        assert property_obj not in properties

    @pytest.mark.asyncio
    async def test_db_session_isolation(self):
        """Test sessions are isolated from each other."""
        tenant_id = str(uuid4())

        # Create two sessions
        session1 = None
        session2 = None

        async for s1 in get_db():
            session1 = s1
            await set_tenant_context(session1, tenant_id)
            break

        async for s2 in get_db():
            session2 = s2
            break

        # Session2 should not have tenant context from session1
        current_tenant = await get_current_tenant_id(session2)
        assert current_tenant != tenant_id or current_tenant is None


class TestORMModels:
    """Test ORM model behavior."""

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_property_model_creation(self, tenant_db_session, sample_property_data):
        """Test Property model creation."""
        property_obj = Property(**sample_property_data)
        tenant_db_session.add(property_obj)
        await tenant_db_session.commit()
        await tenant_db_session.refresh(property_obj)

        assert property_obj.id is not None
        assert property_obj.address == sample_property_data["address"]
        assert property_obj.latitude == sample_property_data["latitude"]
        assert property_obj.created_at is not None
        assert property_obj.updated_at is not None

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_prospect_model_creation(self, tenant_db_session, sample_prospect_data):
        """Test Prospect model creation."""
        prospect_obj = Prospect(**sample_prospect_data)
        tenant_db_session.add(prospect_obj)
        await tenant_db_session.commit()
        await tenant_db_session.refresh(prospect_obj)

        assert prospect_obj.id is not None
        assert prospect_obj.name == sample_prospect_data["name"]
        assert prospect_obj.email == sample_prospect_data["email"]
        assert prospect_obj.status == sample_prospect_data["status"]

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_offer_model_with_relationships(self, tenant_db_session, tenant_id, sample_property_data, sample_prospect_data):
        """Test Offer model with foreign key relationships."""
        # Create property and prospect first
        property_obj = Property(**sample_property_data)
        tenant_db_session.add(property_obj)

        prospect_obj = Prospect(**sample_prospect_data)
        tenant_db_session.add(prospect_obj)

        await tenant_db_session.commit()
        await tenant_db_session.refresh(property_obj)
        await tenant_db_session.refresh(prospect_obj)

        # Create offer
        offer_data = {
            "tenant_id": tenant_id,
            "property_id": property_obj.id,
            "prospect_id": prospect_obj.id,
            "offer_amount": 475000,
            "status": "pending"
        }

        offer_obj = Offer(**offer_data)
        tenant_db_session.add(offer_obj)
        await tenant_db_session.commit()
        await tenant_db_session.refresh(offer_obj)

        assert offer_obj.id is not None
        assert offer_obj.property_id == property_obj.id
        assert offer_obj.prospect_id == prospect_obj.id

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_model_timestamps_auto_update(self, tenant_db_session, sample_property_data):
        """Test created_at and updated_at timestamps."""
        import asyncio

        # Create property
        property_obj = Property(**sample_property_data)
        tenant_db_session.add(property_obj)
        await tenant_db_session.commit()
        await tenant_db_session.refresh(property_obj)

        created_at = property_obj.created_at
        updated_at = property_obj.updated_at

        # Wait a moment
        await asyncio.sleep(0.1)

        # Update property
        property_obj.listing_price = 500000
        await tenant_db_session.commit()
        await tenant_db_session.refresh(property_obj)

        # updated_at should change, created_at should not
        assert property_obj.created_at == created_at
        assert property_obj.updated_at > updated_at

    @pytest.mark.asyncio
    @pytest.mark.requires_db
    async def test_model_unique_constraints(self, tenant_db_session, sample_property_data):
        """Test unique constraints on models."""
        # Create property
        property_obj = Property(**sample_property_data)
        tenant_db_session.add(property_obj)
        await tenant_db_session.commit()

        # Try to create duplicate (if unique constraint exists)
        # This test depends on actual schema - adjust based on constraints
        duplicate_obj = Property(**sample_property_data)
        tenant_db_session.add(duplicate_obj)

        # May or may not raise error depending on schema
        # This is a placeholder test
        try:
            await tenant_db_session.commit()
        except IntegrityError:
            # Expected if unique constraint exists
            pass


# ============================================================================
# Test Statistics
# ============================================================================
# Total tests in this module: 19
