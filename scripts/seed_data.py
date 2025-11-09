"""
Seed Data Script for Real Estate OS
Creates test data for development and testing
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import random
from api.database import get_db_context
from api.auth import get_password_hash
from db.models import (
    Team, User, UserRole, Property, PropertyStage,
    Template, CommunicationType, PropertyTimeline,
    Task, TaskStatus, TaskPriority, OpenDataSource
)

# Sample data
SAMPLE_ADDRESSES = [
    ("123 Main St", "Los Angeles", "CA", "90001", 34.0522, -118.2437),
    ("456 Oak Ave", "San Diego", "CA", "92101", 32.7157, -117.1611),
    ("789 Pine Rd", "San Francisco", "CA", "94102", 37.7749, -122.4194),
    ("321 Elm Dr", "Sacramento", "CA", "95814", 38.5816, -121.4944),
    ("654 Maple Ln", "Fresno", "CA", "93721", 36.7378, -119.7871),
    ("987 Cedar Way", "Long Beach", "CA", "90802", 33.7701, -118.1937),
    ("147 Birch Blvd", "Oakland", "CA", "94612", 37.8044, -122.2712),
    ("258 Spruce Ct", "Bakersfield", "CA", "93301", 35.3733, -119.0187),
    ("369 Willow Pl", "Anaheim", "CA", "92805", 33.8366, -117.9143),
    ("741 Ash St", "Santa Ana", "CA", "92701", 33.7455, -117.8677),
]

SAMPLE_OWNER_NAMES = [
    "John Smith", "Mary Johnson", "Robert Williams", "Patricia Brown",
    "Michael Jones", "Jennifer Garcia", "William Miller", "Linda Davis",
    "David Rodriguez", "Barbara Martinez", "Richard Wilson", "Susan Anderson",
    "Joseph Taylor", "Jessica Thomas", "Thomas Jackson", "Sarah White"
]

PROPERTY_TYPES = ["Single Family", "Condo", "Townhouse", "Multi-Family", "Land"]

def generate_sample_properties(team_id: int, count: int = 50):
    """Generate sample properties"""
    properties = []

    for i in range(count):
        # Random address from samples
        addr_idx = i % len(SAMPLE_ADDRESSES)
        address, city, state, zip_code, lat, lon = SAMPLE_ADDRESSES[addr_idx]
        street_num = random.randint(100, 9999)

        # Random stage with distribution (more in earlier stages)
        stage_weights = [0.3, 0.25, 0.2, 0.15, 0.05, 0.03, 0.02]
        stages = [PropertyStage.NEW, PropertyStage.OUTREACH, PropertyStage.QUALIFIED,
                 PropertyStage.NEGOTIATION, PropertyStage.UNDER_CONTRACT,
                 PropertyStage.CLOSED_WON, PropertyStage.CLOSED_LOST]
        stage = random.choices(stages, weights=stage_weights)[0]

        # Random property characteristics
        beds = random.choice([2, 3, 3, 4, 4, 5])
        baths = random.choice([1.0, 1.5, 2.0, 2.0, 2.5, 3.0])
        sqft = random.randint(1000, 3500)
        lot_size = random.randint(4000, 12000)
        year_built = random.randint(1960, 2020)

        # Valuation
        assessed_value = random.randint(200000, 800000)
        market_value = assessed_value * random.uniform(0.9, 1.1)
        arv = market_value * random.uniform(1.1, 1.3)
        repair_estimate = random.randint(10000, 80000)

        # Scoring
        bird_dog_score = random.uniform(0.3, 0.95)
        propensity_to_sell = random.uniform(0.2, 0.9)

        # Score reasons
        score_reasons = []
        if propensity_to_sell > 0.7:
            score_reasons.append({"reason": "High propensity to sell", "weight": 0.25})
        if assessed_value < market_value * 0.85:
            score_reasons.append({"reason": "Below market assessment", "weight": 0.15})
        if year_built < 1980:
            score_reasons.append({"reason": "Older property (renovation opportunity)", "weight": 0.10})

        # Engagement tracking
        touch_count = random.randint(0, 10) if stage != PropertyStage.NEW else 0
        email_opens = random.randint(0, touch_count * 2)
        reply_count = random.randint(0, 3) if touch_count > 3 else 0

        # Dates
        created_days_ago = random.randint(1, 90)
        created_at = datetime.utcnow() - timedelta(days=created_days_ago)

        last_contact = None
        last_reply = None
        if stage in [PropertyStage.OUTREACH, PropertyStage.QUALIFIED, PropertyStage.NEGOTIATION]:
            last_contact = datetime.utcnow() - timedelta(days=random.randint(1, 30))
            if reply_count > 0:
                last_reply = datetime.utcnow() - timedelta(days=random.randint(1, 14))

        property = Property(
            team_id=team_id,
            address=f"{street_num} {address}",
            city=city,
            state=state,
            zip_code=zip_code,
            latitude=lat + random.uniform(-0.1, 0.1),
            longitude=lon + random.uniform(-0.1, 0.1),
            owner_name=random.choice(SAMPLE_OWNER_NAMES),
            owner_mailing_address=f"{random.randint(100, 999)} {random.choice(['N', 'S', 'E', 'W'])} {random.choice(['Main', 'Oak', 'Pine'])} St, {city}, {state} {zip_code}",
            beds=beds,
            baths=baths,
            sqft=sqft,
            lot_size=lot_size,
            year_built=year_built,
            property_type=random.choice(PROPERTY_TYPES),
            assessed_value=assessed_value,
            market_value_estimate=market_value,
            arv=arv,
            repair_estimate=repair_estimate,
            current_stage=stage,
            stage_changed_at=created_at + timedelta(days=random.randint(0, created_days_ago)),
            last_contact_date=last_contact,
            last_reply_date=last_reply,
            touch_count=touch_count,
            email_opens=email_opens,
            reply_count=reply_count,
            bird_dog_score=bird_dog_score,
            score_reasons=score_reasons,
            propensity_to_sell=propensity_to_sell,
            probability_of_close=random.uniform(0.1, 0.9),
            expected_value=random.randint(5000, 50000),
            data_quality_score=random.uniform(0.7, 1.0),
            created_at=created_at
        )

        properties.append(property)

    return properties

def generate_sample_templates(team_id: int):
    """Generate sample email templates"""
    templates = [
        Template(
            team_id=team_id,
            name="Initial Outreach - Direct Offer",
            type=CommunicationType.EMAIL,
            applicable_stages=["outreach"],
            subject_template="Quick Question About {property.address}",
            body_template="""Hi {owner_name},

My name is {user_name} and I'm reaching out about your property at {property.address}.

I work with real estate investors who are actively looking for properties in {city}. I noticed your property and wanted to see if you might be interested in discussing a potential offer.

Would you be open to a quick 5-minute conversation?

Best regards,
{user_name}
{team_name}""",
            times_used=random.randint(50, 200),
            open_rate=random.uniform(0.15, 0.35),
            reply_rate=random.uniform(0.03, 0.12),
            meeting_rate=random.uniform(0.01, 0.05),
            is_champion=True
        ),
        Template(
            team_id=team_id,
            name="Follow-Up #1",
            type=CommunicationType.EMAIL,
            applicable_stages=["outreach", "qualified"],
            subject_template="Following Up - {property.address}",
            body_template="""Hi {owner_name},

Just wanted to follow up on my previous message about {property.address}.

I have investors ready to make offers on properties in your area. Even if you're not interested right now, would you be open to me keeping in touch for the future?

Thanks,
{user_name}""",
            times_used=random.randint(40, 150),
            open_rate=random.uniform(0.10, 0.25),
            reply_rate=random.uniform(0.02, 0.08)
        ),
        Template(
            team_id=team_id,
            name="Negotiation - Deal Terms",
            type=CommunicationType.EMAIL,
            applicable_stages=["negotiation"],
            subject_template="Offer Details for {property.address}",
            body_template="""Hi {owner_name},

Thank you for your interest in moving forward. I'm excited to present our offer for {property.address}.

Based on our analysis:
- Estimated ARV: ${property.arv:,.0f}
- Estimated Repairs: ${property.repair_estimate:,.0f}
- Our Offer: [TO BE DISCUSSED]

I've attached a detailed investment memo with comparable sales and our analysis.

When would be a good time to discuss?

Best,
{user_name}""",
            times_used=random.randint(20, 80),
            open_rate=random.uniform(0.40, 0.70),
            reply_rate=random.uniform(0.15, 0.40)
        ),
        Template(
            team_id=team_id,
            name="SMS - Quick Check-in",
            type=CommunicationType.SMS,
            applicable_stages=["outreach", "qualified"],
            subject_template=None,
            body_template="Hi {owner_name}, {user_name} here. Quick question about {property.address} - interested in selling? Text YES for details.",
            times_used=random.randint(30, 100),
            reply_rate=random.uniform(0.05, 0.15)
        )
    ]

    return templates

def create_open_data_sources():
    """Create open data source catalog"""
    sources = [
        OpenDataSource(
            name="FEMA_NFHL",
            source_type="government",
            data_types=["flood_zones", "base_flood_elevation"],
            coverage_areas=["US_nationwide"],
            api_endpoint="https://hazards.fema.gov/gis/nfhl/services/",
            license_type="Public Domain",
            cost_per_request=0.0,
            data_quality_rating=0.95,
            freshness_days=90,
            is_active=True
        ),
        OpenDataSource(
            name="OpenAddresses",
            source_type="community",
            data_types=["addresses", "geocoding"],
            coverage_areas=["Global"],
            api_endpoint="https://batch.openaddresses.io/",
            license_type="CC0/ODbL",
            cost_per_request=0.0,
            data_quality_rating=0.85,
            freshness_days=90,
            is_active=True
        ),
        OpenDataSource(
            name="MS_Building_Footprints",
            source_type="community",
            data_types=["building_footprints", "building_confidence"],
            coverage_areas=["US_nationwide"],
            api_endpoint="https://github.com/Microsoft/USBuildingFootprints",
            license_type="ODbL",
            cost_per_request=0.0,
            data_quality_rating=0.90,
            freshness_days=365,
            is_active=True
        ),
        OpenDataSource(
            name="ATTOM",
            source_type="paid",
            data_types=["property_details", "sales_history", "ownership", "liens"],
            coverage_areas=["US_nationwide"],
            api_endpoint="https://api.gateway.attomdata.com/propertyapi/v1.0.0",
            license_type="Proprietary",
            cost_per_request=0.10,
            data_quality_rating=0.95,
            freshness_days=30,
            is_active=False  # Disabled by default (requires API key)
        )
    ]

    return sources

def main():
    """Main seed function"""
    print("🌱 Seeding Real Estate OS Database...")
    print("")

    with get_db_context() as db:
        # Create team
        print("Creating team...")
        team = Team(
            name="Demo Real Estate Team",
            subscription_tier="professional",
            monthly_budget_cap=1000.0
        )
        db.add(team)
        db.flush()
        print(f"✓ Created team: {team.name} (ID: {team.id})")

        # Create users
        print("\nCreating users...")
        # Default password for all demo users: "password123"
        default_password_hash = get_password_hash("password123")

        users = [
            User(
                team_id=team.id,
                email="admin@demo.com",
                full_name="Admin User",
                password_hash=default_password_hash,
                role=UserRole.ADMIN,
                is_active=True
            ),
            User(
                team_id=team.id,
                email="manager@demo.com",
                full_name="Manager User",
                password_hash=default_password_hash,
                role=UserRole.MANAGER,
                is_active=True
            ),
            User(
                team_id=team.id,
                email="agent@demo.com",
                full_name="Agent User",
                password_hash=default_password_hash,
                role=UserRole.AGENT,
                is_active=True
            ),
            User(
                team_id=team.id,
                email="viewer@demo.com",
                full_name="Viewer User",
                password_hash=default_password_hash,
                role=UserRole.VIEWER,
                is_active=True
            )
        ]

        for user in users:
            db.add(user)
            print(f"✓ Created user: {user.email} ({user.role.value})")

        db.flush()

        # Create properties
        print(f"\nCreating 50 sample properties...")
        properties = generate_sample_properties(team.id, count=50)

        stage_counts = {}
        for prop in properties:
            db.add(prop)
            stage_counts[prop.current_stage] = stage_counts.get(prop.current_stage, 0) + 1

        db.flush()

        print(f"✓ Created {len(properties)} properties")
        for stage, count in stage_counts.items():
            print(f"  - {stage.value}: {count}")

        # Create templates
        print("\nCreating sample templates...")
        templates = generate_sample_templates(team.id)
        for template in templates:
            db.add(template)
            print(f"✓ Created template: {template.name} ({template.type.value})")

        db.flush()

        # Create open data sources
        print("\nCreating open data source catalog...")
        sources = create_open_data_sources()
        for source in sources:
            db.add(source)
            print(f"✓ Created data source: {source.name} ({source.source_type})")

        db.flush()

        # Create some timeline events for variety
        print("\nCreating sample timeline events...")
        event_count = 0
        for i, prop in enumerate(properties[:20]):  # Add events to first 20 properties
            if prop.current_stage != PropertyStage.NEW:
                event = PropertyTimeline(
                    property_id=prop.id,
                    event_type="property_created",
                    event_title="Property Added to Pipeline",
                    event_description=f"Added {prop.address} to pipeline",
                    created_at=prop.created_at
                )
                db.add(event)
                event_count += 1

                if prop.current_stage in [PropertyStage.OUTREACH, PropertyStage.QUALIFIED, PropertyStage.NEGOTIATION]:
                    event = PropertyTimeline(
                        property_id=prop.id,
                        event_type="email_sent",
                        event_title="Outreach Email Sent",
                        event_description="Initial outreach email sent to owner",
                        created_at=prop.created_at + timedelta(days=1)
                    )
                    db.add(event)
                    event_count += 1

        db.flush()
        print(f"✓ Created {event_count} timeline events")

        # Create some tasks
        print("\nCreating sample tasks...")
        task_count = 0
        for prop in properties[:15]:  # Add tasks to first 15 properties
            if prop.current_stage in [PropertyStage.OUTREACH, PropertyStage.QUALIFIED, PropertyStage.NEGOTIATION]:
                task = Task(
                    property_id=prop.id,
                    assigned_user_id=users[2].id,  # Agent user
                    title=f"Follow up on {prop.address}",
                    description="Check if owner received memo and is interested",
                    status=TaskStatus.PENDING if random.random() > 0.3 else TaskStatus.COMPLETED,
                    priority=random.choice([TaskPriority.MEDIUM, TaskPriority.HIGH]),
                    due_at=datetime.utcnow() + timedelta(days=random.randint(1, 7)),
                    sla_hours=24
                )
                db.add(task)
                task_count += 1

        db.flush()
        print(f"✓ Created {task_count} tasks")

        # Commit all changes
        db.commit()

        print("\n" + "="*50)
        print("✅ Database seeded successfully!")
        print("="*50)
        print("\nTest Credentials:")
        print("  Admin:   admin@demo.com   / password123")
        print("  Manager: manager@demo.com / password123")
        print("  Agent:   agent@demo.com   / password123")
        print("  Viewer:  viewer@demo.com  / password123")
        print("\nLogin at: POST /api/v1/auth/login")
        print("  {\"email\": \"admin@demo.com\", \"password\": \"password123\"}")
        print("\nYou'll receive a JWT token to use in subsequent requests:")
        print("  Authorization: Bearer <token>")

if __name__ == "__main__":
    main()
