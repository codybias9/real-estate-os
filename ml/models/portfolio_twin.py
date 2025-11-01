"""
Portfolio Twin - ML model that learns user's investment criteria

Learns from user behavior to predict property affinity:
- Properties viewed
- Deals created
- Outreach sent
- Explicit feedback (thumbs up/down)

Uses contrastive learning to create a user-specific embedding space.
Part of Wave 2.1 - Portfolio Twin training pipeline.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PropertyFeatures:
    """Structured property features for twin model"""

    # Financial
    listing_price: float
    price_per_sqft: float
    estimated_value: float
    cap_rate: Optional[float]
    cash_on_cash_return: Optional[float]

    # Physical
    bedrooms: int
    bathrooms: float
    square_footage: int
    lot_size_sqft: int
    year_built: int

    # Location
    lat: float
    lon: float
    zipcode: str

    # Market
    days_on_market: int
    listing_status: str

    # Condition
    condition_score: float  # 0-1
    renovation_needed: bool

    # Metadata
    property_type: str
    source_system: str
    confidence: float

    def to_vector(self) -> np.ndarray:
        """Convert to numerical feature vector"""
        # Normalize numerical features
        features = [
            self.listing_price / 1_000_000,  # Scale to 0-1 range for typical properties
            self.price_per_sqft / 500,
            self.estimated_value / 1_000_000 if self.estimated_value else 0,
            self.cap_rate if self.cap_rate else 0,
            self.cash_on_cash_return if self.cash_on_cash_return else 0,
            self.bedrooms / 10,  # Normalize
            self.bathrooms / 10,
            self.square_footage / 10_000,
            self.lot_size_sqft / 50_000,
            (2024 - self.year_built) / 100,  # Age in years
            self.lat / 90,  # Normalize lat/lon
            self.lon / 180,
            self.days_on_market / 365,
            self.condition_score,
            1.0 if self.renovation_needed else 0.0,
            self.confidence,
        ]

        # One-hot encode categorical
        # Property type
        type_categories = ['Single Family', 'Condo', 'Townhouse', 'Multi-Family', 'Land']
        type_encoding = [1.0 if self.property_type == cat else 0.0 for cat in type_categories]
        features.extend(type_encoding)

        # Listing status
        status_categories = ['Active', 'Pending', 'Sold', 'Off Market']
        status_encoding = [1.0 if self.listing_status == cat else 0.0 for cat in status_categories]
        features.extend(status_encoding)

        return np.array(features, dtype=np.float32)


class PortfolioTwinEncoder(nn.Module):
    """
    Neural network that encodes properties into embedding space

    Architecture:
    - Input: Property features (25-dim)
    - Hidden layers: 128 → 64 → 32
    - Output: Embedding (16-dim)
    """

    def __init__(self, input_dim: int = 25, embedding_dim: int = 16):
        super().__init__()

        self.input_dim = input_dim
        self.embedding_dim = embedding_dim

        # Encoder layers
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),

            nn.Linear(32, embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Encode property features to embedding

        Args:
            x: Property features (batch_size, input_dim)

        Returns:
            Embeddings (batch_size, embedding_dim)
        """
        return self.encoder(x)


class PortfolioTwin(nn.Module):
    """
    Portfolio Twin model for learning user preferences

    Uses contrastive learning:
    - Positive pairs: Properties user liked
    - Negative pairs: Properties user disliked or ignored
    - Anchor: User's portfolio embedding (learned)
    """

    def __init__(
        self,
        property_encoder: PortfolioTwinEncoder,
        num_users: int,
        embedding_dim: int = 16
    ):
        super().__init__()

        self.property_encoder = property_encoder
        self.embedding_dim = embedding_dim

        # Learn a portfolio embedding for each user
        self.user_embeddings = nn.Embedding(num_users, embedding_dim)

        # Initialize with small random values
        nn.init.normal_(self.user_embeddings.weight, mean=0.0, std=0.01)

    def forward(
        self,
        property_features: torch.Tensor,
        user_ids: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass

        Args:
            property_features: Property feature vectors (batch_size, input_dim)
            user_ids: User IDs (batch_size,)

        Returns:
            property_embeddings: Property embeddings (batch_size, embedding_dim)
            user_embeddings: User portfolio embeddings (batch_size, embedding_dim)
        """
        # Encode properties
        property_embeddings = self.property_encoder(property_features)

        # Get user portfolio embeddings
        user_embs = self.user_embeddings(user_ids)

        # L2 normalize
        property_embeddings = F.normalize(property_embeddings, p=2, dim=1)
        user_embs = F.normalize(user_embs, p=2, dim=1)

        return property_embeddings, user_embs

    def compute_affinity(
        self,
        property_embeddings: torch.Tensor,
        user_embeddings: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute affinity score between properties and user portfolio

        Args:
            property_embeddings: (batch_size, embedding_dim)
            user_embeddings: (batch_size, embedding_dim)

        Returns:
            Affinity scores (batch_size,)
        """
        # Cosine similarity
        affinity = torch.sum(property_embeddings * user_embeddings, dim=1)
        return affinity

    def predict_affinity(
        self,
        property_features: torch.Tensor,
        user_id: int
    ) -> torch.Tensor:
        """
        Predict user's affinity for properties

        Args:
            property_features: Property feature vectors (batch_size, input_dim)
            user_id: User ID

        Returns:
            Affinity scores (batch_size,) in range [0, 1]
        """
        user_ids = torch.full((property_features.size(0),), user_id, dtype=torch.long)

        with torch.no_grad():
            property_embs, user_embs = self.forward(property_features, user_ids)
            affinity = self.compute_affinity(property_embs, user_embs)

            # Map from [-1, 1] to [0, 1]
            affinity = (affinity + 1) / 2

        return affinity


def triplet_loss(
    anchor: torch.Tensor,
    positive: torch.Tensor,
    negative: torch.Tensor,
    margin: float = 0.5
) -> torch.Tensor:
    """
    Triplet loss for contrastive learning

    Encourages:
    - anchor close to positive
    - anchor far from negative
    - margin of separation

    Args:
        anchor: User portfolio embeddings (batch_size, embedding_dim)
        positive: Liked property embeddings (batch_size, embedding_dim)
        negative: Disliked property embeddings (batch_size, embedding_dim)
        margin: Minimum separation between positive and negative

    Returns:
        Loss scalar
    """
    # Cosine distance
    pos_distance = 1 - torch.sum(anchor * positive, dim=1)
    neg_distance = 1 - torch.sum(anchor * negative, dim=1)

    # Triplet loss
    loss = torch.relu(pos_distance - neg_distance + margin)

    return loss.mean()


def contrastive_loss(
    property_embeddings: torch.Tensor,
    user_embeddings: torch.Tensor,
    labels: torch.Tensor,
    temperature: float = 0.07
) -> torch.Tensor:
    """
    Contrastive loss (InfoNCE)

    Args:
        property_embeddings: (batch_size, embedding_dim)
        user_embeddings: (batch_size, embedding_dim)
        labels: Binary labels (batch_size,) - 1 for positive, 0 for negative
        temperature: Temperature parameter for softmax

    Returns:
        Loss scalar
    """
    # Compute similarities
    similarities = torch.sum(property_embeddings * user_embeddings, dim=1) / temperature

    # Binary cross-entropy
    loss = F.binary_cross_entropy_with_logits(similarities, labels.float())

    return loss


class PortfolioTwinTrainer:
    """
    Trainer for Portfolio Twin model

    Handles:
    - Data loading from user interactions
    - Training loop with contrastive loss
    - Model checkpointing
    - Evaluation metrics
    """

    def __init__(
        self,
        model: PortfolioTwin,
        learning_rate: float = 0.001,
        device: str = 'cpu'
    ):
        self.model = model.to(device)
        self.device = device
        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    def train_step(
        self,
        property_features: torch.Tensor,
        user_ids: torch.Tensor,
        labels: torch.Tensor
    ) -> float:
        """
        Single training step

        Args:
            property_features: (batch_size, input_dim)
            user_ids: (batch_size,)
            labels: (batch_size,) - 1 for liked, 0 for disliked

        Returns:
            Loss value
        """
        self.model.train()

        # Move to device
        property_features = property_features.to(self.device)
        user_ids = user_ids.to(self.device)
        labels = labels.to(self.device)

        # Forward pass
        property_embs, user_embs = self.model(property_features, user_ids)

        # Compute loss
        loss = contrastive_loss(property_embs, user_embs, labels)

        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss.item()

    def evaluate(
        self,
        property_features: torch.Tensor,
        user_ids: torch.Tensor,
        labels: torch.Tensor
    ) -> Dict[str, float]:
        """
        Evaluate model on validation set

        Args:
            property_features: (batch_size, input_dim)
            user_ids: (batch_size,)
            labels: (batch_size,)

        Returns:
            Metrics dict
        """
        self.model.eval()

        with torch.no_grad():
            property_features = property_features.to(self.device)
            user_ids = user_ids.to(self.device)
            labels = labels.to(self.device)

            # Predictions
            property_embs, user_embs = self.model(property_features, user_ids)
            affinity = self.model.compute_affinity(property_embs, user_embs)
            affinity = (affinity + 1) / 2  # Map to [0, 1]

            # Binary predictions
            predictions = (affinity > 0.5).float()

            # Metrics
            accuracy = (predictions == labels).float().mean().item()
            precision = ((predictions == 1) & (labels == 1)).sum().float() / (predictions == 1).sum().float()
            recall = ((predictions == 1) & (labels == 1)).sum().float() / (labels == 1).sum().float()
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            return {
                'accuracy': accuracy,
                'precision': precision.item() if torch.is_tensor(precision) else precision,
                'recall': recall.item() if torch.is_tensor(recall) else recall,
                'f1': f1.item() if torch.is_tensor(f1) else f1,
            }

    def save_checkpoint(self, path: str):
        """Save model checkpoint"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        }, path)

    def load_checkpoint(self, path: str):
        """Load model checkpoint"""
        checkpoint = torch.load(path)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
