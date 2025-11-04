"""
Policy Kernel - Central decision engine
Evaluates rules and returns verdicts for all policy questions
"""

from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from .rules import Rule, RuleContext, RuleResult
from .providers import ProviderConfig, ProviderTier, DEFAULT_PROVIDERS


class PolicyVerdict(str, Enum):
    """Final policy decision"""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


class PolicyDecision(BaseModel):
    """
    Policy decision result.

    Emitted as: decision.policy.verdict
    """

    decision_id: UUID = Field(default_factory=uuid4, description="Decision ID for audit trail")
    verdict: PolicyVerdict = Field(..., description="Final verdict")
    reasons: list[str] = Field(default_factory=list, description="Evaluation reasons")
    context: RuleContext = Field(..., description="Evaluation context")

    # Metadata
    rules_evaluated: int = Field(default=0, description="Number of rules evaluated")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")


class PolicyKernel:
    """
    Central policy decision engine.

    Responsibilities:
    - Evaluate rules in order (fail-fast on DENY)
    - Track usage for quota/cost enforcement
    - Provide provider priority (hybrid ladder)
    - Emit decision.policy.verdict events
    """

    def __init__(self, providers: list[ProviderConfig] | None = None):
        self.providers = {p.name: p for p in (providers or DEFAULT_PROVIDERS)}
        self.rules: list[Rule] = []

        # Usage trackers (in production, these would be Redis/DB)
        self.cost_tracker: dict[str, int] = {}  # tenant_id -> cents_today
        self.quota_tracker: dict[str, int] = {}  # provider -> calls_today

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the evaluation chain"""
        self.rules.append(rule)

    def evaluate(self, context: RuleContext) -> PolicyDecision:
        """
        Evaluate all rules against context.

        Logic:
        - First DENY → immediate rejection
        - All ALLOW → approval
        - Collect WARNs along the way
        """

        reasons: list[str] = []
        warnings: list[str] = []

        for rule in self.rules:
            result, reason = rule.evaluate(context)

            if result == RuleResult.DENY:
                return PolicyDecision(
                    verdict=PolicyVerdict.DENY,
                    reasons=[reason],
                    context=context,
                    rules_evaluated=len(reasons) + 1
                )

            if result == RuleResult.WARN:
                warnings.append(reason)

            reasons.append(f"{rule.name}: {reason}")

        # All rules passed
        verdict = PolicyVerdict.WARN if warnings else PolicyVerdict.ALLOW

        return PolicyDecision(
            verdict=verdict,
            reasons=reasons,
            context=context,
            rules_evaluated=len(reasons),
            warnings=warnings
        )

    def get_provider_priority(self, field: str) -> list[str]:
        """
        Get providers for a field in priority order (hybrid ladder).

        Returns providers sorted by:
        1. Tier (OPEN > PAID > SCRAPE)
        2. Confidence (within same tier)
        """

        sorted_providers = sorted(
            self.providers.values(),
            key=lambda p: (
                # Tier priority (lower ordinal = higher priority)
                list(ProviderTier).index(p.tier),
                # Confidence (higher is better, so negate)
                -p.confidence
            )
        )

        return [p.name for p in sorted_providers]

    def get_provider(self, name: str) -> ProviderConfig | None:
        """Get provider configuration by name"""
        return self.providers.get(name)

    def can_use_provider(
        self,
        tenant_id: str,
        provider_name: str,
        cost_cents: int = 0
    ) -> PolicyDecision:
        """
        Check if tenant can use a provider.

        Evaluates:
        - Cost cap
        - Quota limits
        - Provider availability
        """

        provider = self.get_provider(provider_name)
        if not provider:
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                reasons=[f"Provider {provider_name} not found"],
                context=RuleContext(
                    tenant_id=tenant_id,
                    action="provider.check",
                    resource=provider_name
                )
            )

        context = RuleContext(
            tenant_id=tenant_id,
            action="provider.check",
            resource=provider_name,
            metadata={"cost_cents": cost_cents or provider.cost_per_call_cents}
        )

        return self.evaluate(context)

    def record_usage(self, tenant_id: str, provider_name: str, cost_cents: int) -> None:
        """Record provider usage for quota/cost tracking"""
        self.cost_tracker[tenant_id] = self.cost_tracker.get(tenant_id, 0) + cost_cents
        self.quota_tracker[provider_name] = self.quota_tracker.get(provider_name, 0) + 1

    def reset_daily_trackers(self) -> None:
        """Reset daily usage trackers (call at midnight)"""
        self.cost_tracker.clear()
        self.quota_tracker.clear()
