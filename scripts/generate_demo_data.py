"""Generate comprehensive demo data for the Real Estate OS platform."""

import sys
sys.path.insert(0, '/home/user/real-estate-os')

from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Property, PropertyEnrichment, PropertyScore, GeneratedDocument, Campaign
from agents.enrichment.service import EnrichmentService
from agents.scoring.scorer import PropertyScorer
from agents.docgen.service import DocumentService
from agents.outreach.email_service import EmailService
from src.scraper.property_generator import PropertyDataGenerator


def get_db_session():
    """Create database session."""
    DATABASE_URL = "postgresql://airflow:airflow@postgres:5432/airflow"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def clear_existing_data(db):
    """Clear existing demo data (optional)."""
    print("Clearing existing data...")

    # Delete in reverse order of dependencies
    db.query(GeneratedDocument).delete()
    db.query(PropertyScore).delete()
    db.query(PropertyEnrichment).delete()
    db.query(Property).delete()
    db.query(Campaign).delete()

    db.commit()
    print("✓ Existing data cleared")


def generate_properties(db, count=50):
    """Generate sample properties."""
    print(f"\nGenerating {count} properties...")

    generator = PropertyDataGenerator()
    properties_data = generator.generate_batch(count=count, source="demo_mls")

    property_ids = []

    for prop_data in properties_data:
        # Create property
        property_obj = Property(
            source=prop_data['source'],
            address=prop_data['address'],
            city=prop_data['city'],
            state=prop_data['state'],
            zip_code=prop_data['zip_code'],
            price=prop_data['price'],
            bedrooms=prop_data['bedrooms'],
            bathrooms=prop_data['bathrooms'],
            sqft=prop_data.get('sqft'),
            lot_size=prop_data.get('lot_size'),
            year_built=prop_data.get('year_built'),
            property_type=prop_data['property_type'],
            description=prop_data.get('description'),
            features=prop_data.get('features', []),
            images=prop_data.get('images', []),
            url=prop_data.get('url'),
            status='new',
        )

        db.add(property_obj)
        db.flush()  # Get the ID
        property_ids.append(property_obj.id)

    db.commit()
    print(f"✓ Created {len(property_ids)} properties")

    return property_ids


def enrich_properties(db, property_ids):
    """Enrich all properties with assessor and market data."""
    print(f"\nEnriching {len(property_ids)} properties...")

    enrichment_service = EnrichmentService(db)
    enriched_count = 0

    for prop_id in property_ids:
        try:
            enrichment_service.enrich_property(prop_id)
            enriched_count += 1

            if enriched_count % 10 == 0:
                print(f"  Enriched {enriched_count}/{len(property_ids)}...")

        except Exception as e:
            print(f"  Error enriching property {prop_id}: {e}")

    print(f"✓ Enriched {enriched_count} properties")


def score_properties(db, property_ids):
    """Score all enriched properties."""
    print(f"\nScoring {len(property_ids)} properties...")

    scorer = PropertyScorer(db)
    scored_count = 0

    for prop_id in property_ids:
        try:
            scorer.score_property(prop_id)
            scored_count += 1

            if scored_count % 10 == 0:
                print(f"  Scored {scored_count}/{len(property_ids)}...")

        except Exception as e:
            print(f"  Error scoring property {prop_id}: {e}")

    print(f"✓ Scored {scored_count} properties")


def generate_documents(db, property_ids):
    """Generate investor memos for top-scored properties."""
    print(f"\nGenerating investor memos for top properties...")

    # Get top 20 properties by score
    top_properties = (
        db.query(Property)
        .join(PropertyScore, Property.id == PropertyScore.property_id)
        .filter(PropertyScore.total_score >= 70)
        .order_by(PropertyScore.total_score.desc())
        .limit(20)
        .all()
    )

    doc_service = DocumentService(db)
    generated_count = 0

    for prop in top_properties:
        try:
            doc_service.generate_investor_memo(prop.id)
            generated_count += 1
            print(f"  Generated memo for {prop.address} (Score: {prop.property_scores[0].total_score})")

        except Exception as e:
            print(f"  Error generating memo for property {prop.id}: {e}")

    print(f"✓ Generated {generated_count} investor memos")


def create_campaigns(db):
    """Create sample email campaigns."""
    print(f"\nCreating sample campaigns...")

    campaigns_data = [
        {
            "name": "Q1 2025 High-Value Opportunities",
            "description": "Outreach to owners of properties scoring 80+ for potential acquisition",
            "status": "draft",
            "template_type": "owner_outreach",
        },
        {
            "name": "Investor Network - Best Deals",
            "description": "Share top investment opportunities with our investor network",
            "status": "draft",
            "template_type": "investor_outreach",
        },
        {
            "name": "Las Vegas Market Update",
            "description": "Property alerts for Las Vegas area investors",
            "status": "scheduled",
            "template_type": "market_update",
            "scheduled_send_date": datetime.utcnow() + timedelta(days=1),
        },
    ]

    created_campaigns = []

    for campaign_data in campaigns_data:
        campaign = Campaign(**campaign_data)
        db.add(campaign)
        db.flush()
        created_campaigns.append(campaign.id)

    db.commit()
    print(f"✓ Created {len(created_campaigns)} campaigns")

    return created_campaigns


def execute_sample_campaign(db, campaign_ids):
    """Execute one campaign to generate sample outreach logs."""
    if not campaign_ids:
        return

    print(f"\nExecuting sample campaign...")

    email_service = EmailService(db)
    campaign_id = campaign_ids[0]  # Execute first campaign

    try:
        # Send campaign
        result = email_service.send_campaign(campaign_id)
        print(f"  Sent {result['sent']} emails")

        # Simulate engagement
        if result['sent'] > 0:
            engagement = email_service.simulate_engagement(campaign_id, engagement_rate=0.4)
            print(f"  Engagement: {engagement['opened']} opens, {engagement['clicked']} clicks, {engagement['replied']} replies")

        print(f"✓ Campaign executed successfully")

    except Exception as e:
        print(f"  Error executing campaign: {e}")


def print_summary(db):
    """Print summary of demo data."""
    print("\n" + "="*60)
    print("DEMO DATA GENERATION SUMMARY")
    print("="*60)

    # Count records
    properties_count = db.query(Property).count()
    enriched_count = db.query(PropertyEnrichment).count()
    scored_count = db.query(PropertyScore).count()
    documents_count = db.query(GeneratedDocument).count()
    campaigns_count = db.query(Campaign).count()

    print(f"\nDatabase Records:")
    print(f"  Properties: {properties_count}")
    print(f"  Enriched: {enriched_count}")
    print(f"  Scored: {scored_count}")
    print(f"  Documents: {documents_count}")
    print(f"  Campaigns: {campaigns_count}")

    # Get score distribution
    high_score = db.query(PropertyScore).filter(PropertyScore.total_score >= 80).count()
    medium_score = db.query(PropertyScore).filter(
        PropertyScore.total_score >= 60,
        PropertyScore.total_score < 80
    ).count()
    low_score = db.query(PropertyScore).filter(PropertyScore.total_score < 60).count()

    print(f"\nScore Distribution:")
    print(f"  High (≥80): {high_score}")
    print(f"  Medium (60-79): {medium_score}")
    print(f"  Low (<60): {low_score}")

    # Get top properties
    top_properties = (
        db.query(Property, PropertyScore)
        .join(PropertyScore, Property.id == PropertyScore.property_id)
        .order_by(PropertyScore.total_score.desc())
        .limit(5)
        .all()
    )

    print(f"\nTop 5 Properties:")
    for prop, score in top_properties:
        print(f"  {score.total_score}/100 - {prop.address}, {prop.city}")

    print("\n" + "="*60)
    print("✓ Demo data generation complete!")
    print("="*60)


def main():
    """Main demo data generation function."""
    print("="*60)
    print("REAL ESTATE OS - DEMO DATA GENERATOR")
    print("="*60)

    db = get_db_session()

    try:
        # Optional: Clear existing data
        # clear_existing_data(db)

        # Step 1: Generate properties
        property_ids = generate_properties(db, count=50)

        # Step 2: Enrich properties
        enrich_properties(db, property_ids)

        # Step 3: Score properties
        score_properties(db, property_ids)

        # Step 4: Generate documents
        generate_documents(db, property_ids)

        # Step 5: Create campaigns
        campaign_ids = create_campaigns(db)

        # Step 6: Execute a sample campaign
        execute_sample_campaign(db, campaign_ids)

        # Print summary
        print_summary(db)

    except Exception as e:
        print(f"\n✗ Error during demo data generation: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    main()
