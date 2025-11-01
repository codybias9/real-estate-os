"""Multi-Armed Bandits for Outreach Optimization
Thompson Sampling and contextual bandits for send-time and message selection

Applications:
- Send-time optimization (which hour of day gets best response?)
- Message template selection (which template performs best?)
- Sequence selection (which followup sequence converts best?)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class BanditArm(Enum):
    """Bandit arm types"""
    SEND_TIME = "send_time"
    TEMPLATE = "template"
    SEQUENCE = "sequence"


@dataclass
class BetaDistribution:
    """Beta distribution for Bayesian bandit"""
    alpha: float = 1.0  # Successes + 1
    beta: float = 1.0  # Failures + 1

    def sample(self) -> float:
        """Sample from Beta distribution"""
        return np.random.beta(self.alpha, self.beta)

    def mean(self) -> float:
        """Expected value (mean)"""
        return self.alpha / (self.alpha + self.beta)

    def confidence_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval

        Args:
            confidence: Confidence level (default 0.95)

        Returns:
            Tuple of (lower, upper)
        """
        lower = stats.beta.ppf((1 - confidence) / 2, self.alpha, self.beta)
        upper = stats.beta.ppf((1 + confidence) / 2, self.alpha, self.beta)
        return (lower, upper)


@dataclass
class ArmStats:
    """Statistics for a bandit arm"""
    arm_id: str
    pulls: int = 0
    successes: int = 0
    failures: int = 0
    distribution: BetaDistribution = field(default_factory=BetaDistribution)

    # Cumulative reward
    total_reward: float = 0.0


class ThompsonSamplingBandit:
    """Thompson Sampling multi-armed bandit

    Uses Bayesian approach with Beta-Bernoulli conjugate prior
    """

    def __init__(self, arm_ids: List[str]):
        """Initialize bandit

        Args:
            arm_ids: List of arm identifiers
        """
        self.arms: Dict[str, ArmStats] = {
            arm_id: ArmStats(arm_id=arm_id)
            for arm_id in arm_ids
        }

    def select_arm(self) -> str:
        """Select arm using Thompson Sampling

        Returns:
            Selected arm ID
        """

        # Sample from each arm's posterior
        samples = {
            arm_id: stats.distribution.sample()
            for arm_id, stats in self.arms.items()
        }

        # Select arm with highest sample
        selected_arm = max(samples, key=samples.get)

        logger.debug(f"Thompson Sampling selected: {selected_arm} (samples={samples})")

        return selected_arm

    def update(self, arm_id: str, reward: float):
        """Update arm statistics with observed reward

        Args:
            arm_id: Arm that was pulled
            reward: Observed reward (0 or 1 for binary, or continuous)
        """

        if arm_id not in self.arms:
            raise ValueError(f"Unknown arm: {arm_id}")

        arm = self.arms[arm_id]

        # Update counts
        arm.pulls += 1
        arm.total_reward += reward

        # Update Beta distribution
        if reward >= 0.5:  # Treat as success
            arm.successes += 1
            arm.distribution.alpha += 1
        else:  # Treat as failure
            arm.failures += 1
            arm.distribution.beta += 1

        logger.info(f"Updated arm {arm_id}: pulls={arm.pulls}, successes={arm.successes}, mean={arm.distribution.mean():.3f}")

    def get_best_arm(self) -> Tuple[str, float]:
        """Get arm with highest expected reward

        Returns:
            Tuple of (arm_id, expected_reward)
        """

        best_arm = max(
            self.arms.items(),
            key=lambda x: x[1].distribution.mean()
        )

        return best_arm[0], best_arm[1].distribution.mean()

    def get_arm_stats(self, arm_id: str) -> ArmStats:
        """Get statistics for an arm

        Args:
            arm_id: Arm identifier

        Returns:
            ArmStats
        """

        return self.arms[arm_id]

    def get_all_stats(self) -> List[Dict]:
        """Get statistics for all arms

        Returns:
            List of arm statistics
        """

        stats_list = []

        for arm_id, arm in self.arms.items():
            lower, upper = arm.distribution.confidence_interval()

            stats_list.append({
                "arm_id": arm_id,
                "pulls": arm.pulls,
                "successes": arm.successes,
                "failures": arm.failures,
                "mean": arm.distribution.mean(),
                "confidence_interval_95": (lower, upper),
                "total_reward": arm.total_reward
            })

        # Sort by mean (descending)
        stats_list.sort(key=lambda x: x["mean"], reverse=True)

        return stats_list


class SendTimeOptimizer:
    """Optimize send time using Thompson Sampling

    Learns which hours of the day get best response rates
    """

    def __init__(self):
        # Create arms for each hour of the day (8 AM - 8 PM)
        # Skip quiet hours
        self.hours = list(range(8, 21))  # 8 AM to 8 PM
        self.bandit = ThompsonSamplingBandit([f"hour_{h}" for h in self.hours])

    def select_send_time(self) -> int:
        """Select optimal send hour

        Returns:
            Hour of day (0-23)
        """

        selected_arm = self.bandit.select_arm()
        hour = int(selected_arm.split("_")[1])

        logger.info(f"Selected send time: {hour}:00")

        return hour

    def record_outcome(self, send_hour: int, replied: bool):
        """Record outcome of send attempt

        Args:
            send_hour: Hour when message was sent
            replied: Whether lead replied
        """

        arm_id = f"hour_{send_hour}"
        reward = 1.0 if replied else 0.0

        self.bandit.update(arm_id, reward)

    def get_best_hours(self, top_n: int = 3) -> List[Tuple[int, float]]:
        """Get top N best hours

        Args:
            top_n: Number of hours to return

        Returns:
            List of (hour, expected_reply_rate) tuples
        """

        all_stats = self.bandit.get_all_stats()

        best_hours = [
            (int(stats["arm_id"].split("_")[1]), stats["mean"])
            for stats in all_stats[:top_n]
        ]

        return best_hours

    def get_hourly_performance(self) -> Dict[int, Dict]:
        """Get performance by hour

        Returns:
            Dict mapping hour -> performance stats
        """

        performance = {}

        for hour in self.hours:
            arm_id = f"hour_{hour}"
            stats = self.bandit.get_arm_stats(arm_id)
            lower, upper = stats.distribution.confidence_interval()

            performance[hour] = {
                "attempts": stats.pulls,
                "replies": stats.successes,
                "reply_rate": stats.distribution.mean(),
                "confidence_interval_95": (lower, upper)
            }

        return performance


class TemplateSelector:
    """Select message templates using Thompson Sampling

    Learns which templates get best responses
    """

    def __init__(self, template_ids: List[str]):
        """Initialize template selector

        Args:
            template_ids: List of template identifiers
        """
        self.bandit = ThompsonSamplingBandit(template_ids)

    def select_template(self) -> str:
        """Select template using Thompson Sampling

        Returns:
            Template ID
        """

        return self.bandit.select_arm()

    def record_outcome(self, template_id: str, replied: bool):
        """Record outcome

        Args:
            template_id: Template that was used
            replied: Whether lead replied
        """

        reward = 1.0 if replied else 0.0
        self.bandit.update(template_id, reward)

    def get_template_performance(self) -> List[Dict]:
        """Get performance for all templates

        Returns:
            List of template performance stats
        """

        return self.bandit.get_all_stats()


@dataclass
class ContextFeatures:
    """Context features for contextual bandit"""
    # Lead features
    lead_responded_before: bool = False
    lead_interest_score: float = 0.0
    days_since_last_contact: int = 999

    # Property features
    property_type: str = "unknown"
    price_range: str = "unknown"  # low, medium, high

    # Market features
    market_regime: str = "warm"  # hot, warm, cool, cold

    # Temporal features
    day_of_week: int = 0  # 0=Monday, 6=Sunday
    is_weekend: bool = False

    def to_vector(self) -> np.ndarray:
        """Convert to feature vector

        Returns:
            Feature vector
        """

        features = [
            1.0 if self.lead_responded_before else 0.0,
            self.lead_interest_score,
            min(self.days_since_last_contact / 30.0, 1.0),  # Normalize
            1.0 if self.is_weekend else 0.0,
            self.day_of_week / 7.0,

            # One-hot for market regime
            1.0 if self.market_regime == "hot" else 0.0,
            1.0 if self.market_regime == "warm" else 0.0,
            1.0 if self.market_regime == "cool" else 0.0,
            1.0 if self.market_regime == "cold" else 0.0,

            # One-hot for price range
            1.0 if self.price_range == "low" else 0.0,
            1.0 if self.price_range == "medium" else 0.0,
            1.0 if self.price_range == "high" else 0.0,
        ]

        return np.array(features)


class ContextualBandit:
    """Contextual bandit using Thompson Sampling with linear models

    Each arm has a linear model: E[reward | context] = context · weights
    """

    def __init__(self, arm_ids: List[str], feature_dim: int = 12):
        """Initialize contextual bandit

        Args:
            arm_ids: List of arm identifiers
            feature_dim: Dimension of context feature vector
        """

        self.arm_ids = arm_ids
        self.feature_dim = feature_dim

        # Bayesian linear regression parameters for each arm
        # Prior: N(0, v * I)
        self.v = 1.0  # Prior variance

        self.arms = {
            arm_id: {
                "A": np.eye(feature_dim),  # Precision matrix (inverse covariance)
                "b": np.zeros(feature_dim),  # Weighted sum of rewards
                "pulls": 0
            }
            for arm_id in arm_ids
        }

    def select_arm(self, context: ContextFeatures) -> str:
        """Select arm given context using Thompson Sampling

        Args:
            context: Context features

        Returns:
            Selected arm ID
        """

        x = context.to_vector()

        # Sample from each arm's posterior
        samples = {}

        for arm_id, arm in self.arms.items():
            # Compute posterior mean and covariance
            A_inv = np.linalg.inv(arm["A"])
            theta_mean = A_inv @ arm["b"]
            theta_cov = self.v * A_inv

            # Sample theta from posterior
            theta_sample = np.random.multivariate_normal(theta_mean, theta_cov)

            # Expected reward for this context
            expected_reward = x @ theta_sample

            samples[arm_id] = expected_reward

        # Select arm with highest expected reward
        selected_arm = max(samples, key=samples.get)

        logger.debug(f"Contextual bandit selected: {selected_arm} (samples={samples})")

        return selected_arm

    def update(self, arm_id: str, context: ContextFeatures, reward: float):
        """Update arm with observed reward

        Args:
            arm_id: Arm that was pulled
            context: Context features
            reward: Observed reward
        """

        if arm_id not in self.arms:
            raise ValueError(f"Unknown arm: {arm_id}")

        x = context.to_vector()

        arm = self.arms[arm_id]

        # Update precision matrix A and weighted sum b
        arm["A"] += np.outer(x, x)
        arm["b"] += reward * x
        arm["pulls"] += 1

        logger.info(f"Updated contextual arm {arm_id}: pulls={arm['pulls']}")

    def get_expected_rewards(self, context: ContextFeatures) -> Dict[str, float]:
        """Get expected reward for each arm given context

        Args:
            context: Context features

        Returns:
            Dict mapping arm_id -> expected_reward
        """

        x = context.to_vector()

        expected_rewards = {}

        for arm_id, arm in self.arms.items():
            A_inv = np.linalg.inv(arm["A"])
            theta_mean = A_inv @ arm["b"]

            expected_reward = x @ theta_mean

            expected_rewards[arm_id] = float(expected_reward)

        return expected_rewards


class SequenceSelector:
    """Select message sequences using contextual bandit

    Sequences:
    - aggressive: 3 messages over 5 days
    - standard: 4 messages over 14 days
    - patient: 5 messages over 30 days
    """

    SEQUENCES = ["aggressive", "standard", "patient"]

    def __init__(self):
        """Initialize sequence selector"""
        self.bandit = ContextualBandit(self.SEQUENCES)

    def select_sequence(self, context: ContextFeatures) -> str:
        """Select sequence given context

        Args:
            context: Context features

        Returns:
            Sequence ID
        """

        return self.bandit.select_arm(context)

    def record_outcome(self, sequence_id: str, context: ContextFeatures, converted: bool):
        """Record outcome

        Args:
            sequence_id: Sequence that was used
            context: Context features
            converted: Whether lead converted
        """

        reward = 1.0 if converted else 0.0
        self.bandit.update(sequence_id, context, reward)

    def get_sequence_performance(self, context: ContextFeatures) -> Dict[str, float]:
        """Get expected performance for each sequence

        Args:
            context: Context features

        Returns:
            Dict mapping sequence_id -> expected_conversion_rate
        """

        return self.bandit.get_expected_rewards(context)


# ============================================================================
# Convenience Functions
# ============================================================================

def create_send_time_optimizer() -> SendTimeOptimizer:
    """Create send time optimizer with default settings

    Returns:
        SendTimeOptimizer
    """

    return SendTimeOptimizer()


def create_template_selector(template_ids: List[str]) -> TemplateSelector:
    """Create template selector

    Args:
        template_ids: List of template IDs

    Returns:
        TemplateSelector
    """

    return TemplateSelector(template_ids)


def create_sequence_selector() -> SequenceSelector:
    """Create sequence selector

    Returns:
        SequenceSelector
    """

    return SequenceSelector()
