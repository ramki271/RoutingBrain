from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.logging import get_logger
from app.models.request import ChatCompletionRequest
from app.routing.engine import RoutingEngine

logger = get_logger(__name__)
router = APIRouter()


def get_routing_engine(request: Request) -> RoutingEngine:
    return request.app.state.routing_engine


@router.post("/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    engine: RoutingEngine = Depends(get_routing_engine),
):
    # Inject request context from middleware state
    body.x_request_id = getattr(request.state, "request_id", None)
    body.x_user_id = getattr(request.state, "user_id", None)
    body.x_tenant_id = getattr(request.state, "tenant_id", None)
    body.x_department = body.x_department or getattr(request.state, "department", "rd")

    response_or_gen, outcome = await engine.route(body)

    if body.stream:
        return StreamingResponse(
            response_or_gen,
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

    # Non-streaming — embed routing metadata in response
    resp_dict = response_or_gen.model_dump(exclude_none=True)
    resp_dict["x_routing_decision"] = {
        "request_id": outcome.request_id,
        "task_type": outcome.classification.task_type.value,
        "complexity": outcome.classification.complexity.value,
        "department": outcome.classification.department.value,
        "confidence": outcome.classification.confidence,
        "classified_by": outcome.classification.classified_by.value,
        "routing_rationale": outcome.classification.routing_rationale,
        "model_selected": outcome.actual_model_used,
        "provider": outcome.actual_provider,
        "model_tier": outcome.routing_decision.model_tier,
        "rule_matched": outcome.routing_decision.rule_matched,
        "fallback_used": outcome.fallback_used,
        "latency_ms": outcome.latency_ms,
        "risk_level": outcome.risk_level,
        "risk_rationale": outcome.risk_rationale,
        "data_residency_note": outcome.data_residency_note,
        "audit_required": outcome.audit_required,
    }

    return JSONResponse(
        content=resp_dict,
        headers={
            "X-Request-Id": outcome.request_id,
            "X-Routing-Model": outcome.actual_model_used,
        },
    )
