"""
Embedding Indexer

Syncs property embeddings from trained Portfolio Twin to Qdrant.

Usage:
    python ml/embeddings/indexer.py --tenant-id <uuid> --model-path <path>

Part of Wave 2.2 - Qdrant indexing pipeline.
"""

import argparse
import logging
from typing import List, Optional
import torch
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm
import os

from db.models import Property
from ml.models.portfolio_twin import (
    PortfolioTwinEncoder,
    PortfolioTwin,
    PropertyFeatures
)
from ml.embeddings.qdrant_client import QdrantVectorDB, PropertyEmbedding
from ml.training.data_loader import PropertyDataset


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PropertyEmbeddingIndexer:
    """
    Index property embeddings into Qdrant

    Loads properties from database, generates embeddings using trained
    Portfolio Twin encoder, and indexes them in Qdrant for fast similarity search.
    """

    def __init__(
        self,
        model_path: str,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        device: str = "cpu"
    ):
        """
        Initialize indexer

        Args:
            model_path: Path to trained Portfolio Twin model
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            device: Device for inference (cpu, cuda, mps)
        """
        self.device = torch.device(device)
        self.model = self._load_model(model_path)
        self.model.eval()

        self.qdrant = QdrantVectorDB(host=qdrant_host, port=qdrant_port)

        logger.info(f"Loaded model from {model_path}")
        logger.info(f"Connected to Qdrant at {qdrant_host}:{qdrant_port}")

    def _load_model(self, model_path: str) -> PortfolioTwin:
        """Load trained Portfolio Twin model"""
        checkpoint = torch.load(model_path, map_location=self.device)

        # Create encoder
        encoder = PortfolioTwinEncoder(input_dim=25, embedding_dim=16)

        # Infer num_users from checkpoint
        user_emb_weight = checkpoint['model_state_dict']['user_embeddings.weight']
        num_users = user_emb_weight.shape[0]

        # Create model
        model = PortfolioTwin(
            property_encoder=encoder,
            num_users=num_users,
            embedding_dim=16
        )

        # Load weights
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(self.device)

        return model

    def _extract_property_features(self, property: Property) -> PropertyFeatures:
        """Extract PropertyFeatures from Property model"""
        address = property.canonical_address or {}

        listing_price = property.listing_price or 0.0
        estimated_value = property.estimated_value or listing_price
        square_footage = property.square_footage or 1500

        price_per_sqft = listing_price / square_footage if square_footage > 0 else 0

        # Get average confidence from provenance
        # TODO: Query FieldProvenance table
        confidence = 0.8  # Placeholder

        return PropertyFeatures(
            listing_price=float(listing_price),
            price_per_sqft=float(price_per_sqft),
            estimated_value=float(estimated_value),
            cap_rate=getattr(property, 'cap_rate', None),
            cash_on_cash_return=getattr(property, 'cash_on_cash_return', None),
            bedrooms=int(property.bedrooms or 3),
            bathrooms=float(property.bathrooms or 2.0),
            square_footage=int(square_footage),
            lot_size_sqft=int(property.lot_size_sqft or 5000),
            year_built=int(property.year_built or 2000),
            lat=float(address.get('lat', 0.0)),
            lon=float(address.get('lon', 0.0)),
            zipcode=str(address.get('zipcode', '00000')),
            days_on_market=int(getattr(property, 'days_on_market', 0)),
            listing_status=str(getattr(property, 'listing_status', 'Active')),
            condition_score=float(getattr(property, 'condition_score', 0.7)),
            renovation_needed=bool(getattr(property, 'renovation_needed', False)),
            property_type=str(property.property_type or 'Single Family'),
            source_system=str(getattr(property, 'source_system', 'unknown')),
            confidence=float(confidence)
        )

    def _generate_embedding(self, property_features: PropertyFeatures) -> np.ndarray:
        """Generate embedding for property"""
        feature_vector = property_features.to_vector()
        feature_tensor = torch.from_numpy(feature_vector).unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self.model.property_encoder(feature_tensor)
            # Normalize
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)
            embedding_np = embedding.cpu().numpy().squeeze()

        return embedding_np

    def index_all_properties(
        self,
        db_session,
        tenant_id: str,
        batch_size: int = 100,
        recreate_collection: bool = False
    ) -> int:
        """
        Index all properties for a tenant

        Args:
            db_session: Database session
            tenant_id: Tenant ID
            batch_size: Batch size for indexing
            recreate_collection: If True, recreate Qdrant collection

        Returns:
            Number of properties indexed
        """
        # Set RLS context
        db_session.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")

        # Create/recreate collection
        if recreate_collection:
            logger.info("Recreating Qdrant collections...")
            self.qdrant.create_collections(embedding_dim=16, recreate=True)
        else:
            logger.info("Ensuring Qdrant collections exist...")
            self.qdrant.create_collections(embedding_dim=16, recreate=False)

        # Get all properties
        logger.info("Loading properties from database...")
        properties = db_session.query(Property).all()
        logger.info(f"Found {len(properties)} properties")

        # Process in batches
        total_indexed = 0
        property_embeddings = []

        for i, property in enumerate(tqdm(properties, desc="Generating embeddings")):
            try:
                # Extract features
                prop_features = self._extract_property_features(property)

                # Generate embedding
                embedding = self._generate_embedding(prop_features)

                # Create PropertyEmbedding
                prop_emb = PropertyEmbedding(
                    property_id=str(property.id),
                    embedding=embedding,
                    tenant_id=tenant_id,
                    listing_price=prop_features.listing_price,
                    bedrooms=prop_features.bedrooms,
                    bathrooms=prop_features.bathrooms,
                    property_type=prop_features.property_type,
                    zipcode=prop_features.zipcode,
                    confidence=prop_features.confidence
                )

                property_embeddings.append(prop_emb)

                # Index batch
                if len(property_embeddings) >= batch_size:
                    self.qdrant.index_properties_batch(property_embeddings)
                    total_indexed += len(property_embeddings)
                    property_embeddings = []

            except Exception as e:
                logger.warning(f"Failed to index property {property.id}: {e}")
                continue

        # Index remaining
        if property_embeddings:
            self.qdrant.index_properties_batch(property_embeddings)
            total_indexed += len(property_embeddings)

        logger.info(f"Successfully indexed {total_indexed} properties")

        return total_indexed

    def index_property(
        self,
        db_session,
        property_id: str,
        tenant_id: str
    ) -> bool:
        """
        Index a single property

        Args:
            db_session: Database session
            property_id: Property ID
            tenant_id: Tenant ID

        Returns:
            True if successful
        """
        # Set RLS context
        db_session.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")

        # Load property
        property = db_session.query(Property).filter(Property.id == property_id).first()

        if not property:
            logger.error(f"Property {property_id} not found")
            return False

        try:
            # Extract features
            prop_features = self._extract_property_features(property)

            # Generate embedding
            embedding = self._generate_embedding(prop_features)

            # Create PropertyEmbedding
            prop_emb = PropertyEmbedding(
                property_id=str(property.id),
                embedding=embedding,
                tenant_id=tenant_id,
                listing_price=prop_features.listing_price,
                bedrooms=prop_features.bedrooms,
                bathrooms=prop_features.bathrooms,
                property_type=prop_features.property_type,
                zipcode=prop_features.zipcode,
                confidence=prop_features.confidence
            )

            # Index
            self.qdrant.index_property(prop_emb)

            logger.info(f"Indexed property {property_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to index property {property_id}: {e}")
            return False

    def delete_property(self, property_id: str):
        """Delete property from index"""
        self.qdrant.delete_property(property_id)

    def get_stats(self) -> dict:
        """Get indexing statistics"""
        return self.qdrant.get_collection_info("property_embeddings")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Index property embeddings in Qdrant')

    # Required
    parser.add_argument('--tenant-id', type=str, required=True,
                        help='Tenant ID')
    parser.add_argument('--model-path', type=str,
                        default='ml/serving/models/portfolio_twin.pt',
                        help='Path to trained Portfolio Twin model')

    # Database
    parser.add_argument('--db-url', type=str,
                        default=os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/realestate'),
                        help='Database URL')

    # Qdrant
    parser.add_argument('--qdrant-host', type=str, default='localhost',
                        help='Qdrant server host')
    parser.add_argument('--qdrant-port', type=int, default=6333,
                        help='Qdrant server port')

    # Options
    parser.add_argument('--batch-size', type=int, default=100,
                        help='Batch size for indexing')
    parser.add_argument('--recreate', action='store_true',
                        help='Recreate Qdrant collections')
    parser.add_argument('--device', type=str, default='cpu',
                        choices=['cpu', 'cuda', 'mps'],
                        help='Device for inference')

    return parser.parse_args()


def main():
    """Main indexing function"""
    args = parse_args()

    # Setup database
    logger.info(f"Connecting to database: {args.db_url}")
    engine = create_engine(args.db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()

    # Create indexer
    logger.info("Creating indexer...")
    indexer = PropertyEmbeddingIndexer(
        model_path=args.model_path,
        qdrant_host=args.qdrant_host,
        qdrant_port=args.qdrant_port,
        device=args.device
    )

    # Index all properties
    logger.info(f"Indexing properties for tenant {args.tenant_id}...")
    num_indexed = indexer.index_all_properties(
        db_session=db_session,
        tenant_id=args.tenant_id,
        batch_size=args.batch_size,
        recreate_collection=args.recreate
    )

    # Get stats
    stats = indexer.get_stats()
    logger.info("\n" + "="*50)
    logger.info("INDEXING COMPLETE")
    logger.info("="*50)
    logger.info(f"Properties indexed: {num_indexed}")
    logger.info(f"Vectors in Qdrant: {stats['vectors_count']}")
    logger.info(f"Collection status: {stats['status']}")

    db_session.close()


if __name__ == '__main__':
    main()
