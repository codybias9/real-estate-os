"""Tests for Policy Kernel"""

import pytest

from policy_kernel import PolicyKernel, PolicyVerdict, PolicyDecision, RuleContext
from policy_kernel.rules import CostCapRule, QuotaRule, AllowListRule, DenyListRule
from policy_kernel.providers import ProviderConfig, ProviderTier


def test_policy_kernel_creation():
    """Test basic kernel creation"""
    kernel = PolicyKernel()
    assert len(kernel.providers) > 0


def test_provider_priority():
    """Test hybrid ladder prioritization"""
    providers = [
        ProviderConfig(name="scraper", tier=ProviderTier.SCRAPE, confidence=0.7),
        ProviderConfig(name="open", tier=ProviderTier.OPEN, confidence=0.8),
        ProviderConfig(name="paid", tier=ProviderTier.PAID, confidence=0.95),
    ]

    kernel = PolicyKernel(providers=providers)
    priority = kernel.get_provider_priority("test_field")

    # Should be: OPEN > PAID > SCRAPE
    assert priority[0] == "open"
    assert priority[1] == "paid"
    assert priority[2] == "scraper"


def test_cost_cap_rule():
    """Test cost cap enforcement"""
    usage_tracker = {"tenant-1": 450}  # Already spent 450 cents

    rule = CostCapRule(daily_cap_cents=500, usage_tracker=usage_tracker)

    # Within budget
    context = RuleContext(
        tenant_id="tenant-1",
        action="test",
        resource="provider",
        metadata={"cost_cents": 30}
    )
    result, reason = rule.evaluate(context)
    assert result.value == "warn"  # 450 + 30 = 480 (96% of cap)

    # Over budget
    context_over = RuleContext(
        tenant_id="tenant-1",
        action="test",
        resource="provider",
        metadata={"cost_cents": 100}
    )
    result_over, reason_over = rule.evaluate(context_over)
    assert result_over.value == "deny"


def test_quota_rule():
    """Test quota enforcement"""
    usage_tracker = {"provider-1": 95}  # 95 calls today

    rule = QuotaRule(daily_quota=100, usage_tracker=usage_tracker)

    # Within quota
    context = RuleContext(
        tenant_id="tenant-1",
        action="test",
        resource="provider-1"
    )
    result, _ = rule.evaluate(context)
    assert result.value == "warn"  # 95/100 = 95% (triggers warning)

    # Over quota
    usage_tracker["provider-1"] = 100
    result_over, _ = rule.evaluate(context)
    assert result_over.value == "deny"


def test_allow_list_rule():
    """Test allow list enforcement"""
    rule = AllowListRule(allowed={"attom", "regrid"})

    # Allowed
    context_ok = RuleContext(tenant_id="t1", action="test", resource="attom")
    result_ok, _ = rule.evaluate(context_ok)
    assert result_ok.value == "allow"

    # Not allowed
    context_deny = RuleContext(tenant_id="t1", action="test", resource="unknown")
    result_deny, _ = rule.evaluate(context_deny)
    assert result_deny.value == "deny"


def test_deny_list_rule():
    """Test deny list enforcement"""
    rule = DenyListRule(denied={"blocked_provider"})

    # Not denied
    context_ok = RuleContext(tenant_id="t1", action="test", resource="attom")
    result_ok, _ = rule.evaluate(context_ok)
    assert result_ok.value == "allow"

    # Denied
    context_deny = RuleContext(tenant_id="t1", action="test", resource="blocked_provider")
    result_deny, _ = rule.evaluate(context_deny)
    assert result_deny.value == "deny"


def test_kernel_evaluation():
    """Test full kernel evaluation with multiple rules"""
    kernel = PolicyKernel()

    # Add rules
    kernel.add_rule(AllowListRule(allowed={"attom", "regrid"}))
    kernel.add_rule(CostCapRule(daily_cap_cents=1000, usage_tracker={}))

    # Evaluate allowed provider within budget
    context = RuleContext(
        tenant_id="tenant-1",
        action="enrichment.fetch",
        resource="attom",
        metadata={"cost_cents": 5}
    )

    decision = kernel.evaluate(context)
    assert decision.verdict == PolicyVerdict.ALLOW
    assert decision.rules_evaluated == 2


def test_kernel_can_use_provider():
    """Test provider usage check"""
    providers = [
        ProviderConfig(name="attom", tier=ProviderTier.PAID, cost_per_call_cents=5, daily_quota=1000)
    ]

    kernel = PolicyKernel(providers=providers)

    # Can use
    decision = kernel.can_use_provider("tenant-1", "attom")
    assert decision.verdict in [PolicyVerdict.ALLOW, PolicyVerdict.WARN]

    # Unknown provider
    decision_unknown = kernel.can_use_provider("tenant-1", "unknown")
    assert decision_unknown.verdict == PolicyVerdict.DENY


def test_kernel_usage_tracking():
    """Test usage recording"""
    kernel = PolicyKernel()

    kernel.record_usage("tenant-1", "attom", 5)
    kernel.record_usage("tenant-1", "attom", 3)

    assert kernel.cost_tracker["tenant-1"] == 8
    assert kernel.quota_tracker["attom"] == 2

    # Reset
    kernel.reset_daily_trackers()
    assert len(kernel.cost_tracker) == 0
    assert len(kernel.quota_tracker) == 0
