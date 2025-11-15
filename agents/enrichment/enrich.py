import argparse
import json
import os
import random
from urllib.parse import urlparse

try:
    import boto3
except ImportError:
    boto3 = None

def load_data(uri: str) -> dict:
    parsed_uri = urlparse(uri)
    scheme = parsed_uri.scheme
    if scheme == "s3":
        if not boto3:
            raise ImportError("boto3 is required for S3 support. Please install it with 'pip install boto3'.")
        s3 = boto3.client("s3")
        bucket = parsed_uri.netloc
        key = parsed_uri.path.lstrip("/")
        response = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    elif scheme == "file" or not scheme:
        path = parsed_uri.path or uri
        if os.name == "nt" and path.startswith("/"):
            path = path[1:]
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported URI scheme: {scheme}")

def write_data(data: dict, uri: str):
    parsed_uri = urlparse(uri)
    scheme = parsed_uri.scheme
    output_content = json.dumps(data, indent=2)

    if scheme == "s3":
        if not boto3:
            raise ImportError("boto3 is required for S3 support. Please install it with 'pip install boto3'.")
        s3 = boto3.client("s3")
        bucket = parsed_uri.netloc
        key = parsed_uri.path.lstrip("/")
        s3.put_object(Bucket=bucket, Key=key, Body=output_content.encode("utf-8"))
        print(f"Successfully wrote enriched data to s3://{bucket}/{key}")
    elif scheme == "file" or not scheme:
        path = parsed_uri.path or uri
        if os.name == "nt" and path.startswith("/"):
            path = path[1:]
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(f"Successfully wrote enriched data to {path}")
    else:
        raise ValueError(f"Unsupported URI scheme: {scheme}")

def enrich_with_assessor_data(property_data: dict) -> dict:
    """Enrich property with realistic simulated assessor and market data."""

    enriched_data = property_data.copy()

    # Get base property info
    price = property_data.get("price", 350000)
    city = property_data.get("city", "Las Vegas")
    state = property_data.get("state", "NV")
    sqft = property_data.get("sqft", random.randint(1500, 2500))
    year_built = property_data.get("year_built", random.randint(1990, 2020))

    # Generate APN
    apn = f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(100, 999)}-{random.randint(100, 999)}"

    # Calculate tax assessment (typically 80-95% of market value)
    tax_assessment_value = int(price * random.uniform(0.80, 0.95))
    annual_tax_amount = int(tax_assessment_value * random.uniform(0.008, 0.015))  # 0.8-1.5% tax rate

    # Generate last sale data (1-10 years ago, lower price)
    years_ago = random.randint(1, 10)
    appreciation_rate = random.uniform(0.03, 0.08)  # 3-8% annual
    last_sale_price = int(price / ((1 + appreciation_rate) ** years_ago))
    last_sale_year = 2025 - years_ago

    # School data based on city
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

    # Crime data (inverse of walkability usually)
    crime_rates = ["low", "low", "medium", "high"]
    crime_weights = [0.5, 0.3, 0.15, 0.05]
    crime_rate = random.choices(crime_rates, weights=crime_weights)[0]
    crime_index = {"low": random.randint(10, 35), "medium": random.randint(35, 65), "high": random.randint(65, 90)}[crime_rate]

    # Market data
    median_home_value = int(price * random.uniform(0.9, 1.1))
    appreciation_1yr = round(random.uniform(2.5, 8.5), 1)
    appreciation_5yr = round(random.uniform(15.0, 35.0), 1)
    median_rent = int(price * random.uniform(0.0045, 0.0065))  # ~0.5-0.65% of value per month

    # Nearby amenities
    parks = random.sample([
        f"{city} Central Park",
        f"{city} Community Park",
        "Sunset Park",
        "Desert Breeze Park",
        "Heritage Park",
        "Discovery Park",
        "Mountain View Park",
    ], k=random.randint(2, 4))

    shopping = random.sample([
        f"{city} Town Center",
        "Main Street Shopping",
        "The District",
        "Fashion Square",
        "Outlets Mall",
        "Premium Plaza",
    ], k=random.randint(1, 3))

    # Flood/earthquake zones
    flood_zone = random.choices(["X", "A", "AE", "VE"], weights=[0.85, 0.08, 0.05, 0.02])[0]
    earthquake_zone = random.choices(["low", "moderate", "high"], weights=[0.7, 0.25, 0.05])[0]

    # HOA fees (30% chance of having HOA)
    hoa_fees = random.randint(50, 350) if random.random() < 0.3 else 0

    enriched_data["enrichment"] = {
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
        "last_sale_date": f"{last_sale_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "last_sale_price": last_sale_price,

        # Property characteristics
        "legal_description": f"Lot {random.randint(1, 250)}, Block {random.randint(1, 50)}, {city} Subdivision",
        "zoning": random.choice(["R-1", "R-2", "R-3", "C-1", "M-1"]),
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
        "nearby_restaurants": [f"{city} Restaurant #{i}" for i in range(random.randint(3, 6))],
        "distance_to_downtown": round(random.uniform(1.5, 15.0), 1),

        # Risk factors
        "flood_zone": flood_zone,
        "earthquake_zone": earthquake_zone,
        "hoa_fees": hoa_fees,

        # Metadata
        "enrichment_source": "simulated_assessor_api",
        "enrichment_timestamp": "2025-01-15T12:00:00Z",
    }

    print(f"Enriched property at {property_data.get('address', 'Unknown')} with realistic assessor data.")
    return enriched_data

def main():
    parser = argparse.ArgumentParser(description="Enrich property data.")
    parser.add_argument("--input-uri", required=True, help="Input URI (local or s3://).")
    parser.add_argument("--output-uri", required=True, help="Output URI (local or s3://).")
    args = parser.parse_args()
    property_data = load_data(args.input_uri)
    enriched_data = enrich_with_assessor_data(property_data)
    write_data(enriched_data, args.output_uri)

if __name__ == "__main__":
    main()
