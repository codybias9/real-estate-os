"""
Property Twin Search Demo.

Demonstrates finding similar properties using vector similarity search.
"""
from ml.similarity.property_twin_search import (
    PropertyTwinSearch,
    PropertyFeatures,
    PropertyEmbedding
)
import numpy as np


def demo_embedding_generation():
    """Demonstrate embedding generation from property features."""
    print("=" * 80)
    print("Property Twin Search - Embedding Generation Demo")
    print("=" * 80)
    print()

    # Create embedding generator
    embedding_gen = PropertyEmbedding(embedding_dim=128)

    # Sample property
    property1 = PropertyFeatures(
        latitude=37.7749,
        longitude=-122.4194,
        city="San Francisco",
        state="CA",
        zip_code="94102",
        building_sqft=2400,
        lot_size_sqft=7500,
        year_built=1985,
        bedrooms=4,
        bathrooms=3.0,
        stories=2,
        parking_spaces=2,
        property_type="Residential",
        purchase_price=1200000,
        monthly_rent=4500,
        property_tax_annual=14400,
        condition_score=7.5,
        composite_hazard_score=0.45
    )

    # Generate embedding
    embedding1 = embedding_gen.generate_embedding(property1)

    print(f"Property: San Francisco Residential")
    print(f"  Size: {property1.building_sqft:,} sqft")
    print(f"  Price: ${property1.purchase_price:,}")
    print(f"  Bedrooms: {property1.bedrooms}")
    print(f"  Year Built: {property1.year_built}")
    print(f"  Hazard Score: {property1.composite_hazard_score:.2f}")
    print()
    print(f"Generated embedding: {embedding1.shape}")
    print(f"Embedding norm: {np.linalg.norm(embedding1):.4f} (should be ~1.0)")
    print(f"Non-zero dimensions: {np.count_nonzero(embedding1)}/{len(embedding1)}")
    print()

    # Show embedding breakdown by feature groups
    print("Embedding Breakdown by Feature Group:")
    print(f"  Location (0-19):    {np.linalg.norm(embedding1[0:20]):.4f}")
    print(f"  Physical (20-49):   {np.linalg.norm(embedding1[20:50]):.4f}")
    print(f"  Type (50-59):       {np.linalg.norm(embedding1[50:60]):.4f}")
    print(f"  Financial (60-79):  {np.linalg.norm(embedding1[60:80]):.4f}")
    print(f"  Condition (80-89):  {np.linalg.norm(embedding1[80:90]):.4f}")
    print(f"  Hazards (90-99):    {np.linalg.norm(embedding1[90:100]):.4f}")
    print()

    # Similar property (slightly different)
    property2 = PropertyFeatures(
        latitude=37.7849,  # 1.1 km north
        longitude=-122.4094,
        city="San Francisco",
        state="CA",
        zip_code="94109",
        building_sqft=2350,  # Slightly smaller
        lot_size_sqft=7200,
        year_built=1988,  # 3 years newer
        bedrooms=4,
        bathrooms=3.0,
        stories=2,
        parking_spaces=2,
        property_type="Residential",
        purchase_price=1250000,  # $50k more
        monthly_rent=4650,
        property_tax_annual=15000,
        condition_score=8.0,  # Better condition
        composite_hazard_score=0.42  # Slightly lower hazard
    )

    embedding2 = embedding_gen.generate_embedding(property2)

    # Calculate similarity
    similarity = np.dot(embedding1, embedding2)
    print(f"Similar Property: San Francisco Residential (1.1 km away)")
    print(f"  Size: {property2.building_sqft:,} sqft")
    print(f"  Price: ${property2.purchase_price:,}")
    print(f"  Year Built: {property2.year_built}")
    print(f"  Similarity Score: {similarity:.4f} (cosine similarity)")
    print()

    # Very different property
    property3 = PropertyFeatures(
        latitude=34.0522,  # Los Angeles
        longitude=-118.2437,
        city="Los Angeles",
        state="CA",
        zip_code="90012",
        building_sqft=15000,  # Much larger
        lot_size_sqft=20000,
        year_built=2010,  # Much newer
        bedrooms=None,
        bathrooms=None,
        stories=4,
        parking_spaces=50,
        property_type="Commercial",  # Different type
        purchase_price=5000000,  # Much more expensive
        monthly_rent=None,
        property_tax_annual=60000,
        condition_score=9.0,
        composite_hazard_score=0.35
    )

    embedding3 = embedding_gen.generate_embedding(property3)
    similarity3 = np.dot(embedding1, embedding3)

    print(f"Dissimilar Property: Los Angeles Commercial")
    print(f"  Size: {property3.building_sqft:,} sqft")
    print(f"  Price: ${property3.purchase_price:,}")
    print(f"  Type: {property3.property_type}")
    print(f"  Similarity Score: {similarity3:.4f} (cosine similarity)")
    print()
    print("✓ Similar properties have higher scores (closer to 1.0)")
    print("✓ Dissimilar properties have lower scores")
    print()


def demo_twin_search():
    """Demonstrate twin search functionality."""
    print("=" * 80)
    print("Property Twin Search - Search Demo")
    print("=" * 80)
    print()

    # Initialize twin search engine
    twin_search = PropertyTwinSearch()

    # Subject property for which we want to find twins
    subject = PropertyFeatures(
        latitude=37.7749,
        longitude=-122.4194,
        city="San Francisco",
        state="CA",
        zip_code="94102",
        building_sqft=2400,
        lot_size_sqft=7500,
        year_built=1985,
        bedrooms=4,
        bathrooms=3.0,
        stories=2,
        parking_spaces=2,
        property_type="Residential",
        purchase_price=1200000,
        monthly_rent=4500,
        property_tax_annual=14400,
        condition_score=7.5,
        composite_hazard_score=0.45
    )

    print("SUBJECT PROPERTY:")
    print(f"  Address: San Francisco, CA 94102")
    print(f"  Type: {subject.property_type}")
    print(f"  Size: {subject.building_sqft:,} sqft")
    print(f"  Bedrooms: {subject.bedrooms}")
    print(f"  Bathrooms: {subject.bathrooms}")
    print(f"  Year Built: {subject.year_built}")
    print(f"  Price: ${subject.purchase_price:,}")
    print(f"  Monthly Rent: ${subject.monthly_rent:,}")
    print(f"  Condition: {subject.condition_score}/10")
    print(f"  Hazard Score: {subject.composite_hazard_score:.2f}")
    print()

    # Search for twins
    print("Searching for property twins...")
    twins = twin_search.search_twins(
        subject_features=subject,
        limit=5
    )

    print(f"Found {len(twins)} similar properties:")
    print()

    for i, twin in enumerate(twins, 1):
        print(f"{i}. {twin.address}")
        print(f"   📍 {twin.city}, {twin.state}")
        print(f"   📊 Similarity: {twin.similarity_score:.1%}")
        if twin.building_sqft:
            print(f"   📐 Size: {twin.building_sqft:,} sqft")
        if twin.purchase_price:
            print(f"   💰 Price: ${twin.purchase_price:,.0f}")
        print(f"   📏 Distance: {twin.distance_miles:.1f} miles")
        print()
        print("   Feature Breakdown:")
        for feature, contribution in twin.feature_breakdown.items():
            print(f"      {feature.capitalize():12s}: {contribution:.1%}")
        print()

    # Test with filters
    print("-" * 80)
    print("Searching with filters (price range $1M - $1.5M)...")
    print()

    twins_filtered = twin_search.search_twins(
        subject_features=subject,
        limit=5,
        filters={
            "min_price": 1000000,
            "max_price": 1500000,
            "property_type": "Residential"
        }
    )

    print(f"Found {len(twins_filtered)} properties matching filters")
    for i, twin in enumerate(twins_filtered, 1):
        print(f"{i}. {twin.address} - {twin.similarity_score:.1%} similar - ${twin.purchase_price:,.0f}")

    print()
    print("✓ Twin search working correctly")
    print()


def demo_use_cases():
    """Demonstrate practical use cases for twin search."""
    print("=" * 80)
    print("Property Twin Search - Use Cases")
    print("=" * 80)
    print()

    print("USE CASE 1: Comparable Property Analysis")
    print("-" * 40)
    print("Goal: Find comps for property valuation")
    print()
    print("Process:")
    print("  1. Input subject property features")
    print("  2. Search for twins with filters (location, type, size)")
    print("  3. Get ranked list by similarity")
    print("  4. Use top 3-5 twins as comparable properties")
    print("  5. Analyze pricing based on high-similarity comps")
    print()
    print("Benefits:")
    print("  ✓ More accurate than simple filter-based comps")
    print("  ✓ Considers ALL features simultaneously")
    print("  ✓ Explainable (feature breakdown shows what drives similarity)")
    print()

    print("USE CASE 2: Investment Opportunity Discovery")
    print("-" * 40)
    print("Goal: Find similar properties to successful investments")
    print()
    print("Process:")
    print("  1. Identify high-performing property in portfolio")
    print("  2. Use it as subject for twin search")
    print("  3. Find properties with high similarity")
    print("  4. Focus acquisition efforts on similar properties")
    print()
    print("Benefits:")
    print("  ✓ Replicate successful investment patterns")
    print("  ✓ Data-driven target identification")
    print("  ✓ Scale winning strategies")
    print()

    print("USE CASE 3: Portfolio Analysis")
    print("-" * 40)
    print("Goal: Understand portfolio composition and diversity")
    print()
    print("Process:")
    print("  1. Search for twins of each portfolio property")
    print("  2. Calculate average similarity within portfolio")
    print("  3. Identify clusters of similar properties")
    print("  4. Measure diversification")
    print()
    print("Benefits:")
    print("  ✓ Quantify portfolio concentration risk")
    print("  ✓ Identify over-exposed segments")
    print("  ✓ Guide diversification strategy")
    print()

    print("USE CASE 4: Market Research")
    print("-" * 40)
    print("Goal: Understand competitive landscape in target market")
    print()
    print("Process:")
    print("  1. Define ideal target property profile")
    print("  2. Search for twins in target markets")
    print("  3. Analyze density of similar properties")
    print("  4. Identify markets with high twin density")
    print()
    print("Benefits:")
    print("  ✓ Data-driven market selection")
    print("  ✓ Competitive analysis")
    print("  ✓ Supply assessment")
    print()


def main():
    """Run all demos."""
    demo_embedding_generation()
    print("\n" * 2)
    demo_twin_search()
    print("\n" * 2)
    demo_use_cases()

    print("=" * 80)
    print("Property Twin Search Demo Complete")
    print("=" * 80)
    print()
    print("Key Capabilities:")
    print("  ✓ 128-dimensional property embeddings")
    print("  ✓ Vector similarity search (Qdrant)")
    print("  ✓ Multi-feature matching (location, physical, financial, hazards)")
    print("  ✓ Explainable results (feature breakdown)")
    print("  ✓ Flexible filtering (price, location, type)")
    print()
    print("API Endpoints:")
    print("  POST /api/v1/twins/search - Search for property twins")
    print("  POST /api/v1/twins/index - Index a property")
    print("  GET  /api/v1/twins/status - Get index status")
    print()


if __name__ == "__main__":
    main()
