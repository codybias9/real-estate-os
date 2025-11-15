"""Generate realistic simulated property data for demo purposes."""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any


class PropertyDataGenerator:
    """Generator for realistic property data."""

    # Real cities and their coordinates
    CITIES = {
        "Las Vegas": {
            "state": "NV",
            "county": "Clark",
            "lat_range": (36.0, 36.3),
            "lng_range": (-115.3, -115.0),
            "zip_codes": ["89101", "89102", "89103", "89104", "89106", "89107", "89108", "89109", "89110", "89129", "89134", "89135", "89138", "89139", "89141", "89142", "89143", "89144", "89145", "89146", "89147", "89148", "89149"],
            "median_price": 380000,
        },
        "Henderson": {
            "state": "NV",
            "county": "Clark",
            "lat_range": (36.0, 36.1),
            "lng_range": (-115.15, -114.95),
            "zip_codes": ["89002", "89011", "89012", "89014", "89015", "89044", "89052", "89074"],
            "median_price": 450000,
        },
        "Phoenix": {
            "state": "AZ",
            "county": "Maricopa",
            "lat_range": (33.3, 33.7),
            "lng_range": (-112.3, -111.9),
            "zip_codes": ["85001", "85003", "85004", "85006", "85007", "85008", "85009", "85012", "85013", "85014", "85015", "85016", "85017", "85018", "85019", "85020", "85021", "85022", "85023", "85024", "85027", "85028", "85029", "85032", "85033", "85034", "85035", "85037", "85040", "85041", "85042", "85043", "85044", "85045", "85048", "85050", "85051"],
            "median_price": 420000,
        },
        "Scottsdale": {
            "state": "AZ",
            "county": "Maricopa",
            "lat_range": (33.4, 33.8),
            "lng_range": (-111.95, -111.85),
            "zip_codes": ["85250", "85251", "85254", "85255", "85256", "85257", "85258", "85259", "85260", "85262"],
            "median_price": 650000,
        },
        "Reno": {
            "state": "NV",
            "county": "Washoe",
            "lat_range": (39.45, 39.6),
            "lng_range": (-119.9, -119.7),
            "zip_codes": ["89501", "89502", "89503", "89506", "89509", "89511", "89512", "89519", "89521", "89523"],
            "median_price": 480000,
        },
    }

    STREET_NAMES = [
        "Main", "Oak", "Pine", "Maple", "Cedar", "Elm", "View", "Park", "Hill", "Lake",
        "Washington", "Jefferson", "Adams", "Madison", "Monroe", "Jackson", "Lincoln",
        "Sunset", "Sunrise", "Mountain", "Desert", "Valley", "Canyon", "Ridge", "Meadow",
        "Spring", "Summer", "Autumn", "Winter", "Garden", "Forest", "River", "Creek",
        "North", "South", "East", "West", "Central", "Highland", "Woodland", "Parkway"
    ]

    STREET_TYPES = ["St", "Ave", "Blvd", "Dr", "Ln", "Rd", "Way", "Ct", "Cir", "Pl"]

    PROPERTY_TYPES = ["single_family", "condo", "townhouse", "multifamily"]

    FEATURES = [
        "granite countertops",
        "stainless steel appliances",
        "hardwood floors",
        "tile flooring",
        "carpet",
        "walk-in closet",
        "master suite",
        "en-suite bathroom",
        "2-car garage",
        "3-car garage",
        "covered parking",
        "private backyard",
        "fenced yard",
        "patio",
        "deck",
        "balcony",
        "fireplace",
        "central air conditioning",
        "ceiling fans",
        "recessed lighting",
        "updated kitchen",
        "renovated bathroom",
        "new paint",
        "new carpet",
        "energy efficient windows",
        "solar panels",
        "tankless water heater",
        "smart home features",
        "security system",
        "community pool",
        "community gym",
        "playground",
        "HOA amenities",
        "mountain views",
        "city views",
        "golf course views",
    ]

    DESCRIPTIONS_TEMPLATES = [
        "Beautiful {property_type} in desirable {city} neighborhood. This {bedrooms} bedroom, {bathrooms} bathroom home features {feature1}, {feature2}, and {feature3}. Perfect for families or investors!",
        "Stunning {property_type} with {sqft} sq ft of living space. Located in the heart of {city}, this property offers {feature1}, {feature2}, and modern finishes throughout.",
        "Don't miss this {property_type} opportunity! {bedrooms} beds, {bathrooms} baths, and {feature1}. Great location in {city} with easy access to shopping, dining, and entertainment.",
        "Charming {property_type} in {city}. Features include {feature1}, {feature2}, and {feature3}. {sqft} sq ft with a {lot_size} sq ft lot. Built in {year_built}.",
        "Investment opportunity! This {property_type} in {city} offers great rental potential. {bedrooms}/{bathrooms} with {feature1} and {feature2}. Priced to sell!",
        "Move-in ready {property_type}! Beautifully maintained home in {city} featuring {feature1}, {feature2}, and {feature3}. {bedrooms} bedrooms and {bathrooms} bathrooms.",
        "Spacious {property_type} with {sqft} sq ft. Located in sought-after {city} area. {bedrooms} beds, {bathrooms} baths, {feature1}, and {feature2}.",
        "Incredible {property_type} in {city}! This {bedrooms} bedroom home boasts {feature1}, {feature2}, {feature3}, and more. {sqft} sq ft of thoughtfully designed space.",
    ]

    @classmethod
    def generate_property(cls, source: str = "simulated_mls", property_id: int = None) -> Dict[str, Any]:
        """Generate a single realistic property listing."""

        # Select random city
        city_name = random.choice(list(cls.CITIES.keys()))
        city_data = cls.CITIES[city_name]

        # Generate property type
        property_type = random.choice(cls.PROPERTY_TYPES)

        # Generate bedrooms/bathrooms based on property type
        if property_type == "condo":
            bedrooms = random.choice([1, 2, 2, 3])
            bathrooms = random.choice([1.0, 1.5, 2.0, 2.0])
            sqft = random.randint(650, 1800)
            lot_size = 0
        elif property_type == "townhouse":
            bedrooms = random.choice([2, 3, 3, 3, 4])
            bathrooms = random.choice([1.5, 2.0, 2.5, 2.5, 3.0])
            sqft = random.randint(1200, 2400)
            lot_size = random.randint(1500, 3500)
        elif property_type == "multifamily":
            bedrooms = random.randint(2, 8)
            bathrooms = random.randint(2, 6)
            sqft = random.randint(1800, 4500)
            lot_size = random.randint(4000, 12000)
        else:  # single_family
            bedrooms = random.choice([2, 3, 3, 3, 4, 4, 5])
            bathrooms = random.choice([1.0, 2.0, 2.0, 2.5, 2.5, 3.0, 3.5])
            sqft = random.randint(1000, 3500)
            lot_size = random.randint(3000, 10000)

        # Calculate price based on city median and size
        base_price = city_data["median_price"]
        price_per_sqft = random.randint(150, 350)
        price = int(sqft * price_per_sqft * random.uniform(0.9, 1.1))

        # Apply some randomness for below-market deals
        if random.random() < 0.3:  # 30% chance of being below market
            price = int(price * random.uniform(0.75, 0.95))

        # Round to nearest $5,000
        price = round(price / 5000) * 5000

        # Generate year built
        current_year = datetime.now().year
        year_built = random.randint(1980, current_year)

        # Generate address
        street_number = random.randint(100, 9999)
        street_name = random.choice(cls.STREET_NAMES)
        street_type = random.choice(cls.STREET_TYPES)
        address = f"{street_number} {street_name} {street_type}"
        if property_type in ["condo", "townhouse"]:
            unit_number = random.randint(1, 250)
            address = f"{address} #{unit_number}"

        # Generate coordinates
        latitude = random.uniform(*city_data["lat_range"])
        longitude = random.uniform(*city_data["lng_range"])

        # Generate features
        num_features = random.randint(5, 12)
        features = random.sample(cls.FEATURES, num_features)

        # Generate description
        description_template = random.choice(cls.DESCRIPTIONS_TEMPLATES)
        description = description_template.format(
            property_type=property_type.replace("_", " "),
            city=city_name,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft=sqft,
            lot_size=lot_size,
            year_built=year_built,
            feature1=features[0] if len(features) > 0 else "modern finishes",
            feature2=features[1] if len(features) > 1 else "updated kitchen",
            feature3=features[2] if len(features) > 2 else "spacious layout",
        )

        # Generate listing date (within last 120 days)
        days_ago = random.randint(1, 120)
        listing_date = (datetime.now() - timedelta(days=days_ago)).isoformat()

        # Generate source ID
        if property_id is None:
            source_id = f"{source}_{random.randint(100000000, 999999999)}"
        else:
            source_id = f"{source}_{property_id}"

        # Generate placeholder images
        images = [
            f"https://placeholder.com/800x600?text=Property+{source_id}+Main",
            f"https://placeholder.com/800x600?text=Property+{source_id}+Kitchen",
            f"https://placeholder.com/800x600?text=Property+{source_id}+Bedroom",
            f"https://placeholder.com/800x600?text=Property+{source_id}+Bathroom",
        ]

        return {
            "source": source,
            "source_id": source_id,
            "url": f"https://example.com/listings/{source_id}",
            "address": address,
            "city": city_name,
            "state": city_data["state"],
            "zip_code": random.choice(city_data["zip_codes"]),
            "county": city_data["county"],
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "property_type": property_type,
            "price": price,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "sqft": sqft,
            "lot_size": lot_size,
            "year_built": year_built,
            "listing_date": listing_date,
            "description": description,
            "features": features,
            "images": images,
            "status": "new",
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "simulated": True,
            },
        }

    @classmethod
    def generate_batch(cls, count: int = 10, source: str = "simulated_mls") -> List[Dict[str, Any]]:
        """Generate multiple property listings."""
        return [cls.generate_property(source=source, property_id=i+1) for i in range(count)]
