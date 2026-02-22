from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/auth/context")
async def auth_context(request: Request):
    """
    Debug endpoint for validating middleware-auth resolution in UI.
    Requires auth (not excluded path).
    """
    return {
        "user_id": getattr(request.state, "user_id", "unknown"),
        "tenant_id": getattr(request.state, "tenant_id", "unknown"),
        "department": getattr(request.state, "department", "rd"),
    }
