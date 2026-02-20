from fastapi import Request
from fastapi.responses import JSONResponse


class RoutingBrainError(Exception):
    """Base exception for all RoutingBrain errors."""
    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AuthenticationError(RoutingBrainError):
    status_code = 401
    error_code = "authentication_error"


class RateLimitError(RoutingBrainError):
    status_code = 429
    error_code = "rate_limit_exceeded"


class ProviderError(RoutingBrainError):
    status_code = 502
    error_code = "provider_error"

    def __init__(self, message: str, provider: str, original_status: int = 0):
        self.provider = provider
        self.original_status = original_status
        super().__init__(message)


class RoutingError(RoutingBrainError):
    status_code = 451   # 451 = Unavailable For Legal Reasons — appropriate for governance blocks
    error_code = "routing_error"

    def __init__(self, message: str, governance_blocked: bool = False):
        self.governance_blocked = governance_blocked
        super().__init__(message)


class PolicyNotFoundError(RoutingBrainError):
    status_code = 404
    error_code = "policy_not_found"


class BudgetExceededError(RoutingBrainError):
    status_code = 429
    error_code = "budget_exceeded"


async def routing_brain_exception_handler(
    request: Request, exc: RoutingBrainError
) -> JSONResponse:
    content = {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
            "type": type(exc).__name__,
        }
    }
    if isinstance(exc, RoutingError):
        content["error"]["governance_blocked"] = exc.governance_blocked
    return JSONResponse(status_code=exc.status_code, content=content)
