from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/routing/policies/reload")
async def reload_policies(request: Request):
    policy_engine = request.app.state.policy_engine
    policy_engine.reload()
    return {"status": "ok", "departments": policy_engine.list_departments()}


@router.get("/routing/policies")
async def list_policies(request: Request):
    policy_engine = request.app.state.policy_engine
    departments = policy_engine.list_departments()
    result = {}
    for dept in departments:
        policy = policy_engine.get_policy(dept)
        if policy:
            result[dept] = {
                "department": policy.department,
                "version": policy.version,
                "description": policy.description,
                "rule_count": len(policy.rules),
                "rules": [
                    {
                        "name": r.name,
                        "task_type": r.task_type,
                        "complexity": r.complexity,
                        "primary_model": r.primary_model,
                        "provider": r.provider,
                        "model_tier": r.model_tier,
                        "rationale": r.rationale,
                    }
                    for r in policy.rules
                ],
            }
    return result
