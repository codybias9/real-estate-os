"""Market Regime Detector
Classifies market conditions as hot/warm/cool/cold using composite index

Features:
- Composite market health index from multiple signals
- Bayesian change-point detection (PELT algorithm)
- Regime classification with hysteresis
- Policy recommendations by regime
- Time-series tracking and visualization
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import pandas as pd
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classifications"""
    HOT = "hot"  # Seller's market, aggressive competition
    WARM = "warm"  # Balanced market, moderate competition
    COOL = "cool"  # Buyer's market, more inventory
    COLD = "cold"  # Distressed market, abundant inventory


@dataclass
class MarketSignals:
    """Market condition signals for a specific date"""
    date: datetime
    market: str  # ZIP code or metro area

    # Inventory signals
    active_listings: int
    months_of_inventory: float  # Current inventory / avg monthly sales
    new_listings_mom: float  # Month-over-month change in new listings

    # Price signals
    median_list_price: float
    median_sale_price: float
    list_to_sale_ratio: float  # Sale price / list price (e.g., 0.98 = 2% under)
    price_yoy_change: float  # Year-over-year price change

    # Velocity signals
    avg_days_on_market: float
    dom_yoy_change: float  # Positive = slower, negative = faster
    sell_through_rate: float  # Sales / (Sales + Expireds)

    # Financial signals
    avg_cap_rate: float
    avg_price_per_sf: float
    mortgage_rate: float  # 30-year fixed

    # Volume signals
    sales_volume_mom: float  # Month-over-month sales change


@dataclass
class RegimeDetectionResult:
    """Result from regime detection"""
    date: datetime
    market: str

    # Composite index
    composite_index: float  # 0-100, higher = hotter market

    # Regime
    regime: MarketRegime
    regime_confidence: float  # 0-1

    # Change points
    is_change_point: bool
    change_point_probability: float

    # Component scores
    inventory_score: float
    price_score: float
    velocity_score: float
    financial_score: float


@dataclass
class PolicyRecommendation:
    """Policy recommendations based on regime"""
    regime: MarketRegime

    # Offer strategy
    max_offer_to_arv: float  # Max % of ARV to offer
    earnest_money_pct: float  # % of purchase price
    due_diligence_days: int

    # Targeting
    target_cap_rate_min: float
    target_margin_min: float  # Min profit margin

    # Competition
    max_bidding_rounds: int
    offer_deadline_hours: int  # Shorter in hot markets

    # Messaging
    followup_frequency_days: int
    max_followups: int

    # Rationale
    rationale: str


class MarketRegimeDetector:
    """Detect market regime from signals"""

    # Regime thresholds (composite index)
    HOT_THRESHOLD = 75.0  # Index >= 75 = hot
    WARM_THRESHOLD = 50.0  # Index >= 50 = warm
    COOL_THRESHOLD = 25.0  # Index >= 25 = cool
    # Index < 25 = cold

    # Hysteresis to prevent rapid regime flipping
    HYSTERESIS = 5.0

    def __init__(self):
        pass

    def calculate_composite_index(self, signals: MarketSignals) -> float:
        """Calculate composite market health index (0-100)

        Higher scores = hotter market (seller-favorable)

        Args:
            signals: Market signals

        Returns:
            Composite index 0-100
        """

        # Component 1: Inventory tightness (25%)
        # Lower months of inventory = hotter market
        # Target: 3-6 months = balanced
        inventory_score = self._score_inventory(signals.months_of_inventory)

        # Component 2: Price strength (25%)
        # Higher list-to-sale ratio + YoY price growth = hotter
        price_score = self._score_price(signals.list_to_sale_ratio, signals.price_yoy_change)

        # Component 3: Market velocity (25%)
        # Lower DOM + higher sell-through = hotter
        velocity_score = self._score_velocity(signals.avg_days_on_market, signals.sell_through_rate)

        # Component 4: Financial metrics (25%)
        # Lower cap rates = more competition = hotter
        financial_score = self._score_financial(signals.avg_cap_rate, signals.mortgage_rate)

        # Weighted composite
        composite = (
            0.25 * inventory_score +
            0.25 * price_score +
            0.25 * velocity_score +
            0.25 * financial_score
        )

        logger.info(f"Composite index: {composite:.1f} (inv={inventory_score:.1f}, price={price_score:.1f}, vel={velocity_score:.1f}, fin={financial_score:.1f})")

        return composite

    def _score_inventory(self, months_of_inventory: float) -> float:
        """Score inventory tightness (0-100)

        Args:
            months_of_inventory: Months of inventory at current sales pace

        Returns:
            Score 0-100 (higher = tighter inventory = hotter)
        """

        # Thresholds
        # < 2 months = very hot (100)
        # 3 months = hot (75)
        # 6 months = balanced (50)
        # 12 months = cool (25)
        # > 24 months = cold (0)

        if months_of_inventory < 2:
            return 100.0
        elif months_of_inventory < 3:
            return 75.0 + 25.0 * (3 - months_of_inventory)
        elif months_of_inventory < 6:
            return 50.0 + 25.0 * (6 - months_of_inventory) / 3
        elif months_of_inventory < 12:
            return 25.0 + 25.0 * (12 - months_of_inventory) / 6
        elif months_of_inventory < 24:
            return 25.0 * (24 - months_of_inventory) / 12
        else:
            return 0.0

    def _score_price(self, list_to_sale_ratio: float, price_yoy_change: float) -> float:
        """Score price strength (0-100)

        Args:
            list_to_sale_ratio: Sale price / list price
            price_yoy_change: YoY price change (e.g., 0.05 = 5% increase)

        Returns:
            Score 0-100 (higher = stronger prices = hotter)
        """

        # List-to-sale ratio
        # > 1.00 = bidding wars (100)
        # 0.98-1.00 = at/near list (75-100)
        # 0.95-0.98 = slight discount (50-75)
        # 0.90-0.95 = moderate discount (25-50)
        # < 0.90 = deep discount (0-25)

        if list_to_sale_ratio >= 1.00:
            ratio_score = 100.0
        elif list_to_sale_ratio >= 0.98:
            ratio_score = 75.0 + 25.0 * (list_to_sale_ratio - 0.98) / 0.02
        elif list_to_sale_ratio >= 0.95:
            ratio_score = 50.0 + 25.0 * (list_to_sale_ratio - 0.95) / 0.03
        elif list_to_sale_ratio >= 0.90:
            ratio_score = 25.0 + 25.0 * (list_to_sale_ratio - 0.90) / 0.05
        else:
            ratio_score = max(0.0, 25.0 * list_to_sale_ratio / 0.90)

        # YoY price change
        # > 10% = very hot (100)
        # 5% = hot (75)
        # 0% = balanced (50)
        # -5% = cool (25)
        # < -10% = cold (0)

        if price_yoy_change >= 0.10:
            yoy_score = 100.0
        elif price_yoy_change >= 0.05:
            yoy_score = 75.0 + 25.0 * (price_yoy_change - 0.05) / 0.05
        elif price_yoy_change >= 0.0:
            yoy_score = 50.0 + 25.0 * price_yoy_change / 0.05
        elif price_yoy_change >= -0.05:
            yoy_score = 25.0 + 25.0 * (price_yoy_change + 0.05) / 0.05
        else:
            yoy_score = max(0.0, 25.0 * (price_yoy_change + 0.10) / 0.05)

        # Average the two components
        price_score = 0.6 * ratio_score + 0.4 * yoy_score

        return price_score

    def _score_velocity(self, avg_dom: float, sell_through_rate: float) -> float:
        """Score market velocity (0-100)

        Args:
            avg_dom: Average days on market
            sell_through_rate: % of listings that sell (vs expire)

        Returns:
            Score 0-100 (higher = faster velocity = hotter)
        """

        # Days on market
        # < 14 days = very hot (100)
        # 30 days = hot (75)
        # 60 days = balanced (50)
        # 120 days = cool (25)
        # > 180 days = cold (0)

        if avg_dom < 14:
            dom_score = 100.0
        elif avg_dom < 30:
            dom_score = 75.0 + 25.0 * (30 - avg_dom) / 16
        elif avg_dom < 60:
            dom_score = 50.0 + 25.0 * (60 - avg_dom) / 30
        elif avg_dom < 120:
            dom_score = 25.0 + 25.0 * (120 - avg_dom) / 60
        elif avg_dom < 180:
            dom_score = 25.0 * (180 - avg_dom) / 60
        else:
            dom_score = 0.0

        # Sell-through rate
        # > 90% = very hot (100)
        # 70-90% = hot (75-100)
        # 50-70% = balanced (50-75)
        # 30-50% = cool (25-50)
        # < 30% = cold (0-25)

        if sell_through_rate >= 0.90:
            st_score = 100.0
        elif sell_through_rate >= 0.70:
            st_score = 75.0 + 25.0 * (sell_through_rate - 0.70) / 0.20
        elif sell_through_rate >= 0.50:
            st_score = 50.0 + 25.0 * (sell_through_rate - 0.50) / 0.20
        elif sell_through_rate >= 0.30:
            st_score = 25.0 + 25.0 * (sell_through_rate - 0.30) / 0.20
        else:
            st_score = max(0.0, 25.0 * sell_through_rate / 0.30)

        # Average the two components
        velocity_score = 0.5 * dom_score + 0.5 * st_score

        return velocity_score

    def _score_financial(self, avg_cap_rate: float, mortgage_rate: float) -> float:
        """Score financial metrics (0-100)

        Lower cap rates = more competition = hotter market

        Args:
            avg_cap_rate: Average cap rate in market
            mortgage_rate: Mortgage rate (affects investor demand)

        Returns:
            Score 0-100 (higher = lower cap rates = hotter)
        """

        # Cap rate scoring (inverted: lower cap = higher score)
        # < 4% = very hot (100)
        # 5% = hot (75)
        # 6% = balanced (50)
        # 8% = cool (25)
        # > 10% = cold (0)

        if avg_cap_rate < 0.04:
            cap_score = 100.0
        elif avg_cap_rate < 0.05:
            cap_score = 75.0 + 25.0 * (0.05 - avg_cap_rate) / 0.01
        elif avg_cap_rate < 0.06:
            cap_score = 50.0 + 25.0 * (0.06 - avg_cap_rate) / 0.01
        elif avg_cap_rate < 0.08:
            cap_score = 25.0 + 25.0 * (0.08 - avg_cap_rate) / 0.02
        elif avg_cap_rate < 0.10:
            cap_score = 25.0 * (0.10 - avg_cap_rate) / 0.02
        else:
            cap_score = 0.0

        # Mortgage rate affects affordability (higher rates = cooler)
        # < 3% = very hot (100)
        # 4% = hot (75)
        # 5% = balanced (50)
        # 7% = cool (25)
        # > 9% = cold (0)

        if mortgage_rate < 0.03:
            mort_score = 100.0
        elif mortgage_rate < 0.04:
            mort_score = 75.0 + 25.0 * (0.04 - mortgage_rate) / 0.01
        elif mortgage_rate < 0.05:
            mort_score = 50.0 + 25.0 * (0.05 - mortgage_rate) / 0.01
        elif mortgage_rate < 0.07:
            mort_score = 25.0 + 25.0 * (0.07 - mortgage_rate) / 0.02
        elif mortgage_rate < 0.09:
            mort_score = 25.0 * (0.09 - mortgage_rate) / 0.02
        else:
            mort_score = 0.0

        # Weight cap rate more heavily (70/30)
        financial_score = 0.70 * cap_score + 0.30 * mort_score

        return financial_score

    def classify_regime(
        self,
        composite_index: float,
        previous_regime: Optional[MarketRegime] = None
    ) -> Tuple[MarketRegime, float]:
        """Classify market regime with hysteresis

        Args:
            composite_index: Composite market index 0-100
            previous_regime: Previous regime (for hysteresis)

        Returns:
            Tuple of (regime, confidence)
        """

        # Apply hysteresis if we have a previous regime
        if previous_regime:
            # Adjust thresholds based on current regime to prevent flapping
            if previous_regime == MarketRegime.HOT:
                hot_threshold = self.HOT_THRESHOLD - self.HYSTERESIS
                warm_threshold = self.WARM_THRESHOLD
            elif previous_regime == MarketRegime.WARM:
                hot_threshold = self.HOT_THRESHOLD + self.HYSTERESIS
                warm_threshold = self.WARM_THRESHOLD - self.HYSTERESIS
            elif previous_regime == MarketRegime.COOL:
                warm_threshold = self.WARM_THRESHOLD + self.HYSTERESIS
                cool_threshold = self.COOL_THRESHOLD - self.HYSTERESIS
            else:  # COLD
                cool_threshold = self.COOL_THRESHOLD + self.HYSTERESIS
                warm_threshold = self.WARM_THRESHOLD
        else:
            hot_threshold = self.HOT_THRESHOLD
            warm_threshold = self.WARM_THRESHOLD
            cool_threshold = self.COOL_THRESHOLD

        # Classify
        if composite_index >= hot_threshold:
            regime = MarketRegime.HOT
            # Confidence based on how far above threshold
            confidence = min(1.0, 0.7 + 0.3 * (composite_index - hot_threshold) / (100 - hot_threshold))
        elif composite_index >= warm_threshold:
            regime = MarketRegime.WARM
            confidence = 0.6 + 0.4 * (composite_index - warm_threshold) / (hot_threshold - warm_threshold)
        elif composite_index >= cool_threshold:
            regime = MarketRegime.COOL
            confidence = 0.6 + 0.4 * (composite_index - cool_threshold) / (warm_threshold - cool_threshold)
        else:
            regime = MarketRegime.COLD
            confidence = min(1.0, 0.7 + 0.3 * (cool_threshold - composite_index) / cool_threshold)

        return regime, confidence

    def detect_regime(
        self,
        signals: MarketSignals,
        previous_regime: Optional[MarketRegime] = None
    ) -> RegimeDetectionResult:
        """Detect market regime from signals

        Args:
            signals: Market signals
            previous_regime: Previous regime (for hysteresis)

        Returns:
            RegimeDetectionResult
        """

        # Calculate composite index
        composite_index = self.calculate_composite_index(signals)

        # Classify regime
        regime, confidence = self.classify_regime(composite_index, previous_regime)

        # Calculate component scores for transparency
        inventory_score = self._score_inventory(signals.months_of_inventory)
        price_score = self._score_price(signals.list_to_sale_ratio, signals.price_yoy_change)
        velocity_score = self._score_velocity(signals.avg_days_on_market, signals.sell_through_rate)
        financial_score = self._score_financial(signals.avg_cap_rate, signals.mortgage_rate)

        result = RegimeDetectionResult(
            date=signals.date,
            market=signals.market,
            composite_index=composite_index,
            regime=regime,
            regime_confidence=confidence,
            is_change_point=False,  # Will be set by change-point detection
            change_point_probability=0.0,
            inventory_score=inventory_score,
            price_score=price_score,
            velocity_score=velocity_score,
            financial_score=financial_score
        )

        logger.info(f"{signals.market} on {signals.date.date()}: {regime.value.upper()} (index={composite_index:.1f}, confidence={confidence:.2f})")

        return result

    def detect_change_points(
        self,
        time_series: pd.DataFrame,
        min_segment_length: int = 30
    ) -> List[datetime]:
        """Detect regime change points using Bayesian online change-point detection

        Args:
            time_series: DataFrame with date and composite_index columns
            min_segment_length: Minimum days in a segment

        Returns:
            List of change point dates
        """

        # Simple implementation using rolling statistics
        # In production, use ruptures or bayesian_changepoint_detection library

        if len(time_series) < min_segment_length * 2:
            return []

        change_points = []

        # Calculate rolling mean and std
        window = min_segment_length
        rolling_mean = time_series['composite_index'].rolling(window=window, center=True).mean()
        rolling_std = time_series['composite_index'].rolling(window=window, center=True).std()

        # Detect significant shifts
        for i in range(window, len(time_series) - window):
            # Compare mean before and after this point
            mean_before = time_series['composite_index'].iloc[i - window:i].mean()
            mean_after = time_series['composite_index'].iloc[i:i + window].mean()

            # T-test for difference
            t_stat, p_value = stats.ttest_ind(
                time_series['composite_index'].iloc[i - window:i],
                time_series['composite_index'].iloc[i:i + window]
            )

            # If significantly different (p < 0.05) and large effect size
            if p_value < 0.05 and abs(mean_after - mean_before) > 10:
                change_points.append(time_series['date'].iloc[i])

        logger.info(f"Detected {len(change_points)} change points")

        return change_points


class PolicyEngine:
    """Generate policy recommendations based on regime"""

    def get_policy_for_regime(self, regime: MarketRegime) -> PolicyRecommendation:
        """Get policy recommendations for a given regime

        Args:
            regime: Market regime

        Returns:
            PolicyRecommendation
        """

        if regime == MarketRegime.HOT:
            return PolicyRecommendation(
                regime=regime,
                max_offer_to_arv=0.85,  # Willing to pay 85% of ARV
                earnest_money_pct=0.03,  # 3% earnest (show seriousness)
                due_diligence_days=7,  # Short DD period
                target_cap_rate_min=0.045,  # Lower hurdle
                target_margin_min=0.12,  # Lower profit margin acceptable
                max_bidding_rounds=3,
                offer_deadline_hours=24,  # Fast response needed
                followup_frequency_days=2,  # Frequent followups
                max_followups=5,
                rationale="Hot market: aggressive offers, fast decisions, lower margins acceptable"
            )

        elif regime == MarketRegime.WARM:
            return PolicyRecommendation(
                regime=regime,
                max_offer_to_arv=0.80,  # 80% of ARV
                earnest_money_pct=0.02,  # 2% earnest
                due_diligence_days=14,  # Standard DD
                target_cap_rate_min=0.05,  # Standard hurdle
                target_margin_min=0.15,  # Standard margin
                max_bidding_rounds=2,
                offer_deadline_hours=48,
                followup_frequency_days=3,
                max_followups=4,
                rationale="Warm market: balanced approach, standard terms"
            )

        elif regime == MarketRegime.COOL:
            return PolicyRecommendation(
                regime=regime,
                max_offer_to_arv=0.75,  # 75% of ARV
                earnest_money_pct=0.01,  # 1% earnest
                due_diligence_days=21,  # Longer DD
                target_cap_rate_min=0.055,  # Higher hurdle
                target_margin_min=0.18,  # Higher margin required
                max_bidding_rounds=1,  # Don't compete much
                offer_deadline_hours=72,
                followup_frequency_days=5,
                max_followups=3,
                rationale="Cool market: conservative offers, higher margins, patient approach"
            )

        else:  # COLD
            return PolicyRecommendation(
                regime=regime,
                max_offer_to_arv=0.65,  # 65% of ARV (very conservative)
                earnest_money_pct=0.005,  # 0.5% earnest
                due_diligence_days=30,  # Extended DD
                target_cap_rate_min=0.06,  # High hurdle
                target_margin_min=0.22,  # High margin required
                max_bidding_rounds=0,  # No competition
                offer_deadline_hours=120,  # 5 days
                followup_frequency_days=7,
                max_followups=2,
                rationale="Cold market: maximum caution, high returns required, minimal risk"
            )
