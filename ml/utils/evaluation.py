"""
Evaluation Utilities for Portfolio Twin

Metrics, visualization, and analysis tools for model evaluation.
Part of Wave 2.1 - Portfolio Twin training pipeline.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple
import torch
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    roc_curve
)
import logging

logger = logging.getLogger(__name__)


def compute_metrics(
    predictions: np.ndarray,
    labels: np.ndarray,
    scores: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    Compute evaluation metrics

    Args:
        predictions: Binary predictions (0 or 1)
        labels: Ground truth labels (0 or 1)
        scores: Optional prediction scores for AUC

    Returns:
        Dictionary of metrics
    """
    metrics = {
        'accuracy': accuracy_score(labels, predictions),
        'precision': precision_score(labels, predictions, zero_division=0),
        'recall': recall_score(labels, predictions, zero_division=0),
        'f1': f1_score(labels, predictions, zero_division=0),
    }

    # Add AUC if scores provided
    if scores is not None:
        try:
            metrics['auc'] = roc_auc_score(labels, scores)
        except ValueError:
            # Not enough positive/negative samples
            metrics['auc'] = 0.0

    return metrics


def compute_ranking_metrics(
    scores: np.ndarray,
    labels: np.ndarray,
    k_values: List[int] = [5, 10, 20]
) -> Dict[str, float]:
    """
    Compute ranking metrics (Precision@K, Recall@K, NDCG@K)

    Args:
        scores: Prediction scores (higher = more likely positive)
        labels: Ground truth labels (0 or 1)
        k_values: List of K values to compute metrics for

    Returns:
        Dictionary of ranking metrics
    """
    metrics = {}

    # Sort by scores descending
    sorted_indices = np.argsort(-scores)
    sorted_labels = labels[sorted_indices]

    for k in k_values:
        if k > len(sorted_labels):
            continue

        # Top K predictions
        top_k_labels = sorted_labels[:k]

        # Precision@K
        precision_at_k = np.sum(top_k_labels) / k
        metrics[f'precision@{k}'] = precision_at_k

        # Recall@K
        total_positives = np.sum(labels)
        if total_positives > 0:
            recall_at_k = np.sum(top_k_labels) / total_positives
            metrics[f'recall@{k}'] = recall_at_k
        else:
            metrics[f'recall@{k}'] = 0.0

        # NDCG@K
        dcg = np.sum(top_k_labels / np.log2(np.arange(2, k + 2)))
        ideal_labels = np.sort(labels)[::-1][:k]
        idcg = np.sum(ideal_labels / np.log2(np.arange(2, k + 2)))
        ndcg_at_k = dcg / idcg if idcg > 0 else 0.0
        metrics[f'ndcg@{k}'] = ndcg_at_k

    return metrics


def evaluate_model(
    model,
    dataloader,
    device: str = 'cpu'
) -> Dict[str, float]:
    """
    Evaluate model on a dataset

    Args:
        model: Portfolio Twin model
        dataloader: Data loader
        device: Device to run on

    Returns:
        Dictionary of metrics
    """
    model.eval()

    all_predictions = []
    all_labels = []
    all_scores = []

    with torch.no_grad():
        for batch_features, batch_user_ids, batch_labels in dataloader:
            # Move to device
            batch_features = batch_features.to(device)
            batch_user_ids = batch_user_ids.to(device)

            # Get predictions
            property_embs, user_embs = model(batch_features, batch_user_ids)
            affinity = model.compute_affinity(property_embs, user_embs)

            # Map to [0, 1]
            scores = (affinity + 1) / 2

            # Binary predictions
            predictions = (scores > 0.5).float()

            # Collect
            all_predictions.extend(predictions.cpu().numpy())
            all_labels.extend(batch_labels.cpu().numpy())
            all_scores.extend(scores.cpu().numpy())

    # Convert to arrays
    predictions = np.array(all_predictions)
    labels = np.array(all_labels)
    scores = np.array(all_scores)

    # Compute classification metrics
    class_metrics = compute_metrics(predictions, labels, scores)

    # Compute ranking metrics
    ranking_metrics = compute_ranking_metrics(scores, labels)

    # Combine
    return {**class_metrics, **ranking_metrics}


def plot_training_curves(
    training_history: List[Dict[str, float]],
    output_path: str
):
    """
    Plot training curves

    Args:
        training_history: List of metric dictionaries per epoch
        output_path: Path to save plot
    """
    # Extract metrics
    epochs = [h['epoch'] for h in training_history]
    train_losses = [h.get('train_loss', 0) for h in training_history]
    val_accuracies = [h.get('accuracy', 0) for h in training_history if 'accuracy' in h]
    val_f1s = [h.get('f1', 0) for h in training_history if 'f1' in h]

    # Create figure
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # Plot 1: Training Loss
    axes[0].plot(epochs, train_losses, marker='o', label='Train Loss')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].set_title('Training Loss')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Validation Accuracy
    if val_accuracies:
        val_epochs = [h['epoch'] for h in training_history if 'accuracy' in h]
        axes[1].plot(val_epochs, val_accuracies, marker='o', color='green', label='Val Accuracy')
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Accuracy')
        axes[1].set_title('Validation Accuracy')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

    # Plot 3: Validation F1
    if val_f1s:
        val_epochs = [h['epoch'] for h in training_history if 'f1' in h]
        axes[2].plot(val_epochs, val_f1s, marker='o', color='blue', label='Val F1')
        axes[2].set_xlabel('Epoch')
        axes[2].set_ylabel('F1 Score')
        axes[2].set_title('Validation F1 Score')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved training curves to {output_path}")


def plot_confusion_matrix(
    predictions: np.ndarray,
    labels: np.ndarray,
    output_path: str
):
    """
    Plot confusion matrix

    Args:
        predictions: Binary predictions
        labels: Ground truth labels
        output_path: Path to save plot
    """
    cm = confusion_matrix(labels, predictions)

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)

    # Labels
    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=['Negative', 'Positive'],
        yticklabels=['Negative', 'Positive'],
        ylabel='True label',
        xlabel='Predicted label',
        title='Confusion Matrix'
    )

    # Text annotations
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved confusion matrix to {output_path}")


def plot_roc_curve(
    scores: np.ndarray,
    labels: np.ndarray,
    output_path: str
):
    """
    Plot ROC curve

    Args:
        scores: Prediction scores
        labels: Ground truth labels
        output_path: Path to save plot
    """
    fpr, tpr, thresholds = roc_curve(labels, scores)
    auc = roc_auc_score(labels, scores)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fpr, tpr, color='blue', lw=2, label=f'ROC curve (AUC = {auc:.2f})')
    ax.plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--', label='Random')

    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curve')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved ROC curve to {output_path}")


def analyze_embeddings(
    model,
    property_features: torch.Tensor,
    property_ids: List[str],
    output_path: str
):
    """
    Visualize property embeddings using t-SNE

    Args:
        model: Portfolio Twin model
        property_features: Property feature tensors
        property_ids: Property IDs
        output_path: Path to save plot
    """
    from sklearn.manifold import TSNE

    model.eval()

    with torch.no_grad():
        # Get embeddings
        embeddings = model.property_encoder(property_features)
        embeddings = embeddings.cpu().numpy()

    # Apply t-SNE
    tsne = TSNE(n_components=2, random_state=42, perplexity=30)
    embeddings_2d = tsne.fit_transform(embeddings)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 8))
    scatter = ax.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], alpha=0.6, s=50)

    ax.set_xlabel('t-SNE Dimension 1')
    ax.set_ylabel('t-SNE Dimension 2')
    ax.set_title('Property Embedding Space (t-SNE)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved embedding visualization to {output_path}")


def compute_user_embedding_stats(
    model,
    user_ids: List[int]
) -> Dict[str, float]:
    """
    Compute statistics about user embeddings

    Args:
        model: Portfolio Twin model
        user_ids: List of user IDs

    Returns:
        Dictionary of statistics
    """
    model.eval()

    with torch.no_grad():
        user_ids_tensor = torch.tensor(user_ids, dtype=torch.long)
        user_embeddings = model.user_embeddings(user_ids_tensor)
        user_embeddings = user_embeddings.cpu().numpy()

    # Compute stats
    stats = {
        'mean_norm': np.mean(np.linalg.norm(user_embeddings, axis=1)),
        'std_norm': np.std(np.linalg.norm(user_embeddings, axis=1)),
        'min_norm': np.min(np.linalg.norm(user_embeddings, axis=1)),
        'max_norm': np.max(np.linalg.norm(user_embeddings, axis=1)),
    }

    # Compute pairwise similarities
    similarities = user_embeddings @ user_embeddings.T
    # Remove diagonal (self-similarities)
    mask = ~np.eye(similarities.shape[0], dtype=bool)
    off_diagonal_sims = similarities[mask]

    stats['mean_similarity'] = np.mean(off_diagonal_sims)
    stats['std_similarity'] = np.std(off_diagonal_sims)

    return stats


def find_similar_properties(
    model,
    query_property_features: torch.Tensor,
    candidate_property_features: torch.Tensor,
    candidate_property_ids: List[str],
    top_k: int = 10
) -> List[Tuple[str, float]]:
    """
    Find properties most similar to query property

    Args:
        model: Portfolio Twin model
        query_property_features: Query property features (1, input_dim)
        candidate_property_features: Candidate property features (N, input_dim)
        candidate_property_ids: Candidate property IDs
        top_k: Number of results to return

    Returns:
        List of (property_id, similarity) tuples
    """
    model.eval()

    with torch.no_grad():
        # Encode query
        query_embedding = model.property_encoder(query_property_features)
        query_embedding = query_embedding / torch.norm(query_embedding)

        # Encode candidates
        candidate_embeddings = model.property_encoder(candidate_property_features)
        candidate_embeddings = candidate_embeddings / torch.norm(candidate_embeddings, dim=1, keepdim=True)

        # Compute similarities
        similarities = (candidate_embeddings @ query_embedding.T).squeeze()
        similarities = similarities.cpu().numpy()

    # Get top K
    top_indices = np.argsort(-similarities)[:top_k]

    results = [
        (candidate_property_ids[i], float(similarities[i]))
        for i in top_indices
    ]

    return results


def generate_evaluation_report(
    model,
    train_loader,
    val_loader,
    output_dir: str,
    device: str = 'cpu'
):
    """
    Generate comprehensive evaluation report

    Args:
        model: Portfolio Twin model
        train_loader: Training data loader
        val_loader: Validation data loader
        output_dir: Directory to save outputs
        device: Device to run on
    """
    import os
    from pathlib import Path

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Generating evaluation report...")

    # Evaluate on train and val sets
    logger.info("Evaluating on training set...")
    train_metrics = evaluate_model(model, train_loader, device)

    logger.info("Evaluating on validation set...")
    val_metrics = evaluate_model(model, val_loader, device)

    # Print metrics
    logger.info("\n" + "="*50)
    logger.info("EVALUATION RESULTS")
    logger.info("="*50)

    logger.info("\nTraining Set:")
    for metric, value in train_metrics.items():
        logger.info(f"  {metric}: {value:.4f}")

    logger.info("\nValidation Set:")
    for metric, value in val_metrics.items():
        logger.info(f"  {metric}: {value:.4f}")

    # Save metrics to file
    import json
    metrics_path = output_dir / "evaluation_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump({
            'train': train_metrics,
            'val': val_metrics
        }, f, indent=2)
    logger.info(f"\nSaved metrics to {metrics_path}")

    logger.info("\nEvaluation report complete!")
