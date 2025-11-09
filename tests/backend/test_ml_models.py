"""
ML Models Tests
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from ml.models.comp_critic import CompCritic
from ml.models.offer_optimizer import OfferOptimizer
from ml.models.dcf_engine import DCFEngine, UnitMix, Lease
from ml.models.regime_monitor import RegimeMonitor
from ml.models.negotiation_brain import NegotiationBrain


class TestCompCritic:
    def test_retrieve_candidates(self):
        """Test comp retrieval"""
        critic = CompCritic()
        subject = {
            "property_id": "TEST-001",
            "building_sqft": 2400,
            "lot_size_sqft": 7500
        }
        candidates = critic.retrieve_candidates(subject, k=10)
        assert len(candidates) == 10
        assert all("distance_weight" in c for c in candidates)
        assert all("recency_weight" in c for c in candidates)

    def test_value_property(self):
        """Test full valuation pipeline"""
        critic = CompCritic()
        subject = {
            "property_id": "TEST-001",
            "list_price": 400000,
            "building_sqft": 2400,
            "lot_size_sqft": 7500,
            "bedrooms": 4,
            "bathrooms": 3.0,
            "condition_score": 7.5
        }
        result = critic.value_property(subject)
        assert "estimated_value" in result
        assert result["estimated_value"] > 0
        assert "confidence_interval" in result
        assert len(result["adjustment_waterfall"]) > 0


class TestOfferOptimizer:
    def test_feasible_optimization(self):
        """Test feasible case returns optimal solution"""
        optimizer = OfferOptimizer()
        property_data = {"arv": 450000, "repair_cost": 30000}
        market_conditions = {"temperature": 0.65}
        regime_policy = {"regime": "WARM"}

        result = optimizer.optimize(
            property_data, market_conditions, regime_policy, scenario="feasible"
        )

        assert result["status"] == "OPTIMAL"
        assert "solution" in result
        assert result["solution"]["price"] > 0
        assert all(result["constraints"][c]["satisfied"] for c in result["constraints"])

    def test_infeasible_optimization(self):
        """Test infeasible case is detected"""
        optimizer = OfferOptimizer()
        property_data = {"arv": 450000, "repair_cost": 30000}
        market_conditions = {"temperature": 0.65}
        regime_policy = {"regime": "WARM"}

        result = optimizer.optimize(
            property_data, market_conditions, regime_policy, scenario="infeasible"
        )

        assert result["status"] == "INFEASIBLE"
        assert "constraints_violated" in result

    def test_pareto_frontier(self):
        """Test Pareto frontier generation"""
        optimizer = OfferOptimizer()
        property_data = {"arv": 450000, "repair_cost": 30000}
        market_conditions = {"temperature": 0.65}
        regime_policy = {"regime": "WARM"}

        frontier = optimizer.generate_pareto_frontier(
            property_data, market_conditions, regime_policy, n_points=10
        )

        assert len(frontier) == 10
        assert all("price" in p and "win_probability" in p for p in frontier)


class TestDCFEngine:
    def test_multifamily_dcf(self):
        """Test MF DCF calculation"""
        engine = DCFEngine(seed=42)
        unit_mix = [
            UnitMix("1BR", 10, 750, 1200, 1300, 0.05, 0.03),
            UnitMix("2BR", 15, 1100, 1800, 1900, 0.05, 0.03)
        ]

        result = engine.model_mf(
            {"property_id": "MF-TEST", "purchase_price": 3_000_000},
            unit_mix,
            {"hold_period": 5}
        )

        assert result["property_type"] == "MULTIFAMILY"
        assert "npv" in result
        assert "irr" in result
        assert "dscr" in result
        assert len(result["cash_flows"]) == 5

    def test_cre_dcf(self):
        """Test CRE DCF calculation"""
        engine = DCFEngine(seed=42)
        leases = [
            Lease("Tenant A", 10000, 300000, "2023-01-01", "2028-01-01", "NNN", 0.75, 40, 2),
            Lease("Tenant B", 5000, 150000, "2023-06-01", "2026-06-01", "Gross", 0.60, 50, 1)
        ]

        result = engine.model_cre(
            {"property_id": "CRE-TEST", "purchase_price": 5_000_000},
            leases,
            {"hold_period": 7}
        )

        assert result["property_type"] == "COMMERCIAL"
        assert "irr" in result
        assert len(result["cash_flows"]) == 7


class TestRegimeMonitor:
    def test_composite_index(self):
        """Test composite index calculation"""
        monitor = RegimeMonitor()
        market_data = {
            "inventory_months": 3.0,
            "price_trend_yoy": 0.05,
            "sales_velocity": 0.3,
            "mortgage_rate": 0.065
        }
        composite = monitor.compute_composite_index(market_data)
        assert 0 <= composite <= 1

    def test_regime_detection(self):
        """Test regime classification"""
        monitor = RegimeMonitor()
        regime, confidence = monitor.detect_regime(0.65)
        assert regime in ["COLD", "COOL", "WARM", "HOT"]
        assert 0 < confidence <= 1

    def test_policy_generation(self):
        """Test policy generation for all regimes"""
        monitor = RegimeMonitor()
        for regime in ["COLD", "COOL", "WARM", "HOT"]:
            policy = monitor.generate_policy(regime, "TEST-MARKET")
            assert "max_offer_pct_arv" in policy
            assert "min_profit_margin" in policy
            assert "contingencies_required" in policy


class TestNegotiationBrain:
    def test_reply_classification(self):
        """Test message classification"""
        brain = NegotiationBrain()

        test_cases = [
            ("Yes, I'm interested in selling", "INTERESTED"),
            ("Not interested, remove me", "NOT_INTERESTED"),
            ("How much are you offering?", "MORE_INFO"),
            ("I want $500k for it", "COUNTER_OFFER"),
            ("Call me next week", "CALLBACK_LATER")
        ]

        for message, expected_class in test_cases:
            result = brain.classify_reply(message)
            assert result["predicted_class"] == expected_class

    def test_send_time_selection(self):
        """Test Thompson Sampling for send time"""
        brain = NegotiationBrain()
        result = brain.select_send_time("America/New_York")

        assert "arm_selected" in result
        assert "send_hour" in result
        assert 0 <= result["send_hour"] < 24

    def test_compliance_dnc(self):
        """Test DNC list blocking"""
        brain = NegotiationBrain()
        brain.dnc_list.add("+1234567890")

        result = brain.check_compliance(
            {"id": "TEST", "phone": "+1234567890", "timezone": "America/New_York"},
            __import__('datetime').datetime.now(__import__('pytz').UTC),
            []
        )

        assert not result["compliant"]
        assert any("DNC_LIST" in v for v in result["violations"])

    def test_confusion_matrix_generation(self):
        """Test confusion matrix generation"""
        brain = NegotiationBrain()
        cm = brain.generate_confusion_matrix()

        assert "classes" in cm
        assert "matrix" in cm
        assert "per_class_metrics" in cm
        assert cm["accuracy"] > 0
