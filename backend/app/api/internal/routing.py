from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

from app.models.routing import ClassificationResult, TaskType, Complexity, Department, ClassifiedBy
from app.routing.risk_analyzer import assess as assess_risk, RiskAssessment, RiskLevel

router = APIRouter()


class SimulateRequest(BaseModel):
    prompt: str = ""
    task_type: str = "general"
    complexity: str = "medium"
    department: str = "rd"
    tenant_id: str = "default"
    risk_level: Optional[str] = None   # override auto-detection if provided
    budget_pct: float = 0.0


@router.post("/routing/policies/reload")
async def reload_policies(request: Request):
    policy_engine = request.app.state.policy_engine
    policy_engine.reload()
    return {"status": "ok", "departments": policy_engine.list_departments()}


@router.get("/routing/policies")
async def list_policies(request: Request):
    policy_engine = request.app.state.policy_engine
    virtual = getattr(request.app.state, "virtual_registry", None)
    departments = policy_engine.list_departments()
    result = {}
    for dept in departments:
        policy = policy_engine.get_policy(dept)
        if policy:
            result[dept] = {
                "tenant_id": policy.tenant_id,
                "department": policy.department,
                "version": policy.version,
                "description": policy.description,
                "rule_count": len(policy.rules),
                "rules": [
                    {
                        "name": r.name,
                        "task_type": r.task_type,
                        "complexity": r.complexity,
                        # Show both the virtual ID and the resolved real model
                        "virtual_model": r.primary_model if virtual and virtual.is_virtual(r.primary_model) else None,
                        "primary_model": virtual.resolve(r.primary_model)[0] if virtual and virtual.is_virtual(r.primary_model) else r.primary_model,
                        "provider": virtual.resolve(r.primary_model)[1] if virtual and virtual.is_virtual(r.primary_model) else r.provider,
                        "model_tier": r.model_tier,
                        "rationale": r.rationale,
                    }
                    for r in policy.rules
                ],
            }

    # Include tenant-scoped policies explicitly for governance inspection.
    tenant_policies = getattr(policy_engine, "_tenant_policies", {})
    for (tenant_id, dept), policy in tenant_policies.items():
        key = f"{tenant_id}:{dept}"
        result[key] = {
            "tenant_id": policy.tenant_id,
            "department": policy.department,
            "version": policy.version,
            "description": policy.description,
            "rule_count": len(policy.rules),
            "rules": [
                {
                    "name": r.name,
                    "task_type": r.task_type,
                    "complexity": r.complexity,
                    "virtual_model": r.primary_model if virtual and virtual.is_virtual(r.primary_model) else None,
                    "primary_model": virtual.resolve(r.primary_model)[0] if virtual and virtual.is_virtual(r.primary_model) else r.primary_model,
                    "provider": virtual.resolve(r.primary_model)[1] if virtual and virtual.is_virtual(r.primary_model) else r.provider,
                    "model_tier": r.model_tier,
                    "rationale": r.rationale,
                }
                for r in policy.rules
            ],
        }
    return result


@router.post("/routing/simulate")
async def simulate_routing(body: SimulateRequest, request: Request):
    """
    Simulate the routing decision for a given classification without calling any LLM.
    Returns the matched rule, resolved model, policy trace, and constraints applied.
    """
    policy_engine = request.app.state.policy_engine

    # Build a mock ClassificationResult from the provided inputs
    try:
        task_type = TaskType(body.task_type)
    except ValueError:
        task_type = TaskType.GENERAL

    try:
        complexity = Complexity(body.complexity)
    except ValueError:
        complexity = Complexity.MEDIUM

    try:
        department = Department(body.department)
    except ValueError:
        department = Department.GENERAL

    classification = ClassificationResult(
        task_type=task_type,
        complexity=complexity,
        department=department,
        required_capability=[],
        confidence=1.0,
        routing_rationale="Simulated — no LLM called",
        classified_by=ClassifiedBy.HEURISTIC_FALLBACK,
    )

    # Build risk assessment — either from override or auto-detect from prompt
    if body.risk_level:
        try:
            risk_level = RiskLevel(body.risk_level)
        except ValueError:
            risk_level = RiskLevel.LOW
        from app.routing.risk_analyzer import RiskAssessment
        risk = RiskAssessment(
            risk_level=risk_level,
            direct_commercial_forbidden=risk_level in (RiskLevel.HIGH, RiskLevel.REGULATED),
            oss_forbidden=False,
            required_min_tier="balanced" if risk_level in (RiskLevel.HIGH, RiskLevel.REGULATED) else "fast_cheap",
            audit_required=risk_level in (RiskLevel.HIGH, RiskLevel.REGULATED),
            rationale=f"Manual override: {risk_level.value}",
        )
    elif body.prompt:
        from app.models.request import ChatCompletionRequest, ChatMessage
        mock_request = ChatCompletionRequest(
            model="auto",
            messages=[ChatMessage(role="user", content=body.prompt)],
        )
        risk = assess_risk(mock_request)
    else:
        from app.routing.risk_analyzer import RiskAssessment
        risk = RiskAssessment(risk_level=RiskLevel.LOW, rationale="No prompt provided")

    # Run the policy engine (no LLM call)
    rule, trace, constraints = policy_engine.match(
        classification,
        risk=risk,
        budget_pct=body.budget_pct,
        tenant_id=body.tenant_id,
    )

    return {
        "input": {
            "tenant_id": body.tenant_id,
            "task_type": task_type.value,
            "complexity": complexity.value,
            "department": department.value,
            "budget_pct": body.budget_pct,
        },
        "risk": {
            "level": risk.risk_level.value,
            "rationale": risk.rationale,
            "direct_commercial_forbidden": risk.direct_commercial_forbidden,
            "audit_required": risk.audit_required,
        },
        "result": {
            "rule_matched": rule.name,
            "primary_model": rule.primary_model,
            "provider": rule.provider,
            "model_tier": rule.model_tier,
            "fallback_models": rule.fallback_models,
            "rationale": rule.rationale,
        },
        "policy_trace": [
            {"rule": t.rule, "result": t.result, "reason": t.reason}
            for t in trace
        ],
        "constraints_applied": constraints,
    }
