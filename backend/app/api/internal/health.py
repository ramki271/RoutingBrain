from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    provider_registry = request.app.state.provider_registry
    budget_tracker = request.app.state.budget_tracker
    api_key_store = getattr(request.app.state, "api_key_store", None)
    provider_status = await provider_registry.health_check_all()
    redis_ok = await budget_tracker.health_check()
    db_ok = await api_key_store.health_check() if api_key_store else False
    all_ok = all(provider_status.values()) and redis_ok and db_ok
    return {
        "status": "ok" if all_ok else "degraded",
        "providers": provider_status,
        "redis": redis_ok,
        "database": db_ok,
    }


@router.get("/ready")
async def ready():
    return {"status": "ready"}
