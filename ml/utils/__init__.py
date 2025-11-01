"""
ML Utilities

Evaluation metrics, visualization, and helper functions.
"""

from ml.utils.evaluation import (
    compute_metrics,
    compute_ranking_metrics,
    evaluate_model,
    plot_training_curves,
    plot_confusion_matrix,
    plot_roc_curve,
    analyze_embeddings,
    compute_user_embedding_stats,
    find_similar_properties,
    generate_evaluation_report
)

__all__ = [
    'compute_metrics',
    'compute_ranking_metrics',
    'evaluate_model',
    'plot_training_curves',
    'plot_confusion_matrix',
    'plot_roc_curve',
    'analyze_embeddings',
    'compute_user_embedding_stats',
    'find_similar_properties',
    'generate_evaluation_report'
]
