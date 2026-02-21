import time
import uuid
from typing import AsyncGenerator, Tuple, Union

from app.core.exceptions import ProviderError, RoutingError
from app.core.logging import get_logger
from app.models.request import ChatCompletionRequest
from app.models.response import ChatCompletionResponse
from app.models.routing import (
    ClassificationResult,
    ClassificationSnapshot,
    PreAnalysis,
    RoutingDecision,
    RoutingOutcome,
)
from app.providers.registry import ProviderRegistry
from app.routing import analyzer
from app.routing.policy import PolicyEngine
from app.routing.risk_analyzer import RiskAssessment, assess as assess_risk
from app.routing.routing_brain import RoutingBrain
from app.storage.budget_tracker import BudgetTracker

logger = get_logger(__name__)


class RoutingEngine:
    """
    Central orchestrator: PreAnalyzer → RiskAnalyzer → RoutingBrain → PolicyEngine → ProviderRegistry
    """

    def __init__(
        self,
        routing_brain: RoutingBrain,
        policy_engine: PolicyEngine,
        provider_registry: ProviderRegistry,
        budget_tracker: BudgetTracker,
    ):
        self.routing_brain = routing_brain
        self.policy_engine = policy_engine
        self.provider_registry = provider_registry
        self.budget_tracker = budget_tracker

    async def route(
        self, request: ChatCompletionRequest
    ) -> Tuple[Union[ChatCompletionResponse, AsyncGenerator], RoutingOutcome]:
        """
        Full routing pipeline. Returns (response_or_generator, outcome).
        """
        request_id = request.x_request_id or f"rb-{uuid.uuid4().hex[:12]}"
        start_ms = int(time.time() * 1000)

        # Step 1 — PreAnalyzer (free, heuristic)
        pre_analysis: PreAnalysis = analyzer.analyze(request)
        logger.info(
            "pre_analysis_complete",
            request_id=request_id,
            tokens=pre_analysis.estimated_tokens,
            task_hint=pre_analysis.heuristic_task_type,
            complexity_hint=pre_analysis.heuristic_complexity,
        )

        # Step 2 — Risk Analyzer (deterministic heuristic gate, free)
        risk: RiskAssessment = assess_risk(request)
        logger.info(
            "risk_assessment",
            request_id=request_id,
            risk_level=risk.risk_level.value,
            oss_forbidden=risk.oss_forbidden,
            audit_required=risk.audit_required,
            rationale=risk.rationale,
        )

        # Step 3 — RoutingBrain (Claude Haiku classifier)
        message_excerpt = " ".join(
            msg.text_content() for msg in request.messages if msg.role == "user"
        )
        classification: ClassificationResult = await self.routing_brain.classify(
            pre_analysis, message_excerpt
        )

        # Step 4 — PolicyEngine (risk floor + YAML rule matching + budget guardrails)
        # Live budget usage from Redis (tenant/user/day).
        selected_policy = self.policy_engine.resolve_policy(
            classification.department.value,
            tenant_id=request.x_tenant_id,
        )
        budget_pct = 0.0
        if selected_policy:
            budget_pct = await self.budget_tracker.get_budget_pct(
                tenant_id=request.x_tenant_id or "unknown",
                user_id=request.x_user_id or "unknown",
                controls=selected_policy.budget_controls,
            )

        rule, policy_trace, constraints_applied = self.policy_engine.match(
            classification,
            risk=risk,
            budget_pct=budget_pct,
            tenant_id=request.x_tenant_id,
        )

        # Governance fields (§4.4, §4.5)
        policy_version = self.policy_engine.get_policy_version(
            classification.department.value,
            tenant_id=request.x_tenant_id,
        )
        risk_signal_categories = [s.category for s in risk.signals]
        classification_snapshot = ClassificationSnapshot(
            task_type=classification.task_type.value,
            complexity=classification.complexity.value,
            confidence=classification.confidence,
            classified_by=classification.classified_by.value,
            department=classification.department.value,
            required_capability=classification.required_capability,
            risk_signals=risk_signal_categories,
        )

        routing_decision = RoutingDecision(
            primary_model=rule.primary_model,
            provider=rule.provider,
            fallback_models=rule.fallback_models,
            model_tier=rule.model_tier,
            cost_budget_applied=budget_pct > 0,
            policy_name=f"{classification.department.value}",
            rule_matched=rule.name,
            virtual_model_id=rule.primary_model if self.policy_engine._virtual and
                             not self.policy_engine._virtual.is_virtual(rule.primary_model)
                             else "",
        )

        logger.info(
            "routing_decision",
            request_id=request_id,
            model=routing_decision.primary_model,
            provider=routing_decision.provider,
            tier=routing_decision.model_tier,
            task_type=classification.task_type.value,
            complexity=classification.complexity.value,
            confidence=classification.confidence,
            risk_level=risk.risk_level.value,
        )

        # Step 4 — Provider call with fallback chain
        models_to_try = [
            (routing_decision.primary_model, routing_decision.provider)
        ] + [
            (m, self._infer_provider(m)) for m in routing_decision.fallback_models
        ]

        last_error = None
        fallback_used = False
        actual_model = routing_decision.primary_model
        actual_provider_name = routing_decision.provider

        for idx, (model, provider_name) in enumerate(models_to_try):
            provider = self.provider_registry.get(provider_name)
            if not provider:
                logger.warning("provider_not_found", provider=provider_name)
                continue

            try:
                if idx > 0:
                    fallback_used = True
                    actual_model = model
                    actual_provider_name = provider_name
                    logger.info("fallback_attempt", model=model, provider=provider_name)

                if request.stream:
                    stream_gen = provider.chat_completion_stream(request, model)
                    latency_ms = int(time.time() * 1000) - start_ms
                    estimated_cost = self.budget_tracker.estimate_cost_usd(
                        model_id=actual_model,
                        prompt_tokens=pre_analysis.estimated_tokens,
                        completion_tokens=0,
                        tier=routing_decision.model_tier.value,
                    )
                    await self.budget_tracker.record_spend(
                        tenant_id=request.x_tenant_id or "unknown",
                        user_id=request.x_user_id or "unknown",
                        amount_usd=estimated_cost,
                    )
                    outcome = RoutingOutcome(
                        request_id=request_id,
                        actual_model_used=actual_model,
                        actual_provider=actual_provider_name,
                        pre_analysis=pre_analysis,
                        classification=classification,
                        routing_decision=routing_decision,
                        tenant_id=request.x_tenant_id or "unknown",
                        user_id=request.x_user_id or "unknown",
                        policy_version=policy_version,
                        risk_level=risk.risk_level.value,
                        risk_rationale=risk.rationale,
                        risk_signals=risk_signal_categories,
                        data_residency_note=risk.data_residency_note,
                        audit_required=risk.audit_required,
                        policy_trace=policy_trace,
                        constraints_applied=constraints_applied,
                        classification_snapshot=classification_snapshot,
                        total_cost_usd=estimated_cost,
                        latency_ms=latency_ms,
                        fallback_used=fallback_used,
                    )
                    return stream_gen, outcome

                else:
                    response = await provider.chat_completion(request, model)
                    latency_ms = int(time.time() * 1000) - start_ms
                    prompt_tokens = response.usage.prompt_tokens if response.usage else pre_analysis.estimated_tokens
                    completion_tokens = response.usage.completion_tokens if response.usage else 0
                    estimated_cost = self.budget_tracker.estimate_cost_usd(
                        model_id=actual_model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        tier=routing_decision.model_tier.value,
                    )
                    await self.budget_tracker.record_spend(
                        tenant_id=request.x_tenant_id or "unknown",
                        user_id=request.x_user_id or "unknown",
                        amount_usd=estimated_cost,
                    )
                    outcome = RoutingOutcome(
                        request_id=request_id,
                        actual_model_used=actual_model,
                        actual_provider=actual_provider_name,
                        pre_analysis=pre_analysis,
                        classification=classification,
                        routing_decision=routing_decision,
                        tenant_id=request.x_tenant_id or "unknown",
                        user_id=request.x_user_id or "unknown",
                        policy_version=policy_version,
                        risk_level=risk.risk_level.value,
                        risk_rationale=risk.rationale,
                        risk_signals=risk_signal_categories,
                        data_residency_note=risk.data_residency_note,
                        audit_required=risk.audit_required,
                        policy_trace=policy_trace,
                        constraints_applied=constraints_applied,
                        classification_snapshot=classification_snapshot,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_cost_usd=estimated_cost,
                        latency_ms=latency_ms,
                        fallback_used=fallback_used,
                    )
                    return response, outcome

            except ProviderError as e:
                last_error = e
                logger.warning(
                    "provider_error_fallback",
                    model=model,
                    provider=provider_name,
                    error=str(e),
                    status=getattr(e, "original_status", 0),
                )
                continue

        # Build a meaningful error message explaining WHY all providers failed
        tried = [m for m, _ in models_to_try]
        if risk.direct_commercial_forbidden:
            msg = (
                f"Governance policy blocked all available providers for this request.\n\n"
                f"Risk level: {risk.risk_level.value.upper()} — {risk.rationale}\n\n"
                f"Direct commercial APIs (Anthropic / OpenAI / Gemini) are forbidden for this content. "
                f"Allowed: self-hosted OSS (Ollama/vLLM) or compliant cloud (AWS Bedrock, Azure AI Foundry with BAA).\n\n"
                f"Models tried: {', '.join(tried)}\n"
                f"To fix: start Ollama locally or add AWS Bedrock / Azure AI Foundry credentials."
            )
            raise RoutingError(msg, governance_blocked=True)
        else:
            msg = (
                f"All providers failed for this request.\n\n"
                f"Models tried: {', '.join(tried)}\n"
                f"Last error: {last_error}\n\n"
                f"Check that API keys are configured in backend/.env."
            )
            raise RoutingError(msg, governance_blocked=False)

    def _infer_provider(self, model: str) -> str:
        """Infer provider from model name prefix."""
        if model.startswith("claude"):
            return "anthropic"
        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            return "openai"
        if model.startswith("gemini"):
            return "gemini"
        if model.startswith("llama") or model.startswith("codellama") or model.startswith("deepseek"):
            return "ollama"
        return "openai"
