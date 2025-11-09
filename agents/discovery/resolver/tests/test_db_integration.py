"""
Integration tests for Discovery.Resolver with database persistence
"""

import os
import uuid
import pytest
from datetime import datetime

# Import resolver and repository
from resolver import DiscoveryResolver, IntakeStatus
from resolver.db import PropertyRepository, Property, Tenant

# Mark all tests in this module as requiring database
pytestmark = pytest.mark.requires_db


@pytest.fixture
def db_repository():
    """
    Create a test database repository.

    Uses DB_DSN environment variable or SQLite for testing.
    """
    dsn = os.getenv("DB_DSN", "sqlite:///./test_discovery.db")
    repo = PropertyRepository(db_dsn=dsn)

    # Create tables for testing (in production, use Alembic migrations)
    if "sqlite" in dsn:
        repo.create_tables()

    yield repo

    # Cleanup: close engine
    repo.engine.dispose()

    # Remove SQLite test database
    if "sqlite" in dsn and os.path.exists("./test_discovery.db"):
        os.remove("./test_discovery.db")


@pytest.fixture
def test_tenant(db_repository):
    """Create a test tenant"""
    tenant_id = uuid.uuid4()
    with db_repository.SessionLocal() as session:
        tenant = Tenant(
            id=tenant_id,
            name="Test Tenant",
            is_active=True
        )
        session.add(tenant)
        session.commit()

    yield str(tenant_id)


@pytest.fixture
def resolver_with_db(db_repository, test_tenant):
    """Create Discovery.Resolver with database repository"""
    return DiscoveryResolver(
        tenant_id=uuid.UUID(test_tenant),
        db_repository=db_repository
    )


class TestDatabaseIntegration:
    """Test Discovery.Resolver database integration"""

    def test_persist_property_creates_new_record(self, resolver_with_db, test_tenant):
        """Persisting a property should create a new database record"""
        raw_data = {
            "apn": "123-456-789",
            "address": {
                "street": "123 Main St",
                "city": "Springfield",
                "state": "CA",
                "zip": "90210"
            },
            "owner": {
                "name": "John Doe"
            },
            "attributes": {
                "beds": 3,
                "baths": 2.0,
                "sqft": 1500,
                "year_built": 2000
            }
        }

        # Process and persist
        result, property_id = resolver_with_db.process_and_persist(
            raw_data=raw_data,
            source="test_spider",
            source_id="test_001"
        )

        # Assertions
        assert result.status == IntakeStatus.NEW
        assert property_id is not None
        assert result.property_record is not None
        assert result.property_record.apn == "123-456-789"
        assert result.property_record.apn_hash is not None

    def test_duplicate_apn_hash_returns_existing(self, resolver_with_db, test_tenant):
        """Duplicate APN hash should return existing property without creating new"""
        raw_data = {
            "apn": "987-654-321",
            "address": {
                "street": "456 Oak Ave",
                "city": "Portland",
                "state": "OR",
                "zip": "97201"
            }
        }

        # First insert
        result1, property_id1 = resolver_with_db.process_and_persist(
            raw_data=raw_data,
            source="test_spider",
            source_id="test_002"
        )

        assert result1.status == IntakeStatus.NEW
        assert property_id1 is not None

        # Second insert with same APN (should be duplicate)
        result2, property_id2 = resolver_with_db.process_and_persist(
            raw_data=raw_data,
            source="test_spider",
            source_id="test_003"  # Different source_id, same APN
        )

        # Should return duplicate status
        assert result2.status == IntakeStatus.DUPLICATE
        assert property_id2 == property_id1  # Same property ID
        assert "duplicate" in result2.reason.lower()

    def test_idempotency_with_normalized_apn(self, resolver_with_db, test_tenant):
        """APN normalization ensures idempotency even with formatting differences"""
        raw_data1 = {
            "apn": "111-222-333",
            "address": {
                "street": "789 Pine St",
                "city": "Seattle",
                "state": "WA",
                "zip": "98101"
            }
        }

        raw_data2 = {
            "apn": "111 222 333",  # Different formatting, same APN
            "address": {
                "street": "789 Pine St",
                "city": "Seattle",
                "state": "WA",
                "zip": "98101"
            }
        }

        # First insert
        result1, property_id1 = resolver_with_db.process_and_persist(
            raw_data=raw_data1,
            source="test_spider",
            source_id="test_004"
        )

        # Second insert with differently formatted APN
        result2, property_id2 = resolver_with_db.process_and_persist(
            raw_data=raw_data2,
            source="test_spider",
            source_id="test_005"
        )

        # Should be treated as duplicate
        assert result1.status == IntakeStatus.NEW
        assert result2.status == IntakeStatus.DUPLICATE
        assert property_id1 == property_id2

        # Both should have same apn_hash
        assert result1.apn_hash == result2.apn_hash

    def test_repository_count_properties(self, resolver_with_db, db_repository, test_tenant):
        """Repository should correctly count properties per tenant"""
        # Insert 3 properties
        for i in range(3):
            raw_data = {
                "apn": f"999-888-77{i}",
                "address": {
                    "street": f"{i+1} Test St",
                    "city": "TestCity",
                    "state": "TX",
                    "zip": "75001"
                }
            }
            resolver_with_db.process_and_persist(
                raw_data=raw_data,
                source="test_spider",
                source_id=f"test_00{i+6}"
            )

        # Count properties
        count = db_repository.count_properties(test_tenant)
        assert count == 3

    def test_repository_get_properties_pagination(self, resolver_with_db, db_repository, test_tenant):
        """Repository should support pagination for property retrieval"""
        # Insert 5 properties
        for i in range(5):
            raw_data = {
                "apn": f"555-444-33{i}",
                "address": {
                    "street": f"{i+10} Pagination St",
                    "city": "PageCity",
                    "state": "FL",
                    "zip": "33101"
                }
            }
            resolver_with_db.process_and_persist(
                raw_data=raw_data,
                source="test_spider",
                source_id=f"test_01{i}"
            )

        # Get first page (limit=2)
        page1 = db_repository.get_properties_by_tenant(
            tenant_id=test_tenant,
            limit=2,
            offset=0
        )
        assert len(page1) == 2

        # Get second page
        page2 = db_repository.get_properties_by_tenant(
            tenant_id=test_tenant,
            limit=2,
            offset=2
        )
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_property_metadata_stored_correctly(self, resolver_with_db, db_repository, test_tenant):
        """Property metadata should be stored as JSON in database"""
        raw_data = {
            "apn": "777-888-999",
            "address": {
                "street": "100 Metadata Ave",
                "city": "DataCity",
                "state": "NY",
                "zip": "10001"
            },
            "url": "https://example.com/property/777888999"
        }

        result, property_id = resolver_with_db.process_and_persist(
            raw_data=raw_data,
            source="test_metadata_spider",
            source_id="test_meta_001"
        )

        # Retrieve property from database
        with db_repository.SessionLocal() as session:
            db_repository.set_tenant_context(session, test_tenant)
            prop = session.query(Property).filter(Property.id == property_id).first()

            # Verify metadata
            assert prop.extra_metadata["source"] == "test_metadata_spider"
            assert prop.extra_metadata["source_id"] == "test_meta_001"
            assert prop.extra_metadata["url"] == "https://example.com/property/777888999"
            assert "discovered_at" in prop.extra_metadata

    def test_invalid_data_not_persisted(self, resolver_with_db, db_repository, test_tenant):
        """Invalid data should not be persisted to database"""
        initial_count = db_repository.count_properties(test_tenant)

        # Invalid data (missing required address fields)
        raw_data = {
            "apn": "000-000-000",
            "address": {
                "street": "Incomplete St"
                # Missing city, state, zip
            }
        }

        result, property_id = resolver_with_db.process_and_persist(
            raw_data=raw_data,
            source="test_spider",
            source_id="test_invalid_001"
        )

        # Should be rejected
        assert result.status == IntakeStatus.REJECTED
        assert property_id is None

        # Count should not increase
        final_count = db_repository.count_properties(test_tenant)
        assert final_count == initial_count


class TestRepositoryIdempotency:
    """Test repository-level idempotency guarantees"""

    def test_create_property_idempotent(self, db_repository, test_tenant):
        """Creating property twice should return same record"""
        from contracts import PropertyRecord, Address

        # Create a normalized PropertyRecord
        record = PropertyRecord(
            apn="IDEMPOTENT-001",
            apn_hash=DiscoveryResolver.compute_apn_hash("IDEMPOTENT-001"),
            address=Address(
                line1="1 Idempotent St",
                city="IdemCity",
                state="CA",
                zip="90001"
            ),
            source="test",
            source_id="idem_001",
            provenance=[]
        )

        # First create
        prop1, created1 = db_repository.create_property(record, test_tenant)
        assert created1 is True
        assert prop1.apn == "IDEMPOTENT-001"

        # Second create (should find existing)
        prop2, created2 = db_repository.create_property(record, test_tenant)
        assert created2 is False
        assert prop2.id == prop1.id  # Same property

    def test_find_by_apn_hash(self, db_repository, test_tenant):
        """Repository should find property by APN hash"""
        from contracts import PropertyRecord, Address

        apn_hash = DiscoveryResolver.compute_apn_hash("FINDME-001")

        record = PropertyRecord(
            apn="FINDME-001",
            apn_hash=apn_hash,
            address=Address(
                line1="1 Find St",
                city="FindCity",
                state="TX",
                zip="75001"
            ),
            source="test",
            source_id="find_001",
            provenance=[]
        )

        # Create property
        prop, created = db_repository.create_property(record, test_tenant)
        assert created is True

        # Find by APN hash
        found = db_repository.find_by_apn_hash(apn_hash, test_tenant)
        assert found is not None
        assert found.id == prop.id
        assert found.apn == "FINDME-001"

    def test_update_property_score(self, db_repository, test_tenant):
        """Repository should update property score"""
        from contracts import PropertyRecord, Address

        record = PropertyRecord(
            apn="SCORE-001",
            apn_hash=DiscoveryResolver.compute_apn_hash("SCORE-001"),
            address=Address(
                line1="1 Score St",
                city="ScoreCity",
                state="FL",
                zip="33101"
            ),
            source="test",
            source_id="score_001",
            provenance=[]
        )

        # Create property
        prop, created = db_repository.create_property(record, test_tenant)
        assert prop.score is None

        # Update score
        score_reasons = [
            {"factor": "location", "weight": 0.3, "contribution": 25}
        ]
        updated = db_repository.update_property_score(
            property_id=str(prop.id),
            tenant_id=test_tenant,
            score=75,
            score_reasons=score_reasons
        )

        assert updated is not None
        assert updated.score == 75
        assert updated.score_reasons == score_reasons
        assert updated.status == "scored"
