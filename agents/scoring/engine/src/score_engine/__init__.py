"""
Score.Engine - Deterministic property scoring with explainability
Emits: event.score.created
"""

from .engine import ScoreEngine, ScoringResult

__all__ = ["ScoreEngine", "ScoringResult"]
