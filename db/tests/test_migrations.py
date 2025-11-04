"""
Tests for Alembic database migrations and RLS policies
"""

import os
import subprocess
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, text, inspect


@pytest.fixture(scope="module")
def db_engine():
    """
    Create a test database engine.

    Uses DB_DSN environment variable or falls back to SQLite for testing.
    """
    dsn = os.getenv("DB_DSN", "sqlite:///test.db")
    engine = create_engine(dsn)
    yield engine
    engine.dispose()


@contextmanager
def temp_tenant_context(connection, tenant_id):
    """
    Context manager to set the current tenant for RLS policies.
    """
    connection.execute(text(f"SET app.current_tenant_id = '{tenant_id}';"))
    try:
        yield
    finally:
        connection.execute(text("RESET app.current_tenant_id;"))


class TestMigrations:
    """Test migration up/down operations"""

    @pytest.mark.requires_db
    def test_migration_runs_successfully(self):
        """Migration should run without errors"""
        result = subprocess.run(
            ["poetry", "run", "alembic", "upgrade", "head"],
            cwd="/home/user/real-estate-os/db",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Migration failed: {result.stderr}"

    @pytest.mark.requires_db
    def test_migration_is_reversible(self):
        """Migration should be reversible (downgrade should work)"""
        # First upgrade to head
        subprocess.run(
            ["poetry", "run", "alembic", "upgrade", "head"],
            cwd="/home/user/real-estate-os/db",
            check=True,
        )

        # Then downgrade to base
        result = subprocess.run(
            ["poetry", "run", "alembic", "downgrade", "base"],
            cwd="/home/user/real-estate-os/db",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Downgrade failed: {result.stderr}"

        # Upgrade again for other tests
        subprocess.run(
            ["poetry", "run", "alembic", "upgrade", "head"],
            cwd="/home/user/real-estate-os/db",
            check=True,
        )

    @pytest.mark.requires_db
    def test_all_expected_tables_exist(self, db_engine):
        """Migration should create all expected tables"""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()

        expected_tables = ["tenants", "users", "properties", "ping"]
        for table in expected_tables:
            assert table in tables, f"Table '{table}' not found in database"

    @pytest.mark.requires_db
    def test_tenants_table_schema(self, db_engine):
        """Tenants table should have correct schema"""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("tenants")}

        assert "id" in columns
        assert "name" in columns
        assert "created_at" in columns
        assert "updated_at" in columns
        assert "is_active" in columns

    @pytest.mark.requires_db
    def test_users_table_schema(self, db_engine):
        """Users table should have correct schema with tenant_id"""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("users")}

        assert "id" in columns
        assert "tenant_id" in columns
        assert "email" in columns
        assert "full_name" in columns
        assert "is_active" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    @pytest.mark.requires_db
    def test_properties_table_schema(self, db_engine):
        """Properties table should have correct schema"""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("properties")}

        # Core fields
        assert "id" in columns
        assert "tenant_id" in columns
        assert "apn" in columns
        assert "apn_hash" in columns

        # Address fields
        assert "street" in columns
        assert "city" in columns
        assert "state" in columns
        assert "zip_code" in columns

        # Geo fields
        assert "latitude" in columns
        assert "longitude" in columns

        # Owner fields
        assert "owner_name" in columns
        assert "owner_type" in columns

        # Attribute fields
        assert "bedrooms" in columns
        assert "bathrooms" in columns
        assert "square_feet" in columns
        assert "year_built" in columns
        assert "lot_size" in columns

        # Scoring fields
        assert "score" in columns
        assert "score_reasons" in columns

        # Metadata
        assert "status" in columns
        assert "metadata" in columns
        assert "created_at" in columns
        assert "updated_at" in columns


class TestRowLevelSecurity:
    """Test Row-Level Security (RLS) policies"""

    @pytest.mark.requires_db
    def test_rls_enabled_on_users(self, db_engine):
        """RLS should be enabled on users table"""
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT relrowsecurity
                    FROM pg_class
                    WHERE relname = 'users';
                """)
            ).scalar()
            assert result is True, "RLS not enabled on users table"

    @pytest.mark.requires_db
    def test_rls_enabled_on_properties(self, db_engine):
        """RLS should be enabled on properties table"""
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT relrowsecurity
                    FROM pg_class
                    WHERE relname = 'properties';
                """)
            ).scalar()
            assert result is True, "RLS not enabled on properties table"

    @pytest.mark.requires_db
    def test_rls_policy_exists_for_users(self, db_engine):
        """RLS policy should exist for users table"""
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM pg_policies
                    WHERE tablename = 'users' AND policyname = 'tenant_isolation_users';
                """)
            ).scalar()
            assert result == 1, "RLS policy 'tenant_isolation_users' not found"

    @pytest.mark.requires_db
    def test_rls_policy_exists_for_properties(self, db_engine):
        """RLS policy should exist for properties table"""
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM pg_policies
                    WHERE tablename = 'properties' AND policyname = 'tenant_isolation_properties';
                """)
            ).scalar()
            assert result == 1, "RLS policy 'tenant_isolation_properties' not found"

    @pytest.mark.requires_db
    def test_rls_isolates_tenant_data(self, db_engine):
        """RLS should isolate data between tenants"""
        with db_engine.begin() as conn:
            # Create two tenants
            tenant1_id = str(uuid.uuid4())
            tenant2_id = str(uuid.uuid4())

            conn.execute(
                text(f"INSERT INTO tenants (id, name) VALUES ('{tenant1_id}', 'Tenant 1');")
            )
            conn.execute(
                text(f"INSERT INTO tenants (id, name) VALUES ('{tenant2_id}', 'Tenant 2');")
            )

            # Disable RLS temporarily to insert test data
            conn.execute(text("ALTER TABLE users DISABLE ROW LEVEL SECURITY;"))

            # Insert users for each tenant
            conn.execute(
                text(
                    f"INSERT INTO users (tenant_id, email) VALUES ('{tenant1_id}', 'user1@tenant1.com');"
                )
            )
            conn.execute(
                text(
                    f"INSERT INTO users (tenant_id, email) VALUES ('{tenant2_id}', 'user2@tenant2.com');"
                )
            )

            # Re-enable RLS
            conn.execute(text("ALTER TABLE users ENABLE ROW LEVEL SECURITY;"))

            # Query as tenant 1 - should only see tenant 1 users
            with temp_tenant_context(conn, tenant1_id):
                result = conn.execute(text("SELECT email FROM users;")).fetchall()
                emails = [row[0] for row in result]
                assert "user1@tenant1.com" in emails
                assert "user2@tenant2.com" not in emails

            # Query as tenant 2 - should only see tenant 2 users
            with temp_tenant_context(conn, tenant2_id):
                result = conn.execute(text("SELECT email FROM users;")).fetchall()
                emails = [row[0] for row in result]
                assert "user2@tenant2.com" in emails
                assert "user1@tenant1.com" not in emails


class TestIndexes:
    """Test database indexes"""

    @pytest.mark.requires_db
    def test_properties_has_tenant_apn_hash_index(self, db_engine):
        """Properties should have unique index on (tenant_id, apn_hash)"""
        inspector = inspect(db_engine)
        indexes = inspector.get_indexes("properties")

        tenant_apn_index = None
        for idx in indexes:
            if idx["name"] == "ix_properties_tenant_apn_hash":
                tenant_apn_index = idx
                break

        assert tenant_apn_index is not None, "Composite index on tenant_id + apn_hash not found"
        assert tenant_apn_index["unique"] is True, "Index should be unique"
        assert "tenant_id" in tenant_apn_index["column_names"]
        assert "apn_hash" in tenant_apn_index["column_names"]

    @pytest.mark.requires_db
    def test_users_has_email_index(self, db_engine):
        """Users should have unique index on email"""
        inspector = inspect(db_engine)
        indexes = inspector.get_indexes("users")

        email_index = None
        for idx in indexes:
            if "email" in idx["column_names"]:
                email_index = idx
                break

        assert email_index is not None, "Index on email not found"
        assert email_index["unique"] is True, "Email index should be unique"


class TestTriggers:
    """Test database triggers"""

    @pytest.mark.requires_db
    def test_updated_at_trigger_exists_for_tenants(self, db_engine):
        """Trigger for updated_at should exist on tenants table"""
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM pg_trigger
                    WHERE tgname = 'update_tenants_updated_at';
                """)
            ).scalar()
            assert result == 1, "Trigger 'update_tenants_updated_at' not found"

    @pytest.mark.requires_db
    def test_updated_at_trigger_works(self, db_engine):
        """Trigger should auto-update updated_at timestamp"""
        with db_engine.begin() as conn:
            # Insert a tenant
            tenant_id = str(uuid.uuid4())
            conn.execute(
                text(
                    f"INSERT INTO tenants (id, name) VALUES ('{tenant_id}', 'Test Tenant');"
                )
            )

            # Get initial updated_at
            initial_updated_at = conn.execute(
                text(f"SELECT updated_at FROM tenants WHERE id = '{tenant_id}';")
            ).scalar()

            # Wait a moment and update
            import time

            time.sleep(0.1)
            conn.execute(
                text(
                    f"UPDATE tenants SET name = 'Updated Tenant' WHERE id = '{tenant_id}';"
                )
            )

            # Get new updated_at
            new_updated_at = conn.execute(
                text(f"SELECT updated_at FROM tenants WHERE id = '{tenant_id}';")
            ).scalar()

            # Verify updated_at changed
            assert (
                new_updated_at > initial_updated_at
            ), "updated_at should be auto-updated by trigger"
