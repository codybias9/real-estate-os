"""
Portfolio Twin Model Serving Service

FastAPI service for serving Portfolio Twin predictions.

Endpoints:
- POST /predict - Get affinity score for property
- POST /recommend - Get top-K property recommendations
- GET /embedding - Get property embedding
- POST /batch_predict - Batch prediction

Part of Wave 2.1 - Portfolio Twin serving infrastructure.
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import torch
import numpy as np
from pathlib import Path
import logging
from uuid import UUID

from ml.models.portfolio_twin import (
    PortfolioTwinEncoder,
    PortfolioTwin,
    PropertyFeatures
)


logger = logging.getLogger(__name__)


# Request/Response models
class PropertyPredictionRequest(BaseModel):
    """Request for property affinity prediction"""
    user_id: int
    property_features: Dict

    class Config:
        schema_extra = {
            "example": {
                "user_id": 1,
                "property_features": {
                    "listing_price": 500000,
                    "bedrooms": 3,
                    "bathrooms": 2.0,
                    "square_footage": 2000,
                    "lat": 37.7749,
                    "lon": -122.4194,
                    "property_type": "Single Family"
                }
            }
        }


class PropertyPredictionResponse(BaseModel):
    """Response with affinity score"""
    user_id: int
    affinity_score: float = Field(..., ge=0.0, le=1.0, description="Affinity score [0, 1]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")


class RecommendationRequest(BaseModel):
    """Request for property recommendations"""
    user_id: int
    candidate_property_ids: List[str]
    top_k: int = Field(default=10, ge=1, le=100)


class RecommendationResponse(BaseModel):
    """Response with ranked property recommendations"""
    user_id: int
    recommendations: List[Dict[str, float]]  # [{"property_id": "...", "score": 0.9}, ...]


class EmbeddingRequest(BaseModel):
    """Request for property embedding"""
    property_features: Dict


class EmbeddingResponse(BaseModel):
    """Response with property embedding"""
    embedding: List[float]
    embedding_dim: int


class BatchPredictionRequest(BaseModel):
    """Request for batch predictions"""
    user_id: int
    properties: List[Dict]


class BatchPredictionResponse(BaseModel):
    """Response with batch predictions"""
    user_id: int
    predictions: List[Dict[str, float]]  # [{"property_id": "...", "score": 0.9}, ...]


# Model serving class
class PortfolioTwinService:
    """
    Portfolio Twin model serving service

    Loads trained model and provides inference API.
    """

    def __init__(self, model_path: str, device: str = 'cpu'):
        """
        Initialize service

        Args:
            model_path: Path to trained model checkpoint
            device: Device to run inference on
        """
        self.device = torch.device(device)
        self.model = self._load_model(model_path)
        self.model.eval()

        logger.info(f"Loaded Portfolio Twin model from {model_path}")
        logger.info(f"Running on device: {self.device}")

    def _load_model(self, model_path: str) -> PortfolioTwin:
        """Load trained model from checkpoint"""
        checkpoint = torch.load(model_path, map_location=self.device)

        # Create model architecture
        encoder = PortfolioTwinEncoder(input_dim=25, embedding_dim=16)

        # Infer num_users from checkpoint
        user_emb_weight = checkpoint['model_state_dict']['user_embeddings.weight']
        num_users = user_emb_weight.shape[0]

        model = PortfolioTwin(
            property_encoder=encoder,
            num_users=num_users,
            embedding_dim=16
        )

        # Load weights
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(self.device)

        return model

    def _dict_to_property_features(self, feature_dict: Dict) -> PropertyFeatures:
        """Convert dictionary to PropertyFeatures"""
        return PropertyFeatures(
            listing_price=float(feature_dict.get('listing_price', 0)),
            price_per_sqft=float(feature_dict.get('price_per_sqft', 0)),
            estimated_value=float(feature_dict.get('estimated_value', 0)),
            cap_rate=feature_dict.get('cap_rate'),
            cash_on_cash_return=feature_dict.get('cash_on_cash_return'),
            bedrooms=int(feature_dict.get('bedrooms', 3)),
            bathrooms=float(feature_dict.get('bathrooms', 2.0)),
            square_footage=int(feature_dict.get('square_footage', 2000)),
            lot_size_sqft=int(feature_dict.get('lot_size_sqft', 5000)),
            year_built=int(feature_dict.get('year_built', 2000)),
            lat=float(feature_dict.get('lat', 0.0)),
            lon=float(feature_dict.get('lon', 0.0)),
            zipcode=str(feature_dict.get('zipcode', '00000')),
            days_on_market=int(feature_dict.get('days_on_market', 0)),
            listing_status=str(feature_dict.get('listing_status', 'Active')),
            condition_score=float(feature_dict.get('condition_score', 0.7)),
            renovation_needed=bool(feature_dict.get('renovation_needed', False)),
            property_type=str(feature_dict.get('property_type', 'Single Family')),
            source_system=str(feature_dict.get('source_system', 'unknown')),
            confidence=float(feature_dict.get('confidence', 0.5))
        )

    def predict_affinity(
        self,
        user_id: int,
        property_features: PropertyFeatures
    ) -> tuple[float, float]:
        """
        Predict user's affinity for a property

        Args:
            user_id: User ID
            property_features: Property features

        Returns:
            (affinity_score, confidence)
        """
        # Convert to tensor
        feature_vector = property_features.to_vector()
        feature_tensor = torch.from_numpy(feature_vector).unsqueeze(0).to(self.device)

        # Predict
        with torch.no_grad():
            affinity = self.model.predict_affinity(feature_tensor, user_id)
            score = affinity.item()

        # Confidence is based on property feature confidence
        confidence = property_features.confidence

        return score, confidence

    def recommend_properties(
        self,
        user_id: int,
        candidate_properties: List[PropertyFeatures],
        top_k: int = 10
    ) -> List[tuple[int, float]]:
        """
        Recommend top-K properties for user

        Args:
            user_id: User ID
            candidate_properties: List of candidate properties
            top_k: Number of recommendations

        Returns:
            List of (property_index, score) tuples
        """
        # Convert to tensors
        feature_vectors = [p.to_vector() for p in candidate_properties]
        feature_tensor = torch.from_numpy(
            np.stack(feature_vectors)
        ).to(self.device)

        # Predict affinities
        with torch.no_grad():
            affinities = self.model.predict_affinity(feature_tensor, user_id)
            scores = affinities.cpu().numpy()

        # Get top K
        top_indices = np.argsort(-scores)[:top_k]
        recommendations = [(int(i), float(scores[i])) for i in top_indices]

        return recommendations

    def get_embedding(self, property_features: PropertyFeatures) -> np.ndarray:
        """
        Get property embedding

        Args:
            property_features: Property features

        Returns:
            Embedding vector
        """
        feature_vector = property_features.to_vector()
        feature_tensor = torch.from_numpy(feature_vector).unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self.model.property_encoder(feature_tensor)
            embedding = embedding.cpu().numpy().squeeze()

        return embedding


# Create FastAPI app
app = FastAPI(
    title="Portfolio Twin Service",
    description="ML service for property affinity prediction",
    version="1.0.0"
)

# Global service instance
service: Optional[PortfolioTwinService] = None


@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    global service

    model_path = Path("ml/serving/models/portfolio_twin.pt")

    if not model_path.exists():
        logger.warning(f"Model not found at {model_path}. Service will not be available.")
        return

    try:
        service = PortfolioTwinService(str(model_path), device='cpu')
        logger.info("Portfolio Twin service started successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if service is not None else "model_not_loaded",
        "service": "portfolio_twin",
        "version": "1.0.0"
    }


@app.post("/predict", response_model=PropertyPredictionResponse)
async def predict_affinity(request: PropertyPredictionRequest):
    """
    Predict user's affinity for a property

    Returns a score [0, 1] indicating how well the property matches user's preferences.
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Convert dict to PropertyFeatures
        prop_features = service._dict_to_property_features(request.property_features)

        # Predict
        score, confidence = service.predict_affinity(request.user_id, prop_features)

        return PropertyPredictionResponse(
            user_id=request.user_id,
            affinity_score=score,
            confidence=confidence
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_properties(request: RecommendationRequest):
    """
    Get top-K property recommendations for user

    Ranks candidate properties by affinity score.
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Load candidate properties from database
        # TODO: Implement property loading from IDs
        # For now, return mock response

        recommendations = [
            {"property_id": prop_id, "score": 0.0}
            for prop_id in request.candidate_property_ids[:request.top_k]
        ]

        return RecommendationResponse(
            user_id=request.user_id,
            recommendations=recommendations
        )
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embedding", response_model=EmbeddingResponse)
async def get_embedding(request: EmbeddingRequest):
    """
    Get property embedding vector

    Returns a 16-dimensional embedding representing the property in learned space.
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        prop_features = service._dict_to_property_features(request.property_features)
        embedding = service.get_embedding(prop_features)

        return EmbeddingResponse(
            embedding=embedding.tolist(),
            embedding_dim=len(embedding)
        )
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch_predict", response_model=BatchPredictionResponse)
async def batch_predict(request: BatchPredictionRequest):
    """
    Batch prediction for multiple properties

    More efficient than calling /predict multiple times.
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Convert all properties
        property_features = [
            service._dict_to_property_features(prop)
            for prop in request.properties
        ]

        # Get recommendations (includes all properties with scores)
        recommendations = service.recommend_properties(
            user_id=request.user_id,
            candidate_properties=property_features,
            top_k=len(property_features)
        )

        # Format response
        predictions = [
            {
                "property_index": idx,
                "score": score
            }
            for idx, score in recommendations
        ]

        return BatchPredictionResponse(
            user_id=request.user_id,
            predictions=predictions
        )
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
