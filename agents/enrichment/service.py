"""Database-integrated enrichment service for properties."""

import sys
sys.path.insert(0, '/home/user/real-estate-os')

import random
from datetime import date
from typing import Dict, Any
from sqlalchemy.orm import Session
from db.models import Property, PropertyEnrichment
from src.models.enrichment import EnrichmentCreate


class EnrichmentService:
    """Service for enriching property data with assessor and market information."""

    def __init__(self, db_session: Session):
        """Initialize service with database session."""
        self.db = db_session

    def enrich_property(self, property_id: int) -> PropertyEnrichment:
        """
        Enrich a property with simulated assessor and market data.

        Args:
            property_id: ID of the property to enrich

        Returns:
            PropertyEnrichment object with enriched data
        """
        # Get property
        prop = self.db.query(Property).filter(Property.id == property_id).first()
        if not prop:
            raise ValueError(f"Property {property_id} not found")

        # Generate enrichment data
        enrichment_data = self._generate_enrichment_data(prop)

        # Check if enrichment already exists
        existing = self.db.query(PropertyEnrichment).filter(
            PropertyEnrichment.property_id == property_id
        ).first()

        if existing:
            # Update existing enrichment
            for field, value in enrichment_data.items():
                setattr(existing, field, value)
            enrichment = existing
        else:
            # Create new enrichment
            enrichment = PropertyEnrichment(property_id=property_id, **enrichment_data)
            self.db.add(enrichment)

        # Update property status
        if prop.status == 'new':
            prop.status = 'enriched'

        self.db.commit()
        self.db.refresh(enrichment)

        return enrichment

    def _generate_enrichment_data(self, prop: Property) -> Dict[str, Any]:
        """Generate realistic enrichment data based on property information."""

        price = prop.price
        city = prop.city
        sqft = prop.sqft or random.randint(1500, 2500)
        year_built = prop.year_built or random.randint(1990, 2020)

        # Generate APN
        apn = f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(100, 999)}-{random.randint(100, 999)}"

        # Tax assessment (80-95% of market value)
        tax_assessment_value = int(price * random.uniform(0.80, 0.95))
        annual_tax_amount = int(tax_assessment_value * random.uniform(0.008, 0.015))

        # Last sale data (1-10 years ago)
        years_ago = random.randint(1, 10)
        appreciation_rate = random.uniform(0.03, 0.08)
        last_sale_price = int(price / ((1 + appreciation_rate) ** years_ago))
        last_sale_year = 2025 - years_ago
        last_sale_date = date(last_sale_year, random.randint(1, 12), random.randint(1, 28))

        # School data
        school_districts = {
            "Las Vegas": "Clark County School District",
            "Henderson": "Clark County School District",
            "Phoenix": "Phoenix Union High School District",
            "Scottsdale": "Scottsdale Unified School District",
            "Reno": "Washoe County School District",
        }
        school_district = school_districts.get(city, "Local School District")
        school_rating = round(random.uniform(5.5, 9.5), 1)

        # Location scores
        walk_score = random.randint(30, 95)
        transit_score = random.randint(20, 75)
        bike_score = random.randint(25, 85)

        # Crime data
        crime_rates = ["low", "low", "medium", "high"]
        crime_weights = [0.5, 0.3, 0.15, 0.05]
        crime_rate = random.choices(crime_rates, weights=crime_weights)[0]
        crime_index_map = {
            "low": random.randint(10, 35),
            "medium": random.randint(35, 65),
            "high": random.randint(65, 90)
        }
        crime_index = crime_index_map[crime_rate]

        # Market data
        median_home_value = int(price * random.uniform(0.9, 1.1))
        appreciation_1yr = round(random.uniform(2.5, 8.5), 1)
        appreciation_5yr = round(random.uniform(15.0, 35.0), 1)
        median_rent = int(price * random.uniform(0.0045, 0.0065))

        # Nearby amenities
        parks = random.sample([
            f"{city} Central Park",
            f"{city} Community Park",
            "Sunset Park",
            "Desert Breeze Park",
            "Heritage Park",
        ], k=min(3, 5))

        shopping = random.sample([
            f"{city} Town Center",
            "Main Street Shopping",
            "The District",
        ], k=min(2, 3))

        restaurants = [f"{city} Restaurant #{i}" for i in range(random.randint(3, 6))]

        # Risk factors
        flood_zone = random.choices(["X", "A", "AE", "VE"], weights=[0.85, 0.08, 0.05, 0.02])[0]
        earthquake_zone = random.choices(["low", "moderate", "high"], weights=[0.7, 0.25, 0.05])[0]

        # HOA fees
        hoa_fees = random.randint(50, 350) if random.random() < 0.3 else None

        return {
            # Assessor data
            "apn": apn,
            "tax_assessment_value": tax_assessment_value,
            "tax_assessment_year": 2024,
            "annual_tax_amount": annual_tax_amount,

            # Ownership
            "owner_name": random.choice([
                f"{random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])} Family Trust",
                f"{random.choice(['Anderson', 'Taylor', 'Thomas', 'Moore'])} LLC",
                "Individual Owner",
            ]),
            "owner_type": random.choice(["trust", "individual", "corporation"]),
            "last_sale_date": last_sale_date,
            "last_sale_price": last_sale_price,

            # Property characteristics
            "legal_description": f"Lot {random.randint(1, 250)}, Block {random.randint(1, 50)}, {city} Subdivision",
            "zoning": random.choice(["R-1", "R-2", "R-3", "C-1"]),
            "land_use": "Residential",

            # Building details
            "building_sqft": sqft,
            "stories": random.choice([1, 1, 2, 2, 3]),
            "units": 1,
            "parking_spaces": random.randint(1, 3),

            # Schools
            "school_district": school_district,
            "elementary_school": f"{city} Elementary #{random.randint(1, 50)}",
            "middle_school": f"{city} Middle School #{random.randint(1, 20)}",
            "high_school": f"{city} High School #{random.randint(1, 10)}",
            "school_rating": school_rating,

            # Location metrics
            "walkability_score": walk_score,
            "transit_score": transit_score,
            "bike_score": bike_score,

            # Crime
            "crime_rate": crime_rate,
            "crime_index": crime_index,

            # Market data
            "median_home_value": median_home_value,
            "appreciation_1yr": appreciation_1yr,
            "appreciation_5yr": appreciation_5yr,
            "median_rent": median_rent,

            # Amenities
            "nearby_parks": parks,
            "nearby_shopping": shopping,
            "nearby_restaurants": restaurants,
            "distance_to_downtown": round(random.uniform(1.5, 15.0), 1),

            # Risk factors
            "flood_zone": flood_zone,
            "earthquake_zone": earthquake_zone,
            "hoa_fees": hoa_fees,

            # Metadata
            "enrichment_source": "simulated_assessor_api",
        }


def enrich_property_by_id(property_id: int, db_session: Session) -> PropertyEnrichment:
    """
    Convenience function to enrich a property by ID.

    Args:
        property_id: ID of property to enrich
        db_session: SQLAlchemy session

    Returns:
        PropertyEnrichment object
    """
    service = EnrichmentService(db_session)
    return service.enrich_property(property_id)
