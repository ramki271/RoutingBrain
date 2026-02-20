import asyncio
import orjson
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.logging import get_logger
from app.models.request import ChatCompletionRequest
from app.models.routing import RoutingOutcome
from app.observability.audit_log import AuditLogger
from app.routing.engine import RoutingEngine

logger = get_logger(__name__)
router = APIRouter()


def get_routing_engine(request: Request) -> RoutingEngine:
    return request.app.state.routing_engine


def get_audit_logger(request: Request) -> AuditLogger:
    return request.app.state.audit_logger


def _routing_decision_payload(outcome: RoutingOutcome) -> dict:
    payload = {
        # Identity (§4.1)
        "request_id": outcome.request_id,
        "tenant_id": outcome.tenant_id,
        "user_id": outcome.user_id,
        "department": outcome.classification.department.value,
        # Policy version (§4.4)
        "policy_version": outcome.policy_version,
        # Classification
        "task_type": outcome.classification.task_type.value,
        "complexity": outcome.classification.complexity.value,
        "confidence": outcome.classification.confidence,
        "classified_by": outcome.classification.classified_by.value,
        "routing_rationale": outcome.classification.routing_rationale,
        # Routing decision
        "model_selected": outcome.actual_model_used,
        "provider": outcome.actual_provider,
        "model_tier": outcome.routing_decision.model_tier,
        "rule_matched": outcome.routing_decision.rule_matched,
        "fallback_used": outcome.fallback_used,
        "latency_ms": outcome.latency_ms,
        # Risk
        "risk_level": outcome.risk_level,
        "risk_rationale": outcome.risk_rationale,
        "data_residency_note": outcome.data_residency_note,
        "audit_required": outcome.audit_required,
        # Trace
        "policy_trace": [{"rule": t.rule, "result": t.result, "reason": t.reason} for t in outcome.policy_trace],
        "constraints_applied": outcome.constraints_applied,
        # Classification snapshot (§4.5)
        "classification_snapshot": outcome.classification_snapshot.model_dump()
            if outcome.classification_snapshot else None,
    }
    return payload


async def _prepend_routing_event(
    outcome: RoutingOutcome, stream: AsyncGenerator
) -> AsyncGenerator[str, None]:
    """Prepend a routing_decision SSE event before the first token."""
    payload = orjson.dumps({"event": "routing_decision", "data": _routing_decision_payload(outcome)}).decode()
    yield f"event: routing_decision\ndata: {payload}\n\n"
    async for chunk in stream:
        yield chunk


@router.post("/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    engine: RoutingEngine = Depends(get_routing_engine),
    audit: AuditLogger = Depends(get_audit_logger),
):
    # Inject request context from middleware state
    body.x_request_id = getattr(request.state, "request_id", None)
    body.x_user_id = getattr(request.state, "user_id", None)
    body.x_tenant_id = getattr(request.state, "tenant_id", None)
    body.x_department = body.x_department or getattr(request.state, "department", "rd")

    response_or_gen, outcome = await engine.route(body)

    # Audit log — always fires, even on provider failure, as a background task
    audit_record = audit.build_record(
        outcome,
        tenant_id=outcome.tenant_id,
        user_id=outcome.user_id,
        policy_version=outcome.policy_version,
    )
    background_tasks.add_task(audit.log, audit_record)

    if body.stream:
        return StreamingResponse(
            _prepend_routing_event(outcome, response_or_gen),
            media_type="text/event-stream",
            headers={
                "X-Request-Id": outcome.request_id,
                "X-Routing-Model": outcome.actual_model_used,
                "X-Routing-Provider": outcome.actual_provider,
                "X-Task-Type": outcome.classification.task_type.value,
                "X-Complexity": outcome.classification.complexity.value,
                "X-Risk-Level": outcome.risk_level,
                "X-Audit-Required": str(outcome.audit_required).lower(),
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    # Non-streaming — embed full routing metadata in response
    resp_dict = response_or_gen.model_dump(exclude_none=True)
    resp_dict["x_routing_decision"] = _routing_decision_payload(outcome)

    return JSONResponse(
        content=resp_dict,
        headers={
            "X-Request-Id": outcome.request_id,
            "X-Routing-Model": outcome.actual_model_used,
        },
    )
