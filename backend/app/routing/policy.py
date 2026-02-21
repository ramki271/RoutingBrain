from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from app.core.logging import get_logger
from app.models.policy import BudgetControls, DepartmentPolicy, RoutingRule
from app.models.routing import ClassificationResult, ModelTier, PolicyTraceEntry
from app.routing.risk_analyzer import RiskAssessment, RiskLevel, is_provider_allowed
from app.routing.virtual_models import VirtualModelRegistry

logger = get_logger(__name__)


class PolicyEngine:
    """Loads YAML routing policies and matches ClassificationResult to a RoutingRule."""

    def __init__(self, policies_dir: str, virtual_registry: Optional[VirtualModelRegistry] = None):
        self.policies_dir = Path(policies_dir)
        self._policies: Dict[str, DepartmentPolicy] = {}
        self._tenant_policies: Dict[Tuple[str, str], DepartmentPolicy] = {}
        self._base_policy: Optional[DepartmentPolicy] = None
        self._virtual = virtual_registry
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
            tenant_id=data.get("tenant_id"),
            department=data["department"],
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            rules=rules,
            budget_controls=budget,
            default_rule=default_rule,
        )

        if policy.tenant_id:
            self._tenant_policies[(policy.tenant_id, policy.department)] = policy
        else:
            self._policies[policy.department] = policy

        if path.stem == "base" and not policy.tenant_id:
            self._base_policy = policy

        logger.info(
            "policy_loaded",
            tenant_id=policy.tenant_id or "global",
            department=policy.department,
            rules=len(rules),
        )

    def reload(self) -> None:
        """Hot-reload all policies without restart."""
        self._policies.clear()
        self._tenant_policies.clear()
        self._base_policy = None
        self.load_all()
        logger.info("policies_reloaded")

    def match(
        self,
        classification: ClassificationResult,
        risk: Optional[RiskAssessment] = None,
        budget_pct: float = 0.0,
        tenant_id: Optional[str] = None,
    ) -> Tuple[RoutingRule, List[PolicyTraceEntry], List[str]]:
        """
        Find the best matching rule for a classification.
        Returns (rule, policy_trace, constraints_applied).

        Risk gate is applied FIRST as a hard gate.
        Budget guardrails are applied after, respecting risk floor.
        """
        trace: List[PolicyTraceEntry] = []
        constraints: List[str] = []

        department = classification.department.value
        policy = self.get_policy(department, tenant_id=tenant_id) or self._base_policy

        if not policy:
            rule = self._emergency_fallback(risk)
            trace.append(PolicyTraceEntry(rule="emergency_fallback", result="matched", reason="no policy found"))
            return self._resolve_rule(rule), trace, constraints

        if tenant_id and policy.tenant_id == tenant_id:
            trace.append(
                PolicyTraceEntry(
                    rule="tenant_policy_select",
                    result="matched",
                    reason=f"tenant='{tenant_id}' department='{department}'",
                )
            )

        matched_rule, find_trace = self._find_rule_with_trace(policy, classification, risk)
        trace.extend(find_trace)

        # Resolve virtual IDs BEFORE risk gate so provider names are concrete
        matched_rule = self._resolve_rule(matched_rule)

        # ── Risk gate (hard — runs before budget) ──────────────────────────
        if risk and risk.risk_level != RiskLevel.LOW:
            before = matched_rule.name
            matched_rule = self._enforce_risk_floor(policy, risk, matched_rule)
            if matched_rule.name != before:
                trace.append(PolicyTraceEntry(
                    rule=f"risk_gate_{risk.risk_level.value}",
                    result="risk_override",
                    reason=f"provider '{before}' forbidden for {risk.risk_level.value} risk — switched to '{matched_rule.name}'",
                ))
                constraints.append(f"risk_floor_{risk.risk_level.value}")
            else:
                trace.append(PolicyTraceEntry(
                    rule=f"risk_gate_{risk.risk_level.value}",
                    result="matched",
                    reason=f"provider allowed for {risk.risk_level.value} risk",
                ))

        risk_floor = ModelTier(risk.required_min_tier) if risk else ModelTier.FAST_CHEAP

        # ── Static budget cap (MVP): max allowed tier from policy ──────────
        max_tier_value = policy.budget_controls.max_tier
        if max_tier_value:
            try:
                max_tier = ModelTier(max_tier_value)
                current_tier = ModelTier(matched_rule.model_tier)
                if self._tier_rank(current_tier) > self._tier_rank(max_tier):
                    capped = self._downgrade_to_tier(policy, max_tier, matched_rule)
                    # Never violate risk floor while capping for budget
                    if self._tier_rank(ModelTier(capped.model_tier)) >= self._tier_rank(risk_floor):
                        matched_rule = capped
                        trace.append(PolicyTraceEntry(
                            rule="budget_guard_max_tier",
                            result="budget_override",
                            reason=f"static max_tier '{max_tier.value}' enforced",
                        ))
                        constraints.append(f"budget_max_tier_{max_tier.value}")
            except ValueError:
                logger.warning("invalid_budget_max_tier", max_tier=max_tier_value, department=policy.department)

        # ── Budget guardrails ───────────────────────────────────────────────
        if budget_pct >= policy.budget_controls.force_cheap_at_percent:
            if self._tier_rank(ModelTier.FAST_CHEAP) >= self._tier_rank(risk_floor):
                matched_rule = self._downgrade_to_tier(policy, ModelTier.FAST_CHEAP, matched_rule)
                trace.append(PolicyTraceEntry(
                    rule="budget_guard_force_cheap",
                    result="budget_override",
                    reason=f"budget {budget_pct:.0f}% >= force threshold {policy.budget_controls.force_cheap_at_percent:.0f}%",
                ))
                constraints.append("budget_force_cheap")
        elif budget_pct >= policy.budget_controls.downgrade_at_percent:
            candidate = self._downgrade_one_tier(policy, matched_rule)
            if self._tier_rank(ModelTier(candidate.model_tier)) >= self._tier_rank(risk_floor):
                matched_rule = candidate
                trace.append(PolicyTraceEntry(
                    rule="budget_guard_downgrade",
                    result="budget_override",
                    reason=f"budget {budget_pct:.0f}% >= downgrade threshold {policy.budget_controls.downgrade_at_percent:.0f}%",
                ))
                constraints.append("budget_downgrade")

        return matched_rule, trace, constraints

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

        # Primary provider is forbidden — find the best allowed rule.
        # OSS (local tier) is ALWAYS a valid candidate regardless of tier floor —
        # data residency trumps quality tier when commercial APIs are forbidden.
        from app.routing.risk_analyzer import OSS_PROVIDERS
        min_tier = ModelTier(risk.required_min_tier)
        candidates = [
            r for r in policy.rules
            # Include if: meets quality floor OR is OSS (data residency safe regardless of tier)
            if self._tier_rank(ModelTier(r.model_tier)) >= self._tier_rank(min_tier)
            or r.model_tier == ModelTier.LOCAL.value
        ]

        if candidates:
            # Resolve virtual IDs so we can check real provider names
            resolved_candidates = [self._resolve_rule(r) for r in candidates]
            allowed_candidates = [
                r for r in resolved_candidates
                if is_provider_allowed(r.provider, risk)
            ]
            if allowed_candidates:
                upgraded = min(allowed_candidates, key=lambda r: self._tier_rank(ModelTier(r.model_tier)))
                logger.info(
                    "risk_provider_switch",
                    from_provider=current.provider,
                    to_provider=upgraded.provider,
                    risk_level=risk.risk_level.value,
                )
                current = upgraded

        # Clean fallback chain of forbidden providers (fallbacks are already resolved model names)
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
        self, policy: DepartmentPolicy, classification: ClassificationResult,
        risk: Optional[RiskAssessment] = None,
    ) -> RoutingRule:
        rule, _ = self._find_rule_with_trace(policy, classification, risk)
        return rule

    def _find_rule_with_trace(
        self, policy: DepartmentPolicy, classification: ClassificationResult,
        risk: Optional[RiskAssessment] = None,
    ) -> Tuple[RoutingRule, List[PolicyTraceEntry]]:
        trace: List[PolicyTraceEntry] = []
        for rule in policy.rules:
            if rule.task_type and rule.task_type != classification.task_type.value:
                trace.append(PolicyTraceEntry(
                    rule=rule.name, result="skipped",
                    reason=f"task_type '{rule.task_type}' != '{classification.task_type.value}'",
                ))
                continue
            if rule.complexity and rule.complexity != classification.complexity.value:
                trace.append(PolicyTraceEntry(
                    rule=rule.name, result="skipped",
                    reason=f"complexity '{rule.complexity}' != '{classification.complexity.value}'",
                ))
                continue
            trace.append(PolicyTraceEntry(
                rule=rule.name, result="matched",
                reason=f"task={classification.task_type.value} complexity={classification.complexity.value}",
            ))
            return rule, trace

        if policy.default_rule:
            trace.append(PolicyTraceEntry(
                rule=policy.default_rule.name, result="matched",
                reason="no specific rule matched — using department default",
            ))
            return policy.default_rule, trace

        fallback = self._emergency_fallback(risk)
        trace.append(PolicyTraceEntry(rule="emergency_fallback", result="matched", reason="no rules or default"))
        return fallback, trace

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

    def _emergency_fallback(self, risk: Optional[RiskAssessment] = None) -> RoutingRule:
        """
        Safe fallback of last resort.
        If risk forbids direct commercial APIs, fall back to OSS (local) instead.
        Never silently route regulated content to a forbidden provider.
        """
        # If direct commercial is forbidden (high/regulated risk), use OSS
        if risk and risk.direct_commercial_forbidden:
            return RoutingRule(
                name="emergency_fallback_oss",
                primary_model="llama3.1:70b",
                provider="ollama",
                fallback_models=[],
                model_tier=ModelTier.LOCAL.value,
                rationale="Emergency fallback — OSS only (risk level forbids direct commercial APIs)",
            )
        # Default safe fallback — Haiku is cheap and fast
        return RoutingRule(
            name="emergency_fallback",
            primary_model="claude-haiku-4-5-20251001",
            provider="anthropic",
            fallback_models=[],
            model_tier=ModelTier.FAST_CHEAP.value,
            rationale="Emergency fallback — no matching policy",
        )

    def _resolve_rule(self, rule: RoutingRule) -> RoutingRule:
        """Resolve virtual rb:// model IDs to concrete model + provider pairs."""
        if not self._virtual:
            return rule

        primary_model, provider = self._virtual.resolve(rule.primary_model)
        fallback_models = [self._virtual.resolve(m)[0] for m in rule.fallback_models]

        return rule.model_copy(update={
            "primary_model": primary_model,
            "provider": provider,
            "fallback_models": fallback_models,
            # Keep original virtual ID for tracing
            "rationale": rule.rationale,
        })

    def get_policy(self, department: str, tenant_id: Optional[str] = None) -> Optional[DepartmentPolicy]:
        if tenant_id:
            scoped = self._tenant_policies.get((tenant_id, department))
            if scoped:
                return scoped
        return self._policies.get(department)

    def resolve_policy(self, department: str, tenant_id: Optional[str] = None) -> Optional[DepartmentPolicy]:
        """Return tenant-scoped policy if present, else global department policy, else base policy."""
        return self.get_policy(department, tenant_id=tenant_id) or self._base_policy

    def get_policy_version(self, department: str, tenant_id: Optional[str] = None) -> str:
        """Return versioned identifier for the department's policy, e.g. 'rd-v2.0'."""
        policy = self.resolve_policy(department, tenant_id=tenant_id)
        if not policy:
            return "unknown"
        if policy.tenant_id:
            return f"{policy.tenant_id}:{policy.department}-v{policy.version}"
        return f"{policy.department}-v{policy.version}"

    def list_departments(self) -> list[str]:
        departments = set(self._policies.keys())
        departments.update(dept for (_, dept) in self._tenant_policies.keys())
        return sorted(departments)
