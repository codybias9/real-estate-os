"""Property Encoder for Vector Search
Supervised metric learning to encode properties into embeddings

Uses triplet loss on won/passed/other properties to learn
embeddings where similar properties are close together.

Training data format:
- Anchor: Won property
- Positive: Other won properties with similar characteristics
- Negative: Passed properties
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Tuple
import pickle
from dataclasses import dataclass


@dataclass
class PropertyFeatures:
    """Property features for encoding"""
    property_id: str
    sqft: float
    lot_size: float
    year_built: int
    bedrooms: int
    bathrooms: float
    list_price: float
    price_per_sqft: float
    days_on_market: int
    cap_rate: float
    latitude: float
    longitude: float
    condition_score: float
    flood_risk: float
    wildfire_risk: float
    walk_score: int
    # ... add more as needed


class TripletDataset(Dataset):
    """Dataset for triplet loss training"""

    def __init__(self, triplets: List[Tuple[PropertyFeatures, PropertyFeatures, PropertyFeatures]]):
        self.triplets = triplets

    def __len__(self):
        return len(self.triplets)

    def __getitem__(self, idx):
        anchor, positive, negative = self.triplets[idx]

        # Convert to tensors
        anchor_tensor = self._features_to_tensor(anchor)
        positive_tensor = self._features_to_tensor(positive)
        negative_tensor = self._features_to_tensor(negative)

        return anchor_tensor, positive_tensor, negative_tensor

    def _features_to_tensor(self, features: PropertyFeatures) -> torch.Tensor:
        """Convert property features to tensor"""
        return torch.tensor([
            features.sqft / 5000.0,  # Normalize
            features.lot_size / 20000.0,
            (features.year_built - 1900) / 125.0,
            features.bedrooms / 6.0,
            features.bathrooms / 5.0,
            features.list_price / 1000000.0,
            features.price_per_sqft / 500.0,
            features.days_on_market / 365.0,
            features.cap_rate,
            (features.latitude - 36.0) / 10.0,  # Rough normalization
            (features.longitude + 115.0) / 50.0,
            features.condition_score / 10.0,
            features.flood_risk,
            features.wildfire_risk,
            features.walk_score / 100.0
        ], dtype=torch.float32)


class PropertyEncoder(nn.Module):
    """Neural network encoder for properties

    Architecture:
    - Input: 15 features
    - Hidden: 128 -> 64
    - Output: 128-dimensional embedding
    """

    def __init__(self, input_dim: int = 15, hidden_dim: int = 128, embedding_dim: int = 128):
        super(PropertyEncoder, self).__init__()

        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.bn2 = nn.BatchNorm1d(hidden_dim // 2)
        self.fc3 = nn.Linear(hidden_dim // 2, embedding_dim)

    def forward(self, x):
        # Layer 1
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)

        # Layer 2
        x = self.fc2(x)
        x = self.bn2(x)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)

        # Output (L2 normalized)
        x = self.fc3(x)
        x = F.normalize(x, p=2, dim=1)  # Unit sphere

        return x


class TripletLoss(nn.Module):
    """Triplet loss for metric learning

    Loss = max(0, ||a - p||^2 - ||a - n||^2 + margin)

    where:
    - a = anchor embedding
    - p = positive embedding (similar property)
    - n = negative embedding (dissimilar property)
    - margin = minimum distance difference
    """

    def __init__(self, margin: float = 1.0):
        super(TripletLoss, self).__init__()
        self.margin = margin

    def forward(self, anchor, positive, negative):
        # Euclidean distance
        pos_dist = F.pairwise_distance(anchor, positive, p=2)
        neg_dist = F.pairwise_distance(anchor, negative, p=2)

        # Triplet loss
        losses = F.relu(pos_dist - neg_dist + self.margin)

        return losses.mean()


class PropertyEncoderTrainer:
    """Trainer for property encoder"""

    def __init__(self, model: PropertyEncoder, device: str = "cpu"):
        self.model = model.to(device)
        self.device = device
        self.criterion = TripletLoss(margin=1.0)
        self.optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    def train_epoch(self, dataloader: DataLoader) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0

        for batch_idx, (anchor, positive, negative) in enumerate(dataloader):
            # Move to device
            anchor = anchor.to(self.device)
            positive = positive.to(self.device)
            negative = negative.to(self.device)

            # Forward pass
            anchor_emb = self.model(anchor)
            positive_emb = self.model(positive)
            negative_emb = self.model(negative)

            # Calculate loss
            loss = self.criterion(anchor_emb, positive_emb, negative_emb)

            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        return total_loss / len(dataloader)

    def evaluate(self, dataloader: DataLoader) -> float:
        """Evaluate on validation set"""
        self.model.eval()
        total_loss = 0.0

        with torch.no_grad():
            for anchor, positive, negative in dataloader:
                anchor = anchor.to(self.device)
                positive = positive.to(self.device)
                negative = negative.to(self.device)

                anchor_emb = self.model(anchor)
                positive_emb = self.model(positive)
                negative_emb = self.model(negative)

                loss = self.criterion(anchor_emb, positive_emb, negative_emb)
                total_loss += loss.item()

        return total_loss / len(dataloader)

    def save(self, path: str):
        """Save model checkpoint"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict()
        }, path)

    def load(self, path: str):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])


# ============================================================================
# Inference
# ============================================================================

class PropertyEmbedder:
    """Production encoder for generating embeddings"""

    def __init__(self, model_path: str, device: str = "cpu"):
        self.device = device
        self.model = PropertyEncoder().to(device)
        self.model.load_state_dict(torch.load(model_path, map_location=device)['model_state_dict'])
        self.model.eval()

    def encode(self, features: Dict) -> np.ndarray:
        """Encode property to embedding vector

        Args:
            features: Dict with property features

        Returns:
            128-dimensional embedding vector
        """
        # Convert dict to tensor
        tensor = torch.tensor([
            features.get("sqft", 0) / 5000.0,
            features.get("lot_size", 0) / 20000.0,
            (features.get("year_built", 2000) - 1900) / 125.0,
            features.get("bedrooms", 0) / 6.0,
            features.get("bathrooms", 0) / 5.0,
            features.get("list_price", 0) / 1000000.0,
            features.get("price_per_sqft", 0) / 500.0,
            features.get("days_on_market", 0) / 365.0,
            features.get("cap_rate", 0),
            (features.get("latitude", 36.0) - 36.0) / 10.0,
            (features.get("longitude", -115.0) + 115.0) / 50.0,
            features.get("condition_score", 5.0) / 10.0,
            features.get("flood_risk", 0),
            features.get("wildfire_risk", 0),
            features.get("walk_score", 0) / 100.0
        ], dtype=torch.float32).unsqueeze(0).to(self.device)

        # Generate embedding
        with torch.no_grad():
            embedding = self.model(tensor)

        return embedding.cpu().numpy()[0]

    def encode_batch(self, features_list: List[Dict]) -> np.ndarray:
        """Encode batch of properties"""
        embeddings = []
        for features in features_list:
            embeddings.append(self.encode(features))
        return np.array(embeddings)


# ============================================================================
# Fallback: Autoencoder (if no training data for triplets)
# ============================================================================

class PropertyAutoencoder(nn.Module):
    """Autoencoder fallback if insufficient training data"""

    def __init__(self, input_dim: int = 15, encoding_dim: int = 128):
        super(PropertyAutoencoder, self).__init__()

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, encoding_dim),
            nn.Tanh()
        )

        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(encoding_dim, 128),
            nn.ReLU(),
            nn.Linear(128, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return encoded, decoded

    def encode(self, x):
        return self.encoder(x)
