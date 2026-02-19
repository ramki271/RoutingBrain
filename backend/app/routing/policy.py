from pathlib import Path
from typing import Dict, Optional

import yaml

from app.core.logging import get_logger
from app.models.policy import BudgetControls, DepartmentPolicy, RoutingRule
from app.models.routing import ClassificationResult, ModelTier
from app.routing.risk_analyzer import RiskAssessment, RiskLevel, is_provider_allowed

logger = get_logger(__name__)


class PolicyEngine:
    """Loads YAML routing policies and matches ClassificationResult to a RoutingRule."""

    def __init__(self, policies_dir: str):
        self.policies_dir = Path(policies_dir)
        self._policies: Dict[str, DepartmentPolicy] = {}
        self._base_policy: Optional[DepartmentPolicy] = None
        self.load_all()

    def load_all(self) -> None:
        """Load all YAML policy files from the policies directory."""
        if not self.policies_dir.exists():
            logger.warning("policies_dir_missing", path=str(self.policies_dir))
            return

        loaded = 0
        for yaml_file in self.policies_dir.glob("*.yaml"):
            try:
                self._load_file(yaml_file)
                loaded += 1
            except Exception as e:
                logger.error("policy_load_error", file=str(yaml_file), error=str(e))

        logger.info("policies_loaded", count=loaded)

    def _load_file(self, path: Path) -> None:
        with open(path) as f:
            data = yaml.safe_load(f)

        rules = [RoutingRule(**r) for r in data.get("rules", [])]
        budget = BudgetControls(**data.get("budget_controls", {}))
        default_rule = None
        if "default_rule" in data:
            default_rule = RoutingRule(**data["default_rule"])

        policy = DepartmentPolicy(
            department=data["department"],
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            rules=rules,
            budget_controls=budget,
            default_rule=default_rule,
        )

        self._policies[policy.department] = policy
        if path.stem == "base":
            self._base_policy = policy

        logger.info("policy_loaded", department=policy.department, rules=len(rules))

    def reload(self) -> None:
        """Hot-reload all policies without restart."""
        self._policies.clear()
        self._base_policy = None
        self.load_all()
        logger.info("policies_reloaded")

    def match(
        self,
        classification: ClassificationResult,
        risk: Optional[RiskAssessment] = None,
        budget_pct: float = 0.0,
    ) -> RoutingRule:
        """
        Find the best matching rule for a classification.
        Risk assessment is applied FIRST as a hard gate — it can only upgrade
        the minimum tier, never downgrade it below the risk floor.
        Budget guardrails are applied after.
        """
        department = classification.department.value
        policy = self._policies.get(department) or self._base_policy

        if not policy:
            return self._emergency_fallback()

        matched_rule = self._find_rule(policy, classification)

        # ── Risk gate (hard — runs before budget) ──────────────────────────
        if risk and risk.risk_level != RiskLevel.LOW:
            matched_rule = self._enforce_risk_floor(policy, risk, matched_rule)

        # ── Budget guardrails (only if risk allows downgrade) ───────────────
        # Never downgrade below the risk floor tier
        risk_floor = ModelTier(risk.required_min_tier) if risk else ModelTier.FAST_CHEAP
        if budget_pct >= policy.budget_controls.force_cheap_at_percent:
            if self._tier_rank(ModelTier.FAST_CHEAP) >= self._tier_rank(risk_floor):
                matched_rule = self._downgrade_to_tier(policy, ModelTier.FAST_CHEAP, matched_rule)
        elif budget_pct >= policy.budget_controls.downgrade_at_percent:
            candidate = self._downgrade_one_tier(policy, matched_rule)
            # Only apply if it doesn't violate risk floor
            if self._tier_rank(ModelTier(candidate.model_tier)) >= self._tier_rank(risk_floor):
                matched_rule = candidate

        return matched_rule

    def _tier_rank(self, tier: ModelTier) -> int:
        """Higher rank = more powerful. LOCAL is 0, POWERFUL is 3."""
        return {ModelTier.LOCAL: 0, ModelTier.FAST_CHEAP: 1,
                ModelTier.BALANCED: 2, ModelTier.POWERFUL: 3}.get(tier, 1)

    def _enforce_risk_floor(
        self, policy: DepartmentPolicy, risk: RiskAssessment, current: RoutingRule
    ) -> RoutingRule:
        """
        Enforces data residency constraints from the risk assessment.

        Key principle:
          - OSS (self-hosted) is ALWAYS allowed — data never leaves your infra
          - Direct commercial APIs (Anthropic/OpenAI/Gemini) are forbidden for high/regulated
          - Compliant cloud (Bedrock/Azure) is allowed for all risk levels

        If the current rule's provider is forbidden, find the best allowed alternative.
        Also strips forbidden providers from the fallback chain.
        """
        # If primary provider is allowed, just clean the fallback chain
        if is_provider_allowed(current.provider, risk):
            # Strip forbidden providers from fallback chain
            clean_fallbacks = [
                m for m in current.fallback_models
                if is_provider_allowed(self._infer_provider(m), risk)
            ]
            if clean_fallbacks != current.fallback_models:
                current = current.model_copy(update={"fallback_models": clean_fallbacks})
                logger.info(
                    "risk_fallback_chain_filtered",
                    risk_level=risk.risk_level.value,
                    remaining_fallbacks=len(clean_fallbacks),
                )
            return current

        # Primary provider is forbidden — find the best allowed rule
        # Prefer: OSS (free, on-prem) > compliant cloud > skip
        min_tier = ModelTier(risk.required_min_tier)
        candidates = [
            r for r in policy.rules
            if is_provider_allowed(r.provider, risk)
            and self._tier_rank(ModelTier(r.model_tier)) >= self._tier_rank(min_tier)
        ]

        if candidates:
            # Pick cheapest allowed rule that meets quality floor
            upgraded = min(candidates, key=lambda r: self._tier_rank(ModelTier(r.model_tier)))
            logger.info(
                "risk_provider_switch",
                from_provider=current.provider,
                to_provider=upgraded.provider,
                risk_level=risk.risk_level.value,
            )
            current = upgraded

        # Clean fallback chain of forbidden providers
        clean_fallbacks = [
            m for m in current.fallback_models
            if is_provider_allowed(self._infer_provider(m), risk)
        ]
        return current.model_copy(update={"fallback_models": clean_fallbacks})

    def _infer_provider(self, model: str) -> str:
        """Infer provider from model name for fallback chain filtering."""
        if model.startswith("claude"):
            return "anthropic"
        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            return "openai"
        if model.startswith("gemini"):
            return "gemini"
        if any(oss in model.lower() for oss in ["llama", "codellama", "deepseek", "mistral", "phi"]):
            return "ollama"
        return "openai"

    def _find_rule(
        self, policy: DepartmentPolicy, classification: ClassificationResult
    ) -> RoutingRule:
        for rule in policy.rules:
            if rule.task_type and rule.task_type != classification.task_type.value:
                continue
            if rule.complexity and rule.complexity != classification.complexity.value:
                continue
            return rule

        if policy.default_rule:
            return policy.default_rule

        return self._emergency_fallback()

    def _downgrade_one_tier(
        self, policy: DepartmentPolicy, current: RoutingRule
    ) -> RoutingRule:
        tier_order = [ModelTier.POWERFUL, ModelTier.BALANCED, ModelTier.FAST_CHEAP, ModelTier.LOCAL]
        try:
            current_idx = tier_order.index(ModelTier(current.model_tier))
            target_tier = tier_order[min(current_idx + 1, len(tier_order) - 1)]
        except (ValueError, IndexError):
            target_tier = ModelTier.FAST_CHEAP

        return self._downgrade_to_tier(policy, target_tier, current)

    def _downgrade_to_tier(
        self, policy: DepartmentPolicy, target_tier: ModelTier, fallback: RoutingRule
    ) -> RoutingRule:
        for rule in policy.rules:
            if rule.model_tier == target_tier.value:
                logger.info("budget_downgrade_applied", target_tier=target_tier.value)
                return rule
        return fallback

    def _emergency_fallback(self) -> RoutingRule:
        return RoutingRule(
            name="emergency_fallback",
            primary_model="claude-haiku-4-5-20251001",
            provider="anthropic",
            fallback_models=[],
            model_tier=ModelTier.FAST_CHEAP.value,
            rationale="Emergency fallback — no matching policy",
        )

    def get_policy(self, department: str) -> Optional[DepartmentPolicy]:
        return self._policies.get(department)

    def list_departments(self) -> list[str]:
        return list(self._policies.keys())
