"""
Demo data seeding script for Real Estate OS
Populates the database with sample data for demonstration
"""
import os
import sys
from datetime import datetime, timedelta
from random import randint, choice, uniform
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import (
    Base, ProspectQueue, Property, ScrapingJob, EnrichmentJob,
    PropertyScore, PipelineRun, DataQualityMetric, JobStatus
)


def create_demo_data(db_dsn: str):
    """Create demo data in the database"""

    engine = create_engine(db_dsn)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("Creating demo data...")

        # Sample data for variety
        sources = ["zillow", "redfin", "realtor.com"]
        cities = ["Austin", "Dallas", "Houston", "San Antonio"]
        states = ["TX"]
        property_types = ["Single Family", "Condo", "Townhouse", "Multi-Family"]

        # Create 50 prospect queue items
        prospects = []
        for i in range(50):
            source = choice(sources)
            prospect = ProspectQueue(
                source=source,
                source_id=f"{source}_{i+1000}",
                url=f"https://{source}.com/property/{i+1000}",
                payload={
                    "title": f"Property {i+1}",
                    "raw_price": f"${randint(200, 800)}K",
                    "beds": randint(2, 5),
                    "baths": randint(1, 3)
                },
                status=choice(["new", "processing", "enriched", "scored"]),
                created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
            )
            prospects.append(prospect)
        session.add_all(prospects)
        session.flush()
        print(f"✓ Created {len(prospects)} prospect queue items")

        # Create 35 enriched properties (from prospects)
        properties = []
        for i in range(35):
            city = choice(cities)
            prop = Property(
                prospect_id=prospects[i].id,
                address=f"{randint(100, 9999)} {choice(['Main', 'Oak', 'Elm', 'Maple'])} St",
                city=city,
                state=choice(states),
                zip_code=f"7{randint(1000, 9999)}",
                property_type=choice(property_types),
                bedrooms=randint(2, 5),
                bathrooms=uniform(1, 3.5),
                sqft=randint(1000, 3500),
                lot_size=uniform(0.1, 0.5),
                year_built=randint(1980, 2023),
                price=uniform(200000, 800000),
                estimated_value=uniform(220000, 850000),
                enrichment_data={
                    "market_data": {
                        "avg_price_per_sqft": uniform(150, 350),
                        "days_on_market": randint(10, 90)
                    }
                },
                enrichment_sources=["zillow_api", "census_data"],
                created_at=datetime.utcnow() - timedelta(days=randint(0, 25))
            )
            properties.append(prop)
        session.add_all(properties)
        session.flush()
        print(f"✓ Created {len(properties)} enriched properties")

        # Create scraping jobs
        scraping_jobs = []
        for i in range(20):
            job = ScrapingJob(
                dag_id="scrape_listings",
                dag_run_id=f"scheduled__{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')}_{i}",
                source=choice(sources),
                status=choice([JobStatus.SUCCESS, JobStatus.SUCCESS, JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.RUNNING]),
                items_scraped=randint(5, 50),
                items_failed=randint(0, 5),
                started_at=datetime.utcnow() - timedelta(hours=randint(1, 48)),
                completed_at=datetime.utcnow() - timedelta(hours=randint(0, 47)),
                config={"max_pages": 10, "delay": 2},
                created_at=datetime.utcnow() - timedelta(days=randint(0, 20))
            )
            scraping_jobs.append(job)
        session.add_all(scraping_jobs)
        print(f"✓ Created {len(scraping_jobs)} scraping jobs")

        # Create enrichment jobs
        enrichment_jobs = []
        for i in range(30):
            job = EnrichmentJob(
                dag_id="enrichment_property",
                dag_run_id=f"scheduled__{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')}_{i}",
                property_id=properties[i % len(properties)].id,
                status=choice([JobStatus.SUCCESS, JobStatus.SUCCESS, JobStatus.RUNNING, JobStatus.FAILED]),
                enrichment_type=choice(["property_data", "market_data", "demographics"]),
                started_at=datetime.utcnow() - timedelta(hours=randint(1, 36)),
                completed_at=datetime.utcnow() - timedelta(hours=randint(0, 35)),
                data_sources_used=["zillow_api", "census_api"],
                fields_enriched=["price", "sqft", "year_built"],
                created_at=datetime.utcnow() - timedelta(days=randint(0, 18))
            )
            enrichment_jobs.append(job)
        session.add_all(enrichment_jobs)
        print(f"✓ Created {len(enrichment_jobs)} enrichment jobs")

        # Create property scores
        scores = []
        for prop in properties[:25]:  # Score first 25 properties
            score = PropertyScore(
                property_id=prop.id,
                dag_run_id=f"scoring_run_{randint(1, 100)}",
                overall_score=uniform(45, 95),
                investment_score=uniform(40, 100),
                risk_score=uniform(20, 80),
                roi_estimate=uniform(5, 25),
                score_components={
                    "location": uniform(60, 95),
                    "condition": uniform(50, 90),
                    "market_trend": uniform(40, 85)
                },
                model_version="v1.2.0",
                features_used=["price", "location", "sqft", "market_data"],
                created_at=datetime.utcnow() - timedelta(days=randint(0, 15))
            )
            scores.append(score)
        session.add_all(scores)
        print(f"✓ Created {len(scores)} property scores")

        # Create pipeline runs
        pipeline_runs = []
        dags = ["scrape_listings", "enrichment_property", "score_master", "discovery_offmarket"]
        for i in range(40):
            run = PipelineRun(
                dag_id=choice(dags),
                dag_run_id=f"scheduled__{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')}_{i}",
                execution_date=datetime.utcnow() - timedelta(hours=randint(1, 720)),
                status=choice(["success", "success", "success", "failed", "running"]),
                started_at=datetime.utcnow() - timedelta(hours=randint(1, 720)),
                completed_at=datetime.utcnow() - timedelta(hours=randint(0, 719)),
                duration_seconds=randint(60, 3600),
                tasks_total=randint(3, 10),
                tasks_success=randint(2, 9),
                tasks_failed=randint(0, 2),
                config={"retry": 3},
                created_at=datetime.utcnow() - timedelta(days=randint(0, 30))
            )
            pipeline_runs.append(run)
        session.add_all(pipeline_runs)
        print(f"✓ Created {len(pipeline_runs)} pipeline runs")

        # Create data quality metrics
        metrics = []
        metric_types = ["completeness", "accuracy", "consistency", "timeliness"]
        for i in range(50):
            metric = DataQualityMetric(
                metric_type=choice(metric_types),
                metric_name=choice(["data_completeness", "price_accuracy", "address_validation"]),
                value=uniform(70, 99),
                threshold=85.0,
                is_passing=choice([True, True, True, False]),
                entity_type=choice(["property", "prospect", "pipeline"]),
                entity_id=randint(1, 50),
                details={"source": "automated_check"},
                measured_at=datetime.utcnow() - timedelta(hours=randint(0, 168))
            )
            metrics.append(metric)
        session.add_all(metrics)
        print(f"✓ Created {len(metrics)} data quality metrics")

        # Commit all data
        session.commit()
        print("\n✅ Demo data created successfully!")
        print("\nSummary:")
        print(f"  - {len(prospects)} prospects")
        print(f"  - {len(properties)} properties")
        print(f"  - {len(scraping_jobs)} scraping jobs")
        print(f"  - {len(enrichment_jobs)} enrichment jobs")
        print(f"  - {len(scores)} property scores")
        print(f"  - {len(pipeline_runs)} pipeline runs")
        print(f"  - {len(metrics)} data quality metrics")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error creating demo data: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    db_dsn = os.getenv("DB_DSN", "postgresql://airflow:airflow@localhost:5432/airflow")
    print(f"Using database: {db_dsn}\n")
    create_demo_data(db_dsn)
