"""
Tests for authentication models
"""

import pytest
from auth.models import User, UserRole, Tenant


class TestUser:
    """Tests for User model"""

    def test_create_user(self):
        """Test creating a user"""
        user = User(
            id="user-123",
            tenant_id="tenant-1",
            email="test@example.com",
            full_name="Test User",
            role=UserRole.ANALYST,
        )

        assert user.id == "user-123"
        assert user.tenant_id == "tenant-1"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.ANALYST
        assert user.is_active is True

    def test_admin_has_all_permissions(self):
        """Test that admin has all permissions"""
        user = User(
            id="user-admin",
            tenant_id="tenant-1",
            email="admin@example.com",
            full_name="Admin User",
            role=UserRole.ADMIN,
        )

        assert user.has_permission("properties:read") is True
        assert user.has_permission("properties:create") is True
        assert user.has_permission("properties:delete") is True
        assert user.has_permission("any:permission") is True

    def test_analyst_permissions(self):
        """Test analyst role permissions"""
        user = User(
            id="user-123",
            tenant_id="tenant-1",
            email="analyst@example.com",
            full_name="Analyst",
            role=UserRole.ANALYST,
        )

        # Should have analyst permissions
        assert user.has_permission("properties:read") is True
        assert user.has_permission("properties:create") is True
        assert user.has_permission("properties:update") is True
        assert user.has_permission("timeline:read") is True
        assert user.has_permission("timeline:write") is True

        # Should not have permissions outside their role
        assert user.has_permission("outreach:write") is False

    def test_viewer_permissions(self):
        """Test viewer role permissions"""
        user = User(
            id="user-123",
            tenant_id="tenant-1",
            email="viewer@example.com",
            full_name="Viewer",
            role=UserRole.VIEWER,
        )

        # Should have read-only permissions
        assert user.has_permission("properties:read") is True
        assert user.has_permission("scores:read") is True
        assert user.has_permission("timeline:read") is True

        # Should not have write permissions
        assert user.has_permission("properties:create") is False
        assert user.has_permission("properties:update") is False
        assert user.has_permission("timeline:write") is False

    def test_underwriter_permissions(self):
        """Test underwriter role permissions"""
        user = User(
            id="user-123",
            tenant_id="tenant-1",
            email="underwriter@example.com",
            full_name="Underwriter",
            role=UserRole.UNDERWRITER,
        )

        # Should have underwriter permissions
        assert user.has_permission("properties:read") is True
        assert user.has_permission("scores:read") is True
        assert user.has_permission("memos:read") is True
        assert user.has_permission("timeline:read") is True
        assert user.has_permission("timeline:write") is True

        # Should not have discovery permissions
        assert user.has_permission("properties:create") is False

    def test_ops_permissions(self):
        """Test ops role permissions"""
        user = User(
            id="user-123",
            tenant_id="tenant-1",
            email="ops@example.com",
            full_name="Ops",
            role=UserRole.OPS,
        )

        # Should have ops permissions
        assert user.has_permission("properties:read") is True
        assert user.has_permission("properties:update") is True
        assert user.has_permission("outreach:read") is True
        assert user.has_permission("outreach:write") is True
        assert user.has_permission("timeline:read") is True
        assert user.has_permission("timeline:write") is True


class TestTenant:
    """Tests for Tenant model"""

    def test_create_tenant(self):
        """Test creating a tenant"""
        tenant = Tenant(
            id="tenant-1",
            name="Acme Corp",
            slug="acme-corp",
        )

        assert tenant.id == "tenant-1"
        assert tenant.name == "Acme Corp"
        assert tenant.slug == "acme-corp"
        assert tenant.is_active is True


class TestUserRole:
    """Tests for UserRole enum"""

    def test_role_values(self):
        """Test role enum values"""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.UNDERWRITER.value == "underwriter"
        assert UserRole.OPS.value == "ops"
        assert UserRole.VIEWER.value == "viewer"

    def test_create_role_from_string(self):
        """Test creating role from string"""
        role = UserRole("analyst")
        assert role == UserRole.ANALYST

    def test_all_roles_defined(self):
        """Test that all expected roles are defined"""
        roles = {r.value for r in UserRole}
        expected = {"admin", "analyst", "underwriter", "ops", "viewer"}
        assert roles == expected
