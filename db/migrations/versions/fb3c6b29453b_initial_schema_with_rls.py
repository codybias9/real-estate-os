"""initial_schema_with_rls

Revision ID: fb3c6b29453b
Revises: 
Create Date: 2025-11-02 23:01:54.910131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb3c6b29453b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable UUID extension
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_name"), "tenants", ["name"], unique=False)

    # Create users table with tenant_id for RLS
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)

    # Create properties table with tenant_id for RLS
    op.create_table(
        "properties",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("apn", sa.String(length=50), nullable=True),
        sa.Column("apn_hash", sa.String(length=64), nullable=True),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("zip_code", sa.String(length=10), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("owner_name", sa.String(length=255), nullable=True),
        sa.Column("owner_type", sa.String(length=50), nullable=True),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Float(), nullable=True),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("lot_size", sa.Float(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("score_reasons", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'discovered'"), nullable=False),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_properties_apn"), "properties", ["apn"], unique=False)
    op.create_index(op.f("ix_properties_apn_hash"), "properties", ["apn_hash"], unique=False)
    op.create_index(op.f("ix_properties_city"), "properties", ["city"], unique=False)
    op.create_index(op.f("ix_properties_state"), "properties", ["state"], unique=False)
    op.create_index(op.f("ix_properties_status"), "properties", ["status"], unique=False)
    op.create_index(op.f("ix_properties_tenant_id"), "properties", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_properties_zip_code"), "properties", ["zip_code"], unique=False)

    # Composite index for tenant_id + apn_hash to enforce uniqueness per tenant
    op.create_index(
        "ix_properties_tenant_apn_hash",
        "properties",
        ["tenant_id", "apn_hash"],
        unique=True,
        postgresql_where=sa.text("apn_hash IS NOT NULL"),
    )

    # Create ping table (no tenant_id, used for health checks)
    op.create_table(
        "ping",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Enable Row-Level Security on users and properties tables
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE properties ENABLE ROW LEVEL SECURITY;")

    # Create RLS policy for users - users can only see their own tenant's users
    op.execute("""
        CREATE POLICY tenant_isolation_users ON users
        FOR ALL
        TO PUBLIC
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
    """)

    # Create RLS policy for properties - users can only see their own tenant's properties
    op.execute("""
        CREATE POLICY tenant_isolation_properties ON properties
        FOR ALL
        TO PUBLIC
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
    """)

    # Create function to set updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create triggers for updated_at
    op.execute("""
        CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    op.execute("""
        CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    op.execute("""
        CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_properties_updated_at ON properties;")
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users;")
    op.execute("DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants;")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_properties ON properties;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_users ON users;")

    # Disable RLS
    op.execute("ALTER TABLE properties DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")

    # Drop tables
    op.drop_table("ping")
    op.drop_index("ix_properties_tenant_apn_hash", table_name="properties")
    op.drop_index(op.f("ix_properties_zip_code"), table_name="properties")
    op.drop_index(op.f("ix_properties_tenant_id"), table_name="properties")
    op.drop_index(op.f("ix_properties_status"), table_name="properties")
    op.drop_index(op.f("ix_properties_state"), table_name="properties")
    op.drop_index(op.f("ix_properties_city"), table_name="properties")
    op.drop_index(op.f("ix_properties_apn_hash"), table_name="properties")
    op.drop_index(op.f("ix_properties_apn"), table_name="properties")
    op.drop_table("properties")
    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_tenants_name"), table_name="tenants")
    op.drop_table("tenants")

    # Drop UUID extension
    op.execute("DROP EXTENSION IF EXISTS \"uuid-ossp\";")

