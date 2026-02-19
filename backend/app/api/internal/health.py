from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    provider_registry = request.app.state.provider_registry
    provider_status = await provider_registry.health_check_all()
    all_ok = all(provider_status.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "providers": provider_status,
    }


@router.get("/ready")
async def ready():
    return {"status": "ready"}
