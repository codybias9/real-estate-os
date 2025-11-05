"""Seed data script for populating the database with sample data."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from decimal import Decimal
import random

from database import SessionLocal, init_db
from models import (
    Organization, User, Role, Permission, UserRole, RolePermission,
    Property, PropertyImage, PropertyValuation,
    Lead, LeadActivity,
    Campaign, CampaignTemplate,
    Deal, Transaction, Portfolio
)
from models.property import PropertyType, PropertyStatus
from models.lead import LeadSource, LeadStatus
from models.campaign import CampaignType, CampaignStatus
from models.deal import DealType, DealStage, TransactionType
from services.auth import hash_password


def create_permissions(db):
    """Create default permissions."""
    permissions = [
        # Property permissions
        ("property.create", "Create properties"),
        ("property.read", "View properties"),
        ("property.update", "Update properties"),
        ("property.delete", "Delete properties"),
        # Lead permissions
        ("lead.create", "Create leads"),
        ("lead.read", "View leads"),
        ("lead.update", "Update leads"),
        ("lead.delete", "Delete leads"),
        ("lead.assign", "Assign leads"),
        # Campaign permissions
        ("campaign.create", "Create campaigns"),
        ("campaign.read", "View campaigns"),
        ("campaign.update", "Update campaigns"),
        ("campaign.delete", "Delete campaigns"),
        ("campaign.send", "Send campaigns"),
        # Deal permissions
        ("deal.create", "Create deals"),
        ("deal.read", "View deals"),
        ("deal.update", "Update deals"),
        ("deal.delete", "Delete deals"),
        # User management
        ("user.create", "Create users"),
        ("user.read", "View users"),
        ("user.update", "Update users"),
        ("user.delete", "Delete users"),
        # Organization settings
        ("organization.settings", "Manage organization settings"),
        ("organization.billing", "Manage billing"),
        # Reports
        ("reports.view", "View reports"),
        ("reports.export", "Export reports"),
    ]

    permission_objs = []
    for name, description in permissions:
        perm = Permission(name=name, description=description)
        db.add(perm)
        permission_objs.append(perm)

    db.commit()
    print(f"Created {len(permission_objs)} permissions")
    return permission_objs


def create_roles(db, permissions):
    """Create default roles."""
    # Admin role - all permissions
    admin_role = Role(
        name="Admin",
        description="Full system access",
        is_system=True
    )
    db.add(admin_role)
    db.flush()

    for perm in permissions:
        db.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))

    # Manager role - most permissions except user management
    manager_role = Role(
        name="Manager",
        description="Manage properties, leads, campaigns, and deals",
        is_system=True
    )
    db.add(manager_role)
    db.flush()

    manager_perms = [p for p in permissions if not p.name.startswith("user.") and not p.name.startswith("organization.")]
    for perm in manager_perms:
        db.add(RolePermission(role_id=manager_role.id, permission_id=perm.id))

    # Agent role - basic access
    agent_role = Role(
        name="Agent",
        description="Basic access to properties and leads",
        is_system=True
    )
    db.add(agent_role)
    db.flush()

    agent_perms = [p for p in permissions if p.name.endswith(".read") or p.name.endswith(".create") or p.name in ["lead.update", "property.update"]]
    for perm in agent_perms:
        db.add(RolePermission(role_id=agent_role.id, permission_id=perm.id))

    db.commit()
    print(f"Created 3 default roles: Admin, Manager, Agent")
    return {"admin": admin_role, "manager": manager_role, "agent": agent_role}


def create_organizations(db):
    """Create sample organizations."""
    orgs = [
        Organization(
            name="Acme Real Estate",
            domain="acme-realestate.com",
            is_active=True,
            settings='{"theme": "blue", "timezone": "America/New_York"}'
        ),
        Organization(
            name="Premium Properties LLC",
            domain="premium-properties.com",
            is_active=True,
            settings='{"theme": "green", "timezone": "America/Los_Angeles"}'
        ),
    ]

    for org in orgs:
        db.add(org)

    db.commit()
    print(f"Created {len(orgs)} organizations")
    return orgs


def create_users(db, organizations, roles):
    """Create sample users."""
    users = []

    # Create users for first organization
    org = organizations[0]

    # Admin user
    admin = User(
        organization_id=org.id,
        email="admin@acme-realestate.com",
        hashed_password=hash_password("Admin123!"),
        first_name="John",
        last_name="Admin",
        phone="+1234567890",
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    db.flush()
    db.add(UserRole(user_id=admin.id, role_id=roles["admin"].id))
    users.append(admin)

    # Manager user
    manager = User(
        organization_id=org.id,
        email="manager@acme-realestate.com",
        hashed_password=hash_password("Manager123!"),
        first_name="Sarah",
        last_name="Manager",
        phone="+1234567891",
        is_active=True,
        is_verified=True,
    )
    db.add(manager)
    db.flush()
    db.add(UserRole(user_id=manager.id, role_id=roles["manager"].id))
    users.append(manager)

    # Agent users
    agent_names = [
        ("Mike", "Agent", "+1234567892"),
        ("Emily", "Sales", "+1234567893"),
        ("David", "Broker", "+1234567894"),
    ]

    for first, last, phone in agent_names:
        agent = User(
            organization_id=org.id,
            email=f"{first.lower()}@acme-realestate.com",
            hashed_password=hash_password("Agent123!"),
            first_name=first,
            last_name=last,
            phone=phone,
            is_active=True,
            is_verified=True,
        )
        db.add(agent)
        db.flush()
        db.add(UserRole(user_id=agent.id, role_id=roles["agent"].id))
        users.append(agent)

    db.commit()
    print(f"Created {len(users)} users")
    return users


def create_properties(db, organization, users):
    """Create sample properties."""
    properties_data = [
        {
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "property_type": PropertyType.SINGLE_FAMILY,
            "status": PropertyStatus.AVAILABLE,
            "price": Decimal("550000.00"),
            "bedrooms": 3,
            "bathrooms": Decimal("2.5"),
            "square_feet": 2000,
            "year_built": 2010,
            "description": "Beautiful single family home in prime location",
        },
        {
            "address": "456 Oak Ave",
            "city": "New York",
            "state": "NY",
            "zip_code": "10002",
            "property_type": PropertyType.CONDO,
            "status": PropertyStatus.UNDER_CONTRACT,
            "price": Decimal("425000.00"),
            "bedrooms": 2,
            "bathrooms": Decimal("2.0"),
            "square_feet": 1500,
            "year_built": 2015,
            "description": "Modern condo with city views",
        },
        {
            "address": "789 Pine Rd",
            "city": "Brooklyn",
            "state": "NY",
            "zip_code": "11201",
            "property_type": PropertyType.MULTI_FAMILY,
            "status": PropertyStatus.AVAILABLE,
            "price": Decimal("875000.00"),
            "bedrooms": 6,
            "bathrooms": Decimal("4.0"),
            "square_feet": 3500,
            "year_built": 2005,
            "description": "Investment opportunity - 3 unit building",
        },
        {
            "address": "321 Elm St",
            "city": "Queens",
            "state": "NY",
            "zip_code": "11354",
            "property_type": PropertyType.TOWNHOUSE,
            "status": PropertyStatus.SOLD,
            "price": Decimal("650000.00"),
            "bedrooms": 4,
            "bathrooms": Decimal("3.0"),
            "square_feet": 2500,
            "year_built": 2008,
            "description": "Spacious townhouse with garage",
        },
        {
            "address": "555 Beach Blvd",
            "city": "Manhattan",
            "state": "NY",
            "zip_code": "10280",
            "property_type": PropertyType.COMMERCIAL,
            "status": PropertyStatus.AVAILABLE,
            "price": Decimal("1250000.00"),
            "square_feet": 5000,
            "year_built": 2018,
            "description": "Prime commercial space near waterfront",
        },
    ]

    properties = []
    for i, prop_data in enumerate(properties_data):
        prop = Property(
            organization_id=organization.id,
            created_by=users[random.randint(0, min(2, len(users)-1))].id,
            **prop_data
        )
        db.add(prop)
        db.flush()

        # Add property images
        for j in range(random.randint(2, 5)):
            image = PropertyImage(
                property_id=prop.id,
                url=f"https://example.com/images/property_{prop.id}_{j+1}.jpg",
                title=f"View {j+1}",
                is_primary=(j == 0)
            )
            db.add(image)

        # Add property valuation
        valuation = PropertyValuation(
            property_id=prop.id,
            value=prop.price,
            valuation_date=datetime.utcnow(),
            source="manual",
            notes="Initial valuation"
        )
        db.add(valuation)

        properties.append(prop)

    db.commit()
    print(f"Created {len(properties)} properties with images and valuations")
    return properties


def create_leads(db, organization, users):
    """Create sample leads."""
    leads_data = [
        {
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice.johnson@example.com",
            "phone": "+1555001001",
            "source": LeadSource.WEBSITE,
            "status": LeadStatus.NEW,
            "budget": Decimal("500000.00"),
            "timeline": "3-6 months",
        },
        {
            "first_name": "Bob",
            "last_name": "Smith",
            "email": "bob.smith@example.com",
            "phone": "+1555001002",
            "source": LeadSource.REFERRAL,
            "status": LeadStatus.CONTACTED,
            "budget": Decimal("750000.00"),
            "timeline": "0-3 months",
        },
        {
            "first_name": "Carol",
            "last_name": "Williams",
            "email": "carol.williams@example.com",
            "phone": "+1555001003",
            "source": LeadSource.SOCIAL_MEDIA,
            "status": LeadStatus.QUALIFIED,
            "budget": Decimal("400000.00"),
            "timeline": "6-12 months",
        },
        {
            "first_name": "David",
            "last_name": "Brown",
            "email": "david.brown@example.com",
            "phone": "+1555001004",
            "source": LeadSource.EMAIL,
            "status": LeadStatus.NURTURING,
            "budget": Decimal("600000.00"),
            "timeline": "3-6 months",
        },
        {
            "first_name": "Eva",
            "last_name": "Martinez",
            "email": "eva.martinez@example.com",
            "phone": "+1555001005",
            "source": LeadSource.PHONE,
            "status": LeadStatus.QUALIFIED,
            "budget": Decimal("850000.00"),
            "timeline": "0-3 months",
        },
    ]

    leads = []
    for lead_data in leads_data:
        lead = Lead(
            organization_id=organization.id,
            created_by=users[0].id,
            assigned_to=users[random.randint(1, min(3, len(users)-1))].id if len(users) > 1 else None,
            **lead_data
        )
        db.add(lead)
        db.flush()

        # Add lead activity
        activity = LeadActivity(
            lead_id=lead.id,
            activity_type="note",
            description="Initial contact made",
            created_by=users[0].id
        )
        db.add(activity)

        leads.append(lead)

    db.commit()
    print(f"Created {len(leads)} leads with activities")
    return leads


def create_campaigns(db, organization, users):
    """Create sample campaigns."""
    # Create campaign template
    template = CampaignTemplate(
        organization_id=organization.id,
        name="New Property Announcement",
        description="Template for announcing new property listings",
        subject="New Property Listing: {{property_address}}",
        content="Hi {{first_name}},\n\nWe have a new property that matches your criteria:\n\n{{property_details}}\n\nContact us to schedule a viewing!",
        campaign_type=CampaignType.EMAIL
    )
    db.add(template)
    db.flush()

    # Create campaign
    campaign = Campaign(
        organization_id=organization.id,
        created_by=users[0].id,
        template_id=template.id,
        name="Fall 2024 Property Showcase",
        campaign_type=CampaignType.EMAIL,
        status=CampaignStatus.COMPLETED,
        subject="Check out our latest properties!",
        content="Browse our newest listings this fall season.",
        scheduled_at=datetime.utcnow() - timedelta(days=7),
        sent_at=datetime.utcnow() - timedelta(days=7),
        total_recipients=50,
        sent_count=50,
        delivered_count=48,
        opened_count=32,
        clicked_count=15,
    )
    db.add(campaign)

    db.commit()
    print(f"Created 1 campaign with template")
    return campaign


def create_deals(db, organization, users, properties, leads):
    """Create sample deals."""
    deals_data = [
        {
            "property_id": properties[0].id if len(properties) > 0 else None,
            "lead_id": leads[0].id if len(leads) > 0 else None,
            "deal_type": DealType.SALE,
            "stage": DealStage.NEGOTIATION,
            "value": Decimal("550000.00"),
            "commission_rate": Decimal("5.00"),
            "probability": 75,
            "expected_close_date": datetime.utcnow().date() + timedelta(days=30),
        },
        {
            "property_id": properties[1].id if len(properties) > 1 else None,
            "lead_id": leads[1].id if len(leads) > 1 else None,
            "deal_type": DealType.SALE,
            "stage": DealStage.CONTRACT,
            "value": Decimal("425000.00"),
            "commission_rate": Decimal("5.00"),
            "probability": 90,
            "expected_close_date": datetime.utcnow().date() + timedelta(days=15),
        },
        {
            "property_id": properties[2].id if len(properties) > 2 else None,
            "lead_id": leads[2].id if len(leads) > 2 else None,
            "deal_type": DealType.LEASE,
            "stage": DealStage.PROPOSAL,
            "value": Decimal("3500.00"),
            "commission_rate": Decimal("10.00"),
            "probability": 60,
            "expected_close_date": datetime.utcnow().date() + timedelta(days=45),
        },
    ]

    deals = []
    for deal_data in deals_data:
        deal = Deal(
            organization_id=organization.id,
            created_by=users[0].id,
            assigned_to=users[random.randint(1, min(2, len(users)-1))].id if len(users) > 1 else None,
            **deal_data
        )
        db.add(deal)
        db.flush()
        deals.append(deal)

    # Add transaction to one of the deals
    if len(deals) > 1:
        transaction = Transaction(
            organization_id=organization.id,
            created_by=users[0].id,
            deal_id=deals[1].id,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("10000.00"),
            description="Earnest money deposit",
            transaction_date=datetime.utcnow().date()
        )
        db.add(transaction)

    # Create a portfolio
    portfolio = Portfolio(
        organization_id=organization.id,
        created_by=users[0].id,
        name="Investment Properties",
        description="Properties for investment purposes"
    )
    db.add(portfolio)

    db.commit()
    print(f"Created {len(deals)} deals with transactions and 1 portfolio")
    return deals


def seed_all():
    """Run all seed functions."""
    print("Starting database seeding...")

    # Initialize database
    init_db()

    # Create database session
    db = SessionLocal()

    try:
        # Create all seed data
        permissions = create_permissions(db)
        roles = create_roles(db, permissions)
        organizations = create_organizations(db)
        users = create_users(db, organizations, roles)
        properties = create_properties(db, organizations[0], users)
        leads = create_leads(db, organizations[0], users)
        campaigns = create_campaigns(db, organizations[0], users)
        deals = create_deals(db, organizations[0], users, properties, leads)

        print("\nDatabase seeding completed successfully!")
        print(f"Summary:")
        print(f"  - {len(permissions)} permissions")
        print(f"  - {len(roles)} roles")
        print(f"  - {len(organizations)} organizations")
        print(f"  - {len(users)} users")
        print(f"  - {len(properties)} properties")
        print(f"  - {len(leads)} leads")
        print(f"  - {len(deals)} deals")

        print("\nTest credentials:")
        print("  Admin: admin@acme-realestate.com / Admin123!")
        print("  Manager: manager@acme-realestate.com / Manager123!")
        print("  Agent: mike@acme-realestate.com / Agent123!")

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
