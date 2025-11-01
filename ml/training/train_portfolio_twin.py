"""
Portfolio Twin Training Script

Trains the Portfolio Twin model on user interaction data.

Usage:
    python ml/training/train_portfolio_twin.py --tenant-id <uuid> --epochs 100

Part of Wave 2.1 - Portfolio Twin training pipeline.
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Dict, List
import torch
import torch.nn as nn
from datetime import datetime
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ml.models.portfolio_twin import (
    PortfolioTwinEncoder,
    PortfolioTwin,
    PortfolioTwinTrainer,
    contrastive_loss
)
from ml.training.data_loader import create_data_loaders, create_negative_samples
from ml.utils.evaluation import evaluate_model, plot_training_curves


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Train Portfolio Twin model')

    # Data
    parser.add_argument('--tenant-id', type=str, required=True,
                        help='Tenant ID for RLS context')
    parser.add_argument('--lookback-days', type=int, default=90,
                        help='How far back to look for user interactions')

    # Model
    parser.add_argument('--embedding-dim', type=int, default=16,
                        help='Embedding dimension')
    parser.add_argument('--input-dim', type=int, default=25,
                        help='Input feature dimension')

    # Training
    parser.add_argument('--epochs', type=int, default=100,
                        help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Batch size')
    parser.add_argument('--learning-rate', type=float, default=0.001,
                        help='Learning rate')
    parser.add_argument('--device', type=str, default='cpu',
                        choices=['cpu', 'cuda', 'mps'],
                        help='Device to train on')

    # Validation
    parser.add_argument('--val-split', type=float, default=0.2,
                        help='Validation split ratio')

    # Output
    parser.add_argument('--output-dir', type=str, default='ml/checkpoints',
                        help='Directory to save model checkpoints')
    parser.add_argument('--save-every', type=int, default=10,
                        help='Save checkpoint every N epochs')

    # Database
    parser.add_argument('--db-url', type=str,
                        default=os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/realestate'),
                        help='Database URL')

    return parser.parse_args()


def setup_database(db_url: str):
    """Setup database connection"""
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def split_users_train_val(all_user_ids: List[int], val_split: float):
    """Split user IDs into train and validation sets"""
    num_val = int(len(all_user_ids) * val_split)
    val_user_ids = all_user_ids[:num_val]
    train_user_ids = all_user_ids[num_val:]
    return train_user_ids, val_user_ids


def train_epoch(
    trainer: PortfolioTwinTrainer,
    train_loader,
    epoch: int
) -> Dict[str, float]:
    """Train for one epoch"""
    total_loss = 0.0
    num_batches = 0

    for batch_features, batch_user_ids, batch_labels in train_loader:
        loss = trainer.train_step(batch_features, batch_user_ids, batch_labels)
        total_loss += loss
        num_batches += 1

    avg_loss = total_loss / num_batches if num_batches > 0 else 0.0

    logger.info(f"Epoch {epoch}: train_loss={avg_loss:.4f}")

    return {
        'epoch': epoch,
        'train_loss': avg_loss
    }


def validate(
    trainer: PortfolioTwinTrainer,
    val_loader,
    epoch: int
) -> Dict[str, float]:
    """Validate model"""
    all_features = []
    all_user_ids = []
    all_labels = []

    # Collect all validation data
    for batch_features, batch_user_ids, batch_labels in val_loader:
        all_features.append(batch_features)
        all_user_ids.append(batch_user_ids)
        all_labels.append(batch_labels)

    if not all_features:
        logger.warning("No validation data available")
        return {}

    # Stack
    features = torch.cat(all_features, dim=0)
    user_ids = torch.cat(all_user_ids, dim=0)
    labels = torch.cat(all_labels, dim=0)

    # Evaluate
    metrics = trainer.evaluate(features, user_ids, labels)

    logger.info(
        f"Epoch {epoch}: val_accuracy={metrics['accuracy']:.4f}, "
        f"val_precision={metrics['precision']:.4f}, "
        f"val_recall={metrics['recall']:.4f}, "
        f"val_f1={metrics['f1']:.4f}"
    )

    return metrics


def main():
    """Main training loop"""
    args = parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup database
    logger.info(f"Connecting to database: {args.db_url}")
    db_session = setup_database(args.db_url)

    # Set tenant context
    db_session.execute(f"SET LOCAL app.current_tenant_id = '{args.tenant_id}'")

    # Get all user IDs
    # TODO: Load from User table when available
    # For now, hardcode some test users
    all_user_ids = [1, 2, 3, 4, 5]  # Placeholder

    # Split train/val
    train_user_ids, val_user_ids = split_users_train_val(all_user_ids, args.val_split)
    logger.info(f"Train users: {len(train_user_ids)}, Val users: {len(val_user_ids)}")

    # Create negative samples
    logger.info("Creating negative samples...")
    negative_samples = create_negative_samples(
        db_session=db_session,
        tenant_id=args.tenant_id,
        num_samples=1000
    )

    # Create data loaders
    logger.info("Creating data loaders...")
    train_loader, val_loader = create_data_loaders(
        db_session=db_session,
        tenant_id=args.tenant_id,
        train_user_ids=train_user_ids,
        val_user_ids=val_user_ids,
        batch_size=args.batch_size,
        lookback_days=args.lookback_days
    )

    # Create model
    logger.info("Creating model...")
    encoder = PortfolioTwinEncoder(
        input_dim=args.input_dim,
        embedding_dim=args.embedding_dim
    )

    model = PortfolioTwin(
        property_encoder=encoder,
        num_users=len(all_user_ids),
        embedding_dim=args.embedding_dim
    )

    # Create trainer
    device = torch.device(args.device)
    trainer = PortfolioTwinTrainer(
        model=model,
        learning_rate=args.learning_rate,
        device=str(device)
    )

    logger.info(f"Training on device: {device}")
    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Training loop
    training_history = []
    best_f1 = 0.0

    for epoch in range(1, args.epochs + 1):
        # Train
        train_metrics = train_epoch(trainer, train_loader, epoch)

        # Validate
        val_metrics = validate(trainer, val_loader, epoch)

        # Combine metrics
        metrics = {**train_metrics, **val_metrics}
        training_history.append(metrics)

        # Save checkpoint
        if epoch % args.save_every == 0 or epoch == args.epochs:
            checkpoint_path = output_dir / f"portfolio_twin_epoch_{epoch}.pt"
            trainer.save_checkpoint(str(checkpoint_path))
            logger.info(f"Saved checkpoint: {checkpoint_path}")

            # Save as latest
            latest_path = output_dir / "portfolio_twin_latest.pt"
            trainer.save_checkpoint(str(latest_path))

        # Save best model
        if val_metrics and val_metrics.get('f1', 0.0) > best_f1:
            best_f1 = val_metrics['f1']
            best_path = output_dir / "portfolio_twin_best.pt"
            trainer.save_checkpoint(str(best_path))
            logger.info(f"New best model! F1={best_f1:.4f}")

    # Save training history
    history_path = output_dir / "training_history.json"
    with open(history_path, 'w') as f:
        json.dump(training_history, f, indent=2)
    logger.info(f"Saved training history: {history_path}")

    # Plot training curves
    try:
        plot_path = output_dir / "training_curves.png"
        plot_training_curves(training_history, str(plot_path))
        logger.info(f"Saved training curves: {plot_path}")
    except Exception as e:
        logger.warning(f"Failed to plot training curves: {e}")

    # Final evaluation
    logger.info("\n" + "="*50)
    logger.info("TRAINING COMPLETE")
    logger.info("="*50)
    logger.info(f"Best F1 score: {best_f1:.4f}")
    logger.info(f"Model saved to: {output_dir}")

    db_session.close()


if __name__ == '__main__':
    main()
