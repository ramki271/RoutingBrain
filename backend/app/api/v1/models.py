import time

from fastapi import APIRouter, Request

router = APIRouter()

ROUTABLE_MODELS = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-5-20251101",
    "gpt-4o-mini",
    "gpt-4o",
    "o1",
    "gemini-2.0-flash",
    "gemini-2.0-pro",
    "llama3.1:70b",
    "codellama:34b",
    "deepseek-coder:33b",
    "auto",  # RoutingBrain auto-select
]


@router.get("/models")
async def list_models(request: Request):
    return {
        "object": "list",
        "data": [
            {
                "id": m,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "routing-brain",
            }
            for m in ROUTABLE_MODELS
        ],
    }
