"""
Property Twin Search Engine.

Uses vector similarity search to find properties similar to a subject property.

Process:
1. Generate embedding vector from property features
2. Store embeddings in Qdrant vector database
3. Query Qdrant for nearest neighbors
4. Rank results by similarity score
5. Apply filters (location, price range, property type)
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class PropertyFeatures:
    """Property features for embedding generation."""
    # Location
    latitude: float
    longitude: float
    city: str
    state: str
    zip_code: str

    # Physical characteristics
    building_sqft: Optional[int] = None
    lot_size_sqft: Optional[int] = None
    year_built: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    stories: Optional[int] = None
    parking_spaces: Optional[int] = None

    # Property type
    property_type: str = "Residential"  # Residential, Commercial, Multifamily, Industrial, Land

    # Financial
    purchase_price: Optional[float] = None
    monthly_rent: Optional[float] = None
    property_tax_annual: Optional[float] = None

    # Condition
    condition_score: Optional[float] = None  # 1-10 scale

    # Hazards (from P1.6)
    composite_hazard_score: Optional[float] = None


@dataclass
class PropertyTwin:
    """Similar property result."""
    property_id: str
    similarity_score: float  # 0-1, higher is more similar
    address: str
    city: str
    state: str
    building_sqft: Optional[int]
    purchase_price: Optional[float]
    distance_miles: Optional[float]  # Physical distance from subject
    feature_breakdown: Dict[str, float]  # Contribution of each feature to similarity


class PropertyEmbedding:
    """
    Generates vector embeddings from property features.

    Embedding dimensions (128-d vector):
    - Location: lat/lon normalized, city/state encoded (20-d)
    - Physical: sqft, lot size, year built, bed/bath normalized (30-d)
    - Type: one-hot encoding of property types (10-d)
    - Financial: price, rent, taxes normalized (20-d)
    - Condition: condition score, age-adjusted depreciation (10-d)
    - Hazards: composite hazard score decomposed (10-d)
    - Derived: cap rate, price per sqft, rent per sqft (10-d)
    - Context: neighborhood features, market trends (18-d)
    """

    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim

    def generate_embedding(self, features: PropertyFeatures) -> np.ndarray:
        """
        Generate embedding vector from property features.

        Returns 128-dimensional vector normalized to unit length.
        """
        logger.info(f"Generating embedding for property in {features.city}, {features.state}")

        # Initialize embedding vector
        embedding = np.zeros(self.embedding_dim)

        # Location features (0-19)
        embedding[0] = (features.latitude + 90) / 180  # Normalize to [0,1]
        embedding[1] = (features.longitude + 180) / 360

        # City/state encoding (simple hash for demo, would use learned embeddings in production)
        city_hash = hash(features.city) % 1000 / 1000
        state_hash = hash(features.state) % 1000 / 1000
        embedding[2] = city_hash
        embedding[3] = state_hash

        # Physical characteristics (20-49)
        if features.building_sqft:
            # Normalize sqft: assume range 500-10,000 sqft
            embedding[20] = min((features.building_sqft - 500) / 9500, 1.0)

        if features.lot_size_sqft:
            # Normalize lot: assume range 1,000-50,000 sqft
            embedding[21] = min((features.lot_size_sqft - 1000) / 49000, 1.0)

        if features.year_built:
            # Age normalized: 0 years (2024) to 100 years (1924)
            age = 2024 - features.year_built
            embedding[22] = min(age / 100, 1.0)

        if features.bedrooms:
            embedding[23] = min(features.bedrooms / 10, 1.0)  # Max 10 bedrooms

        if features.bathrooms:
            embedding[24] = min(features.bathrooms / 10, 1.0)

        if features.stories:
            embedding[25] = min(features.stories / 10, 1.0)

        if features.parking_spaces:
            embedding[26] = min(features.parking_spaces / 10, 1.0)

        # Property type one-hot (50-59)
        property_types = ["Residential", "Commercial", "Multifamily", "Industrial", "Land",
                         "Office", "Retail", "Warehouse", "Mixed-Use", "Other"]
        try:
            type_idx = property_types.index(features.property_type)
            embedding[50 + type_idx] = 1.0
        except ValueError:
            embedding[59] = 1.0  # Other

        # Financial features (60-79)
        if features.purchase_price:
            # Normalize price: assume $100k to $10M range
            embedding[60] = min((features.purchase_price - 100000) / 9900000, 1.0)

        if features.monthly_rent:
            # Normalize rent: $500 to $10k/month
            embedding[61] = min((features.monthly_rent - 500) / 9500, 1.0)

        if features.property_tax_annual:
            # Normalize tax: $1k to $100k/year
            embedding[62] = min((features.property_tax_annual - 1000) / 99000, 1.0)

        # Derived financial metrics
        if features.purchase_price and features.building_sqft:
            price_per_sqft = features.purchase_price / features.building_sqft
            embedding[63] = min(price_per_sqft / 1000, 1.0)  # $0-1000/sqft

        if features.monthly_rent and features.building_sqft:
            rent_per_sqft = features.monthly_rent / features.building_sqft
            embedding[64] = min(rent_per_sqft / 10, 1.0)  # $0-10/sqft/month

        if features.monthly_rent and features.purchase_price:
            # Cap rate approximation
            annual_noi = features.monthly_rent * 12 * 0.6  # Assume 60% net margin
            cap_rate = annual_noi / features.purchase_price if features.purchase_price > 0 else 0
            embedding[65] = min(cap_rate / 0.15, 1.0)  # 0-15% cap rate

        # Condition features (80-89)
        if features.condition_score:
            embedding[80] = features.condition_score / 10  # 1-10 scale

        # Hazard features (90-99)
        if features.composite_hazard_score is not None:
            embedding[90] = features.composite_hazard_score  # Already 0-1

        # Normalize to unit length
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding


class PropertyTwinSearch:
    """
    Property twin search engine using Qdrant vector similarity.
    """

    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.qdrant_url = qdrant_url
        self.collection_name = "property_embeddings"
        self.embedding_generator = PropertyEmbedding()

    def index_property(
        self,
        property_id: str,
        features: PropertyFeatures
    ):
        """
        Generate embedding and index property in Qdrant.

        Args:
            property_id: Unique property identifier
            features: Property features
        """
        logger.info(f"Indexing property {property_id}")

        # Generate embedding
        embedding = self.embedding_generator.generate_embedding(features)

        # In production: Store in Qdrant
        # from qdrant_client import QdrantClient
        # client = QdrantClient(self.qdrant_url)
        # client.upsert(
        #     collection_name=self.collection_name,
        #     points=[
        #         {
        #             "id": property_id,
        #             "vector": embedding.tolist(),
        #             "payload": {
        #                 "address": features.address,
        #                 "city": features.city,
        #                 "state": features.state,
        #                 "property_type": features.property_type,
        #                 "building_sqft": features.building_sqft,
        #                 "purchase_price": features.purchase_price,
        #                 ...
        #             }
        #         }
        #     ]
        # )

        logger.info(f"Property {property_id} indexed with {len(embedding)}-d embedding")

    def search_twins(
        self,
        subject_features: PropertyFeatures,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[PropertyTwin]:
        """
        Find similar properties (twins).

        Args:
            subject_features: Features of subject property
            limit: Maximum number of twins to return
            filters: Optional filters (location, price range, property type)

        Returns:
            List of PropertyTwin objects ordered by similarity
        """
        logger.info(f"Searching for twins in {subject_features.city}, {subject_features.state}")

        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(subject_features)

        # In production: Query Qdrant
        # client = QdrantClient(self.qdrant_url)
        # search_result = client.search(
        #     collection_name=self.collection_name,
        #     query_vector=query_embedding.tolist(),
        #     limit=limit,
        #     query_filter=self._build_qdrant_filter(filters)
        # )
        #
        # twins = []
        # for hit in search_result:
        #     twin = PropertyTwin(
        #         property_id=hit.id,
        #         similarity_score=hit.score,
        #         address=hit.payload["address"],
        #         city=hit.payload["city"],
        #         state=hit.payload["state"],
        #         building_sqft=hit.payload.get("building_sqft"),
        #         purchase_price=hit.payload.get("purchase_price"),
        #         distance_miles=self._calculate_distance(
        #             subject_features.latitude,
        #             subject_features.longitude,
        #             hit.payload["latitude"],
        #             hit.payload["longitude"]
        #         ),
        #         feature_breakdown=self._explain_similarity(
        #             query_embedding,
        #             hit.vector
        #         )
        #     )
        #     twins.append(twin)

        # Mock response for now
        twins = [
            PropertyTwin(
                property_id=f"TWIN-{i+1:03d}",
                similarity_score=0.95 - (i * 0.05),
                address=f"{1000 + i*100} Similar St",
                city=subject_features.city,
                state=subject_features.state,
                building_sqft=subject_features.building_sqft + np.random.randint(-200, 200) if subject_features.building_sqft else None,
                purchase_price=subject_features.purchase_price * (1 + np.random.uniform(-0.1, 0.1)) if subject_features.purchase_price else None,
                distance_miles=np.random.uniform(0.5, 5.0),
                feature_breakdown={
                    "location": 0.25,
                    "physical": 0.30,
                    "financial": 0.25,
                    "condition": 0.15,
                    "hazards": 0.05
                }
            )
            for i in range(min(limit, 5))
        ]

        logger.info(f"Found {len(twins)} twins")

        return twins

    def _build_qdrant_filter(self, filters: Optional[Dict[str, Any]]) -> Dict:
        """Build Qdrant filter from user filters."""
        if not filters:
            return {}

        # Example filter structure:
        # {
        #     "must": [
        #         {"key": "property_type", "match": {"value": "Residential"}},
        #         {"key": "purchase_price", "range": {"gte": 500000, "lte": 1500000}}
        #     ]
        # }

        qdrant_filter = {"must": []}

        if "property_type" in filters:
            qdrant_filter["must"].append({
                "key": "property_type",
                "match": {"value": filters["property_type"]}
            })

        if "min_price" in filters or "max_price" in filters:
            price_range = {}
            if "min_price" in filters:
                price_range["gte"] = filters["min_price"]
            if "max_price" in filters:
                price_range["lte"] = filters["max_price"]
            qdrant_filter["must"].append({
                "key": "purchase_price",
                "range": price_range
            })

        if "city" in filters:
            qdrant_filter["must"].append({
                "key": "city",
                "match": {"value": filters["city"]}
            })

        return qdrant_filter

    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calculate distance between two coordinates in miles (Haversine)."""
        from math import radians, cos, sin, asin, sqrt

        # Convert to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 3956  # Radius of earth in miles

        return c * r

    def _explain_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> Dict[str, float]:
        """
        Explain which features contribute most to similarity.

        Breaks down similarity by feature group.
        """
        # Calculate similarity contribution by dimension ranges
        location_sim = np.dot(embedding1[0:20], embedding2[0:20])
        physical_sim = np.dot(embedding1[20:50], embedding2[20:50])
        type_sim = np.dot(embedding1[50:60], embedding2[50:60])
        financial_sim = np.dot(embedding1[60:80], embedding2[60:80])
        condition_sim = np.dot(embedding1[80:90], embedding2[80:90])
        hazard_sim = np.dot(embedding1[90:100], embedding2[90:100])

        total = location_sim + physical_sim + type_sim + financial_sim + condition_sim + hazard_sim

        if total > 0:
            return {
                "location": location_sim / total,
                "physical": physical_sim / total,
                "type": type_sim / total,
                "financial": financial_sim / total,
                "condition": condition_sim / total,
                "hazards": hazard_sim / total
            }
        else:
            return {}


if __name__ == "__main__":
    # Test twin search
    search_engine = PropertyTwinSearch()

    # Subject property
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
        property_type="Residential",
        purchase_price=1200000,
        condition_score=7.5,
        composite_hazard_score=0.45
    )

    # Index subject
    search_engine.index_property("SUBJECT-001", subject)

    # Find twins
    twins = search_engine.search_twins(subject, limit=10)

    print(f"\nFound {len(twins)} property twins for {subject.city}, {subject.state}:\n")
    for i, twin in enumerate(twins, 1):
        print(f"{i}. {twin.address}")
        print(f"   Similarity: {twin.similarity_score:.2%}")
        print(f"   Size: {twin.building_sqft:,} sqft" if twin.building_sqft else "")
        print(f"   Price: ${twin.purchase_price:,.0f}" if twin.purchase_price else "")
        print(f"   Distance: {twin.distance_miles:.1f} miles")
        print(f"   Feature breakdown: {twin.feature_breakdown}")
        print()

    print("Property twin search test complete")
