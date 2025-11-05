"""Create admin user script."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, init_db
from models import Organization, User, Role, Permission, UserRole, RolePermission
from services.auth import hash_password


def create_admin_user(email, password, organization_name):
    """Create an admin user with full permissions."""
    db = SessionLocal()

    try:
        # Initialize database tables
        init_db()

        # Create organization if it doesn't exist
        org = db.query(Organization).filter_by(name=organization_name).first()
        if not org:
            org = Organization(
                name=organization_name,
                domain=organization_name.lower().replace(" ", "-") + ".com",
                is_active=True,
                settings='{"theme": "default"}'
            )
            db.add(org)
            db.flush()
            print(f"Created organization: {organization_name}")
        else:
            print(f"Using existing organization: {organization_name}")

        # Create admin role if it doesn't exist
        admin_role = db.query(Role).filter_by(name="Admin", is_system=True).first()
        if not admin_role:
            admin_role = Role(
                name="Admin",
                description="Full system access",
                is_system=True
            )
            db.add(admin_role)
            db.flush()

            # Create basic permissions and assign to admin
            basic_permissions = [
                ("property.*", "All property permissions"),
                ("lead.*", "All lead permissions"),
                ("campaign.*", "All campaign permissions"),
                ("deal.*", "All deal permissions"),
                ("user.*", "All user permissions"),
                ("organization.*", "All organization permissions"),
                ("reports.*", "All report permissions"),
            ]

            for name, desc in basic_permissions:
                perm = Permission(name=name, description=desc)
                db.add(perm)
                db.flush()
                db.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))

            print("Created Admin role with permissions")
        else:
            print("Using existing Admin role")

        # Check if user already exists
        existing_user = db.query(User).filter_by(email=email).first()
        if existing_user:
            print(f"User with email {email} already exists!")
            return

        # Create admin user
        user = User(
            organization_id=org.id,
            email=email,
            hashed_password=hash_password(password),
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        db.add(user)
        db.flush()

        # Assign admin role
        db.add(UserRole(user_id=user.id, role_id=admin_role.id))

        db.commit()

        print(f"\nAdmin user created successfully!")
        print(f"Email: {email}")
        print(f"Organization: {organization_name}")
        print(f"You can now login with these credentials.")

    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <email> <password> <organization_name>")
        print("Example: python create_admin.py admin@example.com Admin123! 'My Company'")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    org_name = sys.argv[3]

    # Validate email
    if "@" not in email:
        print("Error: Invalid email address")
        sys.exit(1)

    # Validate password
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        sys.exit(1)

    create_admin_user(email, password, org_name)
