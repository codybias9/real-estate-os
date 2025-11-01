"""Main scoring agent

Applies ML model to score properties and stores results in database.
"""
import logging
import os
from typing import List, Dict, Any, Optional
import psycopg2
import psycopg2.extras
import json
from datetime import datetime

from .feature_engineering import FeatureEngineer
from .vector_embeddings import PropertyVectorStore, PropertyEmbedder
from .model_training import ModelTrainer

logger = logging.getLogger(__name__)


class ScoringAgent:
    """
    Main scoring agent

    Workflow:
    1. Load trained model from storage
    2. Fetch enriched properties from database
    3. Extract features using FeatureEngineer
    4. Generate predictions using LightGBM
    5. Create vector embeddings
    6. Store in Qdrant vector database
    7. Store scores in property_scores table
    """

    def __init__(
        self,
        database_url: str,
        model_path: str,
        qdrant_url: Optional[str] = None,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333
    ):
        """
        Initialize scoring agent

        Args:
            database_url: PostgreSQL connection string
            model_path: Path to trained model (without extension)
            qdrant_url: Full Qdrant URL
            qdrant_host: Qdrant host
            qdrant_port: Qdrant port
        """
        self.database_url = database_url
        self.model_path = model_path

        # Initialize components
        self.feature_engineer = FeatureEngineer()

        self.model = ModelTrainer()
        if os.path.exists(f"{model_path}.txt"):
            self.model.load_model(model_path)
            logger.info(f"Loaded model from {model_path}")
        else:
            logger.warning(f"Model not found at {model_path}. Call train_model() first.")

        self.vector_store = PropertyVectorStore(
            qdrant_url=qdrant_url,
            qdrant_host=qdrant_host,
            qdrant_port=qdrant_port
        )

        self.embedder = PropertyEmbedder()

        logger.info("ScoringAgent initialized")

    def score_batch(self, prospect_ids: List[int]) -> Dict[str, Any]:
        """
        Score a batch of properties

        Args:
            prospect_ids: List of prospect IDs to score

        Returns:
            Dictionary with scoring results and statistics
        """
        logger.info(f"Starting scoring batch: {len(prospect_ids)} prospects")

        if self.model.model is None:
            raise ValueError("Model not loaded. Cannot score properties.")

        results = {
            'total': len(prospect_ids),
            'succeeded': 0,
            'failed': 0,
            'errors': []
        }

        conn = None
        try:
            conn = psycopg2.connect(self.database_url)

            for prospect_id in prospect_ids:
                try:
                    success = self.score_single_property(prospect_id, conn)
                    if success:
                        results['succeeded'] += 1
                    else:
                        results['failed'] += 1

                except Exception as e:
                    logger.error(f"Failed to score prospect {prospect_id}: {e}")
                    results['failed'] += 1
                    results['errors'].append({
                        'prospect_id': prospect_id,
                        'error': str(e)
                    })

            conn.commit()

        except Exception as e:
            logger.error(f"Batch scoring error: {e}")
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                conn.close()

        logger.info(f"Scoring batch complete: {results['succeeded']}/{results['total']} succeeded")

        return results

    def score_single_property(self, prospect_id: int, conn) -> bool:
        """
        Score a single property

        Args:
            prospect_id: Prospect ID to score
            conn: Database connection

        Returns:
            True if scoring succeeded
        """
        logger.info(f"Scoring prospect {prospect_id}")

        # Fetch data
        data = self._fetch_property_data(prospect_id, conn)

        if not data:
            logger.error(f"Property data not found for prospect {prospect_id}")
            return False

        prospect = data['prospect']
        enrichment = data.get('enrichment')

        if not enrichment:
            logger.warning(f"No enrichment data for prospect {prospect_id}")
            # Continue anyway - some features can be extracted from prospect alone

        # Extract features
        features = self.feature_engineer.extract_features(prospect, enrichment)
        feature_vector = self.feature_engineer.get_feature_vector(features)

        logger.debug(f"Extracted {len(feature_vector)} features")

        # Predict score
        import numpy as np
        score = self.model.predict(np.array([feature_vector]))[0]

        # Clip to 0-100 range
        score = float(np.clip(score, 0, 100))

        logger.info(f"Predicted score: {score:.2f}")

        # Get feature importance from model
        feature_importance = self.model.get_feature_importance()

        # Create feature importance dict for this prediction
        score_breakdown = {
            'feature_contributions': {
                name: features.get(name, 0.0) * feature_importance.get(name, 0.0)
                for name in self.feature_engineer.FEATURE_NAMES[:10]  # Top 10
            }
        }

        # Create vector embedding
        embedding = self.embedder.embed_property_features(feature_vector)

        # Store in Qdrant
        point_id = self.vector_store.store_property_vector(
            prospect_id=prospect_id,
            feature_vector=embedding,
            metadata={
                'score': score,
                'listing_price': features.get('listing_price', 0),
                'square_footage': features.get('square_footage', 0),
                'bedrooms': features.get('bedrooms', 0),
            }
        )

        logger.debug(f"Stored vector in Qdrant: {point_id}")

        # Get model version
        model_version = self._get_model_version()

        # Store score in database
        success = self._store_score(
            prospect_id=prospect_id,
            enrichment_id=enrichment.get('id') if enrichment else None,
            score=score,
            model_version=model_version,
            feature_vector=feature_vector,
            feature_importance=feature_importance,
            score_breakdown=score_breakdown,
            qdrant_point_id=point_id,
            conn=conn
        )

        return success

    def _fetch_property_data(self, prospect_id: int, conn) -> Optional[Dict]:
        """Fetch prospect and enrichment data"""
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Fetch prospect
        cursor.execute(
            "SELECT id, source, source_id, url, payload, status FROM prospect_queue WHERE id = %s",
            (prospect_id,)
        )
        prospect = cursor.fetchone()

        if not prospect:
            cursor.close()
            return None

        # Fetch enrichment
        cursor.execute(
            """
            SELECT * FROM property_enrichment WHERE prospect_id = %s
            """,
            (prospect_id,)
        )
        enrichment = cursor.fetchone()

        cursor.close()

        return {
            'prospect': dict(prospect),
            'enrichment': dict(enrichment) if enrichment else None
        }

    def _get_model_version(self) -> str:
        """Get current model version"""
        # In production, this would query ml_models table for active model
        # For now, use timestamp from model path
        if hasattr(self.model, 'training_history') and self.model.training_history:
            last_training = self.model.training_history[-1]
            return last_training.get('timestamp', 'unknown')

        return 'v1.0'

    def _store_score(
        self,
        prospect_id: int,
        enrichment_id: Optional[int],
        score: float,
        model_version: str,
        feature_vector: List[float],
        feature_importance: Dict[str, float],
        score_breakdown: Dict[str, Any],
        qdrant_point_id: str,
        conn
    ) -> bool:
        """Store score in database"""
        try:
            cursor = conn.cursor()

            # Convert to JSON
            feature_vector_json = json.dumps(feature_vector)
            feature_importance_json = json.dumps(feature_importance)
            score_breakdown_json = json.dumps(score_breakdown)

            # Calculate confidence level (simplified)
            # In production, this could be based on feature completeness, model uncertainty, etc.
            confidence = min(100.0, 80.0 + (score / 100.0) * 20.0)

            query = """
                INSERT INTO property_scores (
                    prospect_id, enrichment_id, bird_dog_score, model_version,
                    feature_vector, feature_importance, score_breakdown,
                    confidence_level, qdrant_point_id, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (prospect_id)
                DO UPDATE SET
                    enrichment_id = EXCLUDED.enrichment_id,
                    bird_dog_score = EXCLUDED.bird_dog_score,
                    model_version = EXCLUDED.model_version,
                    feature_vector = EXCLUDED.feature_vector,
                    feature_importance = EXCLUDED.feature_importance,
                    score_breakdown = EXCLUDED.score_breakdown,
                    confidence_level = EXCLUDED.confidence_level,
                    qdrant_point_id = EXCLUDED.qdrant_point_id,
                    created_at = NOW()
            """

            cursor.execute(query, (
                prospect_id,
                enrichment_id,
                score,
                model_version,
                feature_vector_json,
                feature_importance_json,
                score_breakdown_json,
                confidence,
                qdrant_point_id
            ))

            cursor.close()

            logger.info(f"Stored score for prospect {prospect_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store score: {e}")
            return False

    def get_similar_properties(
        self,
        prospect_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find properties similar to given prospect

        Args:
            prospect_id: Reference prospect ID
            limit: Maximum number of results

        Returns:
            List of similar properties with scores
        """
        conn = None
        try:
            conn = psycopg2.connect(self.database_url)

            # Get the property's features
            data = self._fetch_property_data(prospect_id, conn)

            if not data:
                logger.error(f"Property not found: {prospect_id}")
                return []

            # Extract features
            features = self.feature_engineer.extract_features(
                data['prospect'],
                data.get('enrichment')
            )
            feature_vector = self.feature_engineer.get_feature_vector(features)

            # Create embedding
            embedding = self.embedder.embed_property_features(feature_vector)

            # Search Qdrant
            similar = self.vector_store.search_similar_properties(
                feature_vector=embedding,
                limit=limit + 1  # +1 because it might include itself
            )

            # Filter out self
            similar = [s for s in similar if s['prospect_id'] != prospect_id][:limit]

            return similar

        except Exception as e:
            logger.error(f"Failed to find similar properties: {e}")
            return []

        finally:
            if conn:
                conn.close()


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Property Scoring Agent")
    parser.add_argument('--prospect-ids', type=str, required=True,
                       help='Comma-separated prospect IDs to score')
    parser.add_argument('--db-dsn', type=str, default=os.getenv('DB_DSN'),
                       help='Database connection string')
    parser.add_argument('--model-path', type=str, default='/models/lightgbm_latest',
                       help='Path to trained model')
    parser.add_argument('--qdrant-url', type=str, default=os.getenv('QDRANT_URL'),
                       help='Qdrant URL')
    parser.add_argument('--qdrant-host', type=str, default='localhost',
                       help='Qdrant host')
    parser.add_argument('--qdrant-port', type=int, default=6333,
                       help='Qdrant port')

    args = parser.parse_args()

    # Parse prospect IDs
    prospect_ids = [int(pid.strip()) for pid in args.prospect_ids.split(',')]

    # Initialize agent
    agent = ScoringAgent(
        database_url=args.db_dsn,
        model_path=args.model_path,
        qdrant_url=args.qdrant_url,
        qdrant_host=args.qdrant_host,
        qdrant_port=args.qdrant_port
    )

    # Run scoring
    results = agent.score_batch(prospect_ids)

    print(f"\nScoring Results:")
    print(f"  Total: {results['total']}")
    print(f"  Succeeded: {results['succeeded']}")
    print(f"  Failed: {results['failed']}")

    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  Prospect {error['prospect_id']}: {error['error']}")


if __name__ == "__main__":
    main()
