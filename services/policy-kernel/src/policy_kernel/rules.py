"""
Rule engine for policy evaluation
Composable rules with allow/deny/warn verdicts
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class RuleResult(str, Enum):
    """Rule evaluation result"""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


class RuleContext(BaseModel):
    """
    Context for rule evaluation.

    Contains all information needed for policy decisions:
    - Tenant ID (for quota tracking)
    - Action being evaluated
    - Resource being accessed
    - Current usage stats
    """

    tenant_id: str = Field(..., description="Tenant identifier")
    action: str = Field(..., description="Action being evaluated (e.g., 'enrichment.fetch')")
    resource: str = Field(..., description="Resource identifier (e.g., provider name)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class Rule(ABC):
    """
    Base class for policy rules.

    Rules are composable and evaluated in order.
    First DENY wins; all ALLOW required to proceed.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate(self, context: RuleContext) -> tuple[RuleResult, str]:
        """
        Evaluate rule against context.

        Returns:
            (result, reason) tuple
        """
        pass


class CostCapRule(Rule):
    """Enforce daily cost cap per tenant"""

    def __init__(self, daily_cap_cents: int, usage_tracker: dict[str, int]):
        super().__init__("cost_cap")
        self.daily_cap_cents = daily_cap_cents
        self.usage_tracker = usage_tracker  # tenant_id -> cents_spent_today

    def evaluate(self, context: RuleContext) -> tuple[RuleResult, str]:
        spent = self.usage_tracker.get(context.tenant_id, 0)
        cost = context.metadata.get("cost_cents", 0)

        if spent + cost > self.daily_cap_cents:
            return (
                RuleResult.DENY,
                f"Daily cost cap exceeded: {spent + cost} > {self.daily_cap_cents} cents"
            )

        if spent + cost > self.daily_cap_cents * 0.8:
            return (
                RuleResult.WARN,
                f"Approaching daily cap: {spent + cost}/{self.daily_cap_cents} cents (80%)"
            )

        return RuleResult.ALLOW, "Within budget"


class QuotaRule(Rule):
    """Enforce daily quota per provider"""

    def __init__(self, daily_quota: int, usage_tracker: dict[str, int]):
        super().__init__("quota")
        self.daily_quota = daily_quota
        self.usage_tracker = usage_tracker  # resource -> calls_today

    def evaluate(self, context: RuleContext) -> tuple[RuleResult, str]:
        used = self.usage_tracker.get(context.resource, 0)

        if used >= self.daily_quota:
            return (
                RuleResult.DENY,
                f"Daily quota exceeded for {context.resource}: {used}/{self.daily_quota}"
            )

        if used >= self.daily_quota * 0.9:
            return (
                RuleResult.WARN,
                f"Quota warning for {context.resource}: {used}/{self.daily_quota} (90%)"
            )

        return RuleResult.ALLOW, "Within quota"


class AllowListRule(Rule):
    """Allow only specific resources"""

    def __init__(self, allowed: set[str]):
        super().__init__("allow_list")
        self.allowed = allowed

    def evaluate(self, context: RuleContext) -> tuple[RuleResult, str]:
        if context.resource in self.allowed:
            return RuleResult.ALLOW, f"{context.resource} is allowed"
        return RuleResult.DENY, f"{context.resource} not in allow list"


class DenyListRule(Rule):
    """Deny specific resources"""

    def __init__(self, denied: set[str]):
        super().__init__("deny_list")
        self.denied = denied

    def evaluate(self, context: RuleContext) -> tuple[RuleResult, str]:
        if context.resource in self.denied:
            return RuleResult.DENY, f"{context.resource} is denied"
        return RuleResult.ALLOW, f"{context.resource} not in deny list"
