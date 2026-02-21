from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from typing import Optional

EXCLUDED_PATHS = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        valid_api_keys: list[str],
        api_key_metadata: Optional[dict] = None,
        dev_mode: bool = False,
    ):
        super().__init__(app)
        self.valid_api_keys = set(valid_api_keys)
        self.api_key_metadata = api_key_metadata or {}
        self.dev_mode = dev_mode

    async def dispatch(self, request: Request, call_next) -> Response:
        # Always pass OPTIONS through — CORS preflight must not be blocked by auth
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # In dev mode, allow requests without auth
        if self.dev_mode and not self.valid_api_keys:
            request.state.user_id = "dev-user"
            request.state.tenant_id = "dev-tenant"
            request.state.department = request.headers.get("X-Department", "rd")
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        api_key = None

        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:].strip()
        elif "api-key" in request.headers:
            api_key = request.headers["api-key"].strip()

        if not api_key or api_key not in self.valid_api_keys:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "authentication_error", "message": "Invalid or missing API key"}},
            )

        meta = self.api_key_metadata.get(api_key, {})

        request.state.user_id = request.headers.get("X-User-Id", meta.get("user_id", "unknown"))

        # Tenant is pinned by API key metadata when configured.
        if "tenant_id" in meta:
            request.state.tenant_id = meta["tenant_id"]
        else:
            request.state.tenant_id = request.headers.get("X-Tenant-Id", "default")

        default_department = meta.get("department", "rd")
        requested_department = request.headers.get("X-Department", default_department)
        allowed_departments = meta.get("allowed_departments")

        if isinstance(allowed_departments, list) and allowed_departments:
            if requested_department not in allowed_departments:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "department_not_allowed",
                            "message": (
                                f"Department '{requested_department}' is not allowed for this API key. "
                                f"Allowed: {', '.join(allowed_departments)}"
                            ),
                        }
                    },
                )
        request.state.department = requested_department

        return await call_next(request)
