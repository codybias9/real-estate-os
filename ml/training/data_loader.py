"""
Data Loader for Portfolio Twin Training

Loads user interaction data from database:
- Property views
- Deal creation
- Outreach sent
- Explicit feedback (thumbs up/down)

Creates training batches with positive/negative examples.
Part of Wave 2.1 - Portfolio Twin training pipeline.
"""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from db.models import Property, Deal, OwnerEntity, PropertyOwnerLink
from ml.models.portfolio_twin import PropertyFeatures


logger = logging.getLogger(__name__)


@dataclass
class UserInteraction:
    """User interaction with a property"""
    user_id: int
    property_id: str
    interaction_type: str  # 'view', 'deal', 'outreach', 'feedback'
    label: float  # 1.0 for positive, 0.0 for negative
    timestamp: datetime


class PropertyDataset(Dataset):
    """
    PyTorch Dataset for Portfolio Twin training

    Loads property features and user interactions from database.
    Returns (property_features, user_id, label) tuples.
    """

    def __init__(
        self,
        db_session: Session,
        tenant_id: str,
        user_ids: Optional[List[int]] = None,
        lookback_days: int = 90
    ):
        """
        Initialize dataset

        Args:
            db_session: Database session
            tenant_id: Tenant ID for RLS context
            user_ids: Optional list of user IDs to filter by
            lookback_days: How far back to look for interactions
        """
        self.db_session = db_session
        self.tenant_id = tenant_id
        self.user_ids = user_ids
        self.lookback_days = lookback_days

        # Set RLS context
        self.db_session.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")

        # Load data
        self.interactions = self._load_interactions()
        self.property_features = self._load_property_features()

        logger.info(f"Loaded {len(self.interactions)} interactions for {len(self.property_features)} properties")

    def _load_interactions(self) -> List[UserInteraction]:
        """Load user interactions from database"""
        interactions = []
        cutoff_date = datetime.utcnow() - timedelta(days=self.lookback_days)

        # 1. Load deals (positive signal)
        deals_query = self.db_session.query(Deal).filter(
            Deal.created_at >= cutoff_date
        )
        if self.user_ids:
            deals_query = deals_query.filter(Deal.user_id.in_(self.user_ids))

        for deal in deals_query.all():
            interactions.append(UserInteraction(
                user_id=deal.user_id,
                property_id=str(deal.property_id),
                interaction_type='deal',
                label=1.0,  # Creating a deal is strong positive signal
                timestamp=deal.created_at
            ))

        # 2. Load property views (weak positive signal)
        # TODO: Add PropertyView tracking table in future wave
        # For now, we'll just use deals and explicit feedback

        # 3. Load explicit feedback (if available)
        # TODO: Add UserFeedback table in future wave

        return interactions

    def _load_property_features(self) -> Dict[str, PropertyFeatures]:
        """Load property features from database"""
        features = {}

        # Get unique property IDs from interactions
        property_ids = list(set(i.property_id for i in self.interactions))

        # Load properties
        properties = self.db_session.query(Property).filter(
            Property.id.in_(property_ids)
        ).all()

        for prop in properties:
            try:
                features[str(prop.id)] = self._extract_features(prop)
            except Exception as e:
                logger.warning(f"Failed to extract features for property {prop.id}: {e}")
                continue

        return features

    def _extract_features(self, property: Property) -> PropertyFeatures:
        """Extract PropertyFeatures from Property model"""
        # Parse canonical address
        address = property.canonical_address or {}

        # Get financial data
        listing_price = property.listing_price or 0.0
        estimated_value = property.estimated_value or listing_price
        square_footage = property.square_footage or 1500  # Default if missing

        # Calculate derived features
        price_per_sqft = listing_price / square_footage if square_footage > 0 else 0

        # Cap rate and cash-on-cash (may be None)
        cap_rate = getattr(property, 'cap_rate', None)
        cash_on_cash = getattr(property, 'cash_on_cash_return', None)

        # Get provenance confidence (average across all fields)
        confidence = self._get_average_confidence(property)

        return PropertyFeatures(
            listing_price=float(listing_price),
            price_per_sqft=float(price_per_sqft),
            estimated_value=float(estimated_value),
            cap_rate=float(cap_rate) if cap_rate else None,
            cash_on_cash_return=float(cash_on_cash) if cash_on_cash else None,
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

    def _get_average_confidence(self, property: Property) -> float:
        """Calculate average provenance confidence across all fields"""
        # Get all provenance records for this property
        from db.models import FieldProvenance

        provenances = self.db_session.query(FieldProvenance).filter(
            FieldProvenance.entity_id == property.id,
            FieldProvenance.entity_type == 'property'
        ).all()

        if not provenances:
            return 0.5  # Default confidence

        confidences = [p.confidence for p in provenances if p.confidence is not None]
        return sum(confidences) / len(confidences) if confidences else 0.5

    def __len__(self) -> int:
        return len(self.interactions)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, float]:
        """
        Get a training example

        Returns:
            property_features: Tensor of shape (feature_dim,)
            user_id: Integer user ID
            label: Float label (0.0 or 1.0)
        """
        interaction = self.interactions[idx]

        # Get property features
        if interaction.property_id not in self.property_features:
            # Property features not available, return zeros
            features = torch.zeros(25, dtype=torch.float32)
        else:
            prop_features = self.property_features[interaction.property_id]
            features = torch.from_numpy(prop_features.to_vector())

        return features, interaction.user_id, interaction.label


class ContrastiveDataLoader:
    """
    Data loader for contrastive learning

    Creates batches with balanced positive/negative examples.
    Each batch contains equal numbers of liked and disliked properties.
    """

    def __init__(
        self,
        dataset: PropertyDataset,
        batch_size: int = 32,
        shuffle: bool = True
    ):
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle

        # Split interactions by label
        self.positive_indices = [
            i for i, interaction in enumerate(dataset.interactions)
            if interaction.label == 1.0
        ]
        self.negative_indices = [
            i for i, interaction in enumerate(dataset.interactions)
            if interaction.label == 0.0
        ]

        logger.info(f"Dataset split: {len(self.positive_indices)} positive, {len(self.negative_indices)} negative")

    def __iter__(self):
        """Iterate over balanced batches"""
        # Shuffle if requested
        if self.shuffle:
            np.random.shuffle(self.positive_indices)
            np.random.shuffle(self.negative_indices)

        # Create balanced batches
        half_batch = self.batch_size // 2

        # Determine number of batches
        num_batches = min(
            len(self.positive_indices) // half_batch,
            len(self.negative_indices) // half_batch
        )

        for i in range(num_batches):
            # Get positive and negative examples
            pos_batch = self.positive_indices[i * half_batch:(i + 1) * half_batch]
            neg_batch = self.negative_indices[i * half_batch:(i + 1) * half_batch]

            # Combine and load
            batch_indices = pos_batch + neg_batch

            # Load batch
            features_list = []
            user_ids_list = []
            labels_list = []

            for idx in batch_indices:
                features, user_id, label = self.dataset[idx]
                features_list.append(features)
                user_ids_list.append(user_id)
                labels_list.append(label)

            # Stack into tensors
            batch_features = torch.stack(features_list)
            batch_user_ids = torch.tensor(user_ids_list, dtype=torch.long)
            batch_labels = torch.tensor(labels_list, dtype=torch.float32)

            yield batch_features, batch_user_ids, batch_labels


def create_data_loaders(
    db_session: Session,
    tenant_id: str,
    train_user_ids: List[int],
    val_user_ids: List[int],
    batch_size: int = 32,
    lookback_days: int = 90
) -> Tuple[ContrastiveDataLoader, ContrastiveDataLoader]:
    """
    Create train and validation data loaders

    Args:
        db_session: Database session
        tenant_id: Tenant ID
        train_user_ids: User IDs for training set
        val_user_ids: User IDs for validation set
        batch_size: Batch size
        lookback_days: How far back to look for interactions

    Returns:
        (train_loader, val_loader)
    """
    # Create datasets
    train_dataset = PropertyDataset(
        db_session=db_session,
        tenant_id=tenant_id,
        user_ids=train_user_ids,
        lookback_days=lookback_days
    )

    val_dataset = PropertyDataset(
        db_session=db_session,
        tenant_id=tenant_id,
        user_ids=val_user_ids,
        lookback_days=lookback_days
    )

    # Create loaders
    train_loader = ContrastiveDataLoader(
        dataset=train_dataset,
        batch_size=batch_size,
        shuffle=True
    )

    val_loader = ContrastiveDataLoader(
        dataset=val_dataset,
        batch_size=batch_size,
        shuffle=False
    )

    return train_loader, val_loader


def create_negative_samples(
    db_session: Session,
    tenant_id: str,
    num_samples: int = 1000
) -> List[UserInteraction]:
    """
    Create negative samples from properties user hasn't interacted with

    Args:
        db_session: Database session
        tenant_id: Tenant ID
        num_samples: Number of negative samples to create

    Returns:
        List of negative UserInteraction objects
    """
    # Set RLS context
    db_session.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")

    # Get all properties
    all_properties = db_session.query(Property.id).all()
    property_ids = [str(p.id) for p in all_properties]

    # Get properties with deals (positive interactions)
    properties_with_deals = db_session.query(Deal.property_id).distinct().all()
    positive_property_ids = set(str(p.property_id) for p in properties_with_deals)

    # Find properties without deals (potential negatives)
    negative_property_ids = [p for p in property_ids if p not in positive_property_ids]

    # Sample random negatives
    if len(negative_property_ids) > num_samples:
        negative_property_ids = np.random.choice(
            negative_property_ids,
            size=num_samples,
            replace=False
        ).tolist()

    # Create UserInteraction objects
    # For now, assign to user_id=1 (default user)
    # In production, sample based on user distribution
    negative_interactions = []
    for prop_id in negative_property_ids:
        negative_interactions.append(UserInteraction(
            user_id=1,  # TODO: Sample from actual user distribution
            property_id=prop_id,
            interaction_type='negative_sample',
            label=0.0,
            timestamp=datetime.utcnow()
        ))

    logger.info(f"Created {len(negative_interactions)} negative samples")
    return negative_interactions
