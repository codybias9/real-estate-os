"""Bayesian Change-Point Detection
Detect structural breaks in market regime time series

Algorithms:
- BOCPD (Bayesian Online Change Point Detection)
- PELT (Pruned Exact Linear Time) for offline analysis
- Cumulative Sum (CUSUM) for online monitoring
"""

from typing import List, Tuple, Optional
import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import logsumexp
import logging

logger = logging.getLogger(__name__)


class BayesianOnlineChangePointDetection:
    """Bayesian Online Change Point Detection (BOCPD)

    Based on Adams & MacKay (2007) "Bayesian Online Changepoint Detection"

    Maintains a probability distribution over the run length (time since last change point)
    and updates it online as new data arrives.
    """

    def __init__(
        self,
        hazard_lambda: float = 250.0,
        alpha: float = 1.0,
        beta: float = 1.0,
        kappa: float = 1.0,
        mu: float = 50.0
    ):
        """Initialize BOCPD

        Args:
            hazard_lambda: Expected time between change points (in periods)
            alpha: Prior shape parameter for precision (gamma distribution)
            beta: Prior scale parameter for precision
            kappa: Prior precision of mean
            mu: Prior mean
        """
        self.hazard_lambda = hazard_lambda

        # Gaussian-Gamma conjugate prior parameters
        self.alpha0 = alpha
        self.beta0 = beta
        self.kappa0 = kappa
        self.mu0 = mu

        # Current state
        self.t = 0  # Current time
        self.run_length_log_probs = np.array([0.0])  # Log P(r_t | x_1:t)

        # Sufficient statistics for each run length
        self.alpha = np.array([alpha])
        self.beta = np.array([beta])
        self.kappa = np.array([kappa])
        self.mu = np.array([mu])

        # History
        self.changepoint_probs = []
        self.run_length_probs = []

    def hazard_function(self, r: np.ndarray) -> np.ndarray:
        """Constant hazard function

        P(changepoint at t | run length r) = 1 / lambda

        Args:
            r: Run length (array)

        Returns:
            Hazard probability
        """
        return 1.0 / self.hazard_lambda * np.ones_like(r)

    def update(self, x: float) -> Tuple[float, np.ndarray]:
        """Update with new observation

        Args:
            x: New observation

        Returns:
            Tuple of (changepoint_probability, run_length_distribution)
        """
        self.t += 1

        # Calculate predictive probability for each run length
        # Using Student's t-distribution (marginalizing over precision)
        pred_log_probs = self._student_t_log_prob(x)

        # Evaluate growth probabilities
        # P(r_t = r_{t-1} + 1 | x_1:t) - no changepoint
        growth_log_probs = self.run_length_log_probs + pred_log_probs + np.log(1 - self.hazard_function(np.arange(len(self.run_length_log_probs))))

        # Evaluate changepoint probabilities
        # P(r_t = 0 | x_1:t) - changepoint occurred
        cp_log_prob = logsumexp(self.run_length_log_probs + pred_log_probs + np.log(self.hazard_function(np.arange(len(self.run_length_log_probs)))))

        # Combine
        new_run_length_log_probs = np.concatenate(([cp_log_prob], growth_log_probs))

        # Normalize
        new_run_length_log_probs -= logsumexp(new_run_length_log_probs)

        # Store current changepoint probability
        changepoint_prob = np.exp(cp_log_prob - logsumexp(new_run_length_log_probs))
        self.changepoint_probs.append(changepoint_prob)
        self.run_length_probs.append(np.exp(new_run_length_log_probs))

        # Update run length distribution
        self.run_length_log_probs = new_run_length_log_probs

        # Update sufficient statistics
        self._update_statistics(x)

        # Prune to prevent memory growth (keep only likely run lengths)
        self._prune(threshold=-10.0)

        return changepoint_prob, np.exp(self.run_length_log_probs)

    def _student_t_log_prob(self, x: float) -> np.ndarray:
        """Calculate log predictive probability under Student's t

        Args:
            x: Observation

        Returns:
            Log probability for each run length
        """
        # Parameters of predictive distribution
        df = 2 * self.alpha
        loc = self.mu
        scale = np.sqrt(self.beta * (self.kappa + 1) / (self.alpha * self.kappa))

        # Student's t log pdf
        log_probs = stats.t.logpdf(x, df=df, loc=loc, scale=scale)

        return log_probs

    def _update_statistics(self, x: float):
        """Update sufficient statistics for Gaussian-Gamma posterior

        Args:
            x: New observation
        """
        # Append prior for new run length
        self.mu = np.concatenate(([self.mu0], self.mu))
        self.kappa = np.concatenate(([self.kappa0], self.kappa))
        self.alpha = np.concatenate(([self.alpha0], self.alpha))
        self.beta = np.concatenate(([self.beta0], self.beta))

        # Update with observation for existing run lengths
        self.mu[1:] = (self.kappa[1:] * self.mu[1:] + x) / (self.kappa[1:] + 1)
        self.kappa[1:] = self.kappa[1:] + 1
        self.alpha[1:] = self.alpha[1:] + 0.5
        self.beta[1:] = self.beta[1:] + (self.kappa[1:] * (x - self.mu[1:]) ** 2) / (2 * (self.kappa[1:] + 1))

    def _prune(self, threshold: float = -10.0):
        """Prune unlikely run lengths

        Args:
            threshold: Log probability threshold
        """
        # Keep only run lengths with log prob > threshold
        keep_indices = self.run_length_log_probs >= threshold

        if not np.any(keep_indices):
            # Keep at least the most likely
            keep_indices[np.argmax(self.run_length_log_probs)] = True

        self.run_length_log_probs = self.run_length_log_probs[keep_indices]
        self.mu = self.mu[keep_indices]
        self.kappa = self.kappa[keep_indices]
        self.alpha = self.alpha[keep_indices]
        self.beta = self.beta[keep_indices]

    def get_most_likely_run_length(self) -> int:
        """Get the most likely current run length

        Returns:
            Run length (time since last change point)
        """
        return np.argmax(self.run_length_log_probs)

    def get_changepoint_probabilities(self) -> np.ndarray:
        """Get history of changepoint probabilities

        Returns:
            Array of changepoint probabilities over time
        """
        return np.array(self.changepoint_probs)


class CUSUMDetector:
    """Cumulative Sum (CUSUM) change-point detection

    Detects shifts in the mean of a time series.
    """

    def __init__(
        self,
        threshold: float = 5.0,
        drift: float = 0.5,
        reset_after_detection: bool = True
    ):
        """Initialize CUSUM detector

        Args:
            threshold: Detection threshold (higher = less sensitive)
            drift: Allowable drift (should be ~0.5 * expected shift)
            reset_after_detection: Reset cumulative sums after detection
        """
        self.threshold = threshold
        self.drift = drift
        self.reset_after_detection = reset_after_detection

        # State
        self.cumsum_pos = 0.0  # Positive cumulative sum
        self.cumsum_neg = 0.0  # Negative cumulative sum
        self.mean_estimate = None
        self.history = []

    def update(self, x: float) -> bool:
        """Update with new observation

        Args:
            x: New observation

        Returns:
            True if change point detected
        """
        # Initialize mean estimate
        if self.mean_estimate is None:
            self.mean_estimate = x
            self.history.append(x)
            return False

        # Calculate deviation from mean
        deviation = x - self.mean_estimate

        # Update cumulative sums
        self.cumsum_pos = max(0, self.cumsum_pos + deviation - self.drift)
        self.cumsum_neg = min(0, self.cumsum_neg + deviation + self.drift)

        # Check for change point
        detected = (self.cumsum_pos > self.threshold) or (self.cumsum_neg < -self.threshold)

        if detected and self.reset_after_detection:
            # Reset
            self.cumsum_pos = 0.0
            self.cumsum_neg = 0.0
            self.mean_estimate = x
            self.history = [x]
        else:
            # Update running mean
            self.history.append(x)
            self.mean_estimate = np.mean(self.history[-100:])  # Use last 100 points

        return detected


def detect_changepoints_offline(
    time_series: np.ndarray,
    method: str = "bocpd",
    **kwargs
) -> List[int]:
    """Detect change points in time series (offline analysis)

    Args:
        time_series: 1D array of observations
        method: Detection method ("bocpd", "cusum", or "ruptures")
        **kwargs: Method-specific parameters

    Returns:
        List of change point indices
    """
    if method == "bocpd":
        return _detect_bocpd_offline(time_series, **kwargs)
    elif method == "cusum":
        return _detect_cusum_offline(time_series, **kwargs)
    elif method == "ruptures":
        return _detect_ruptures_offline(time_series, **kwargs)
    else:
        raise ValueError(f"Unknown method: {method}")


def _detect_bocpd_offline(
    time_series: np.ndarray,
    hazard_lambda: float = 250.0,
    threshold: float = 0.5
) -> List[int]:
    """Detect change points using BOCPD

    Args:
        time_series: Observations
        hazard_lambda: Expected time between change points
        threshold: Probability threshold for detection

    Returns:
        List of change point indices
    """
    detector = BayesianOnlineChangePointDetection(hazard_lambda=hazard_lambda)

    change_points = []

    for i, x in enumerate(time_series):
        cp_prob, _ = detector.update(x)

        if cp_prob > threshold:
            change_points.append(i)

    logger.info(f"BOCPD detected {len(change_points)} change points")

    return change_points


def _detect_cusum_offline(
    time_series: np.ndarray,
    threshold: float = 5.0,
    drift: float = 0.5
) -> List[int]:
    """Detect change points using CUSUM

    Args:
        time_series: Observations
        threshold: Detection threshold
        drift: Allowable drift

    Returns:
        List of change point indices
    """
    detector = CUSUMDetector(threshold=threshold, drift=drift)

    change_points = []

    for i, x in enumerate(time_series):
        detected = detector.update(x)

        if detected:
            change_points.append(i)

    logger.info(f"CUSUM detected {len(change_points)} change points")

    return change_points


def _detect_ruptures_offline(
    time_series: np.ndarray,
    model: str = "rbf",
    min_size: int = 30,
    jump: int = 1,
    pen: float = 10.0
) -> List[int]:
    """Detect change points using ruptures library (if available)

    Args:
        time_series: Observations
        model: Cost function ("l2", "rbf", "linear", "normal")
        min_size: Minimum segment size
        jump: Subsample step (1 = no subsampling)
        pen: Penalty value (higher = fewer change points)

    Returns:
        List of change point indices
    """
    try:
        import ruptures as rpt

        # Use PELT algorithm
        algo = rpt.Pelt(model=model, min_size=min_size, jump=jump).fit(time_series.reshape(-1, 1))
        change_points = algo.predict(pen=pen)

        # Remove the final index (end of series)
        if change_points and change_points[-1] == len(time_series):
            change_points = change_points[:-1]

        logger.info(f"Ruptures PELT detected {len(change_points)} change points")

        return change_points

    except ImportError:
        logger.warning("ruptures library not available, falling back to BOCPD")
        return _detect_bocpd_offline(time_series)


def segment_time_series(
    df: pd.DataFrame,
    change_points: List[int],
    value_column: str = "composite_index",
    date_column: str = "date"
) -> pd.DataFrame:
    """Segment time series by change points

    Args:
        df: DataFrame with time series
        change_points: List of change point indices
        value_column: Column name for values
        date_column: Column name for dates

    Returns:
        DataFrame with segment labels and statistics
    """
    # Add segment labels
    df = df.copy()
    df["segment"] = 0

    for i, cp in enumerate(sorted(change_points)):
        df.loc[df.index >= cp, "segment"] = i + 1

    # Calculate segment statistics
    segment_stats = df.groupby("segment").agg({
        value_column: ["mean", "std", "min", "max", "count"],
        date_column: ["min", "max"]
    })

    segment_stats.columns = ["_".join(col).strip() for col in segment_stats.columns.values]

    return df, segment_stats
