import time
import uuid
from typing import AsyncGenerator, Tuple, Union

from app.core.exceptions import ProviderError, RoutingError
from app.core.logging import get_logger
from app.models.request import ChatCompletionRequest
from app.models.response import ChatCompletionResponse
from app.models.routing import (
    ClassificationResult,
    PreAnalysis,
    RoutingDecision,
    RoutingOutcome,
)
from app.providers.registry import ProviderRegistry
from app.routing import analyzer
from app.routing.policy import PolicyEngine
from app.routing.risk_analyzer import RiskAssessment, assess as assess_risk
from app.routing.routing_brain import RoutingBrain

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
    ):
        self.routing_brain = routing_brain
        self.policy_engine = policy_engine
        self.provider_registry = provider_registry

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
        # TODO: pass actual budget_pct from Redis in Phase 3
        budget_pct = 0.0
        rule = self.policy_engine.match(classification, risk=risk, budget_pct=budget_pct)

        routing_decision = RoutingDecision(
            primary_model=rule.primary_model,
            provider=rule.provider,
            fallback_models=rule.fallback_models,
            model_tier=rule.model_tier,
            cost_budget_applied=budget_pct > 0,
            policy_name=f"{classification.department.value}",
            rule_matched=rule.name,
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
                    outcome = RoutingOutcome(
                        request_id=request_id,
                        actual_model_used=actual_model,
                        actual_provider=actual_provider_name,
                        pre_analysis=pre_analysis,
                        classification=classification,
                        routing_decision=routing_decision,
                        risk_level=risk.risk_level.value,
                        risk_rationale=risk.rationale,
                        data_residency_note=risk.data_residency_note,
                        audit_required=risk.audit_required,
                        latency_ms=latency_ms,
                        fallback_used=fallback_used,
                    )
                    return stream_gen, outcome

                else:
                    response = await provider.chat_completion(request, model)
                    latency_ms = int(time.time() * 1000) - start_ms
                    outcome = RoutingOutcome(
                        request_id=request_id,
                        actual_model_used=actual_model,
                        actual_provider=actual_provider_name,
                        pre_analysis=pre_analysis,
                        classification=classification,
                        routing_decision=routing_decision,
                        risk_level=risk.risk_level.value,
                        risk_rationale=risk.rationale,
                        data_residency_note=risk.data_residency_note,
                        audit_required=risk.audit_required,
                        prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                        completion_tokens=response.usage.completion_tokens if response.usage else 0,
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

        raise RoutingError(
            f"All providers failed. Last error: {last_error}"
        )

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
