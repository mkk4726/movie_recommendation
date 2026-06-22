"""
Startup readiness middleware.
Returns 503 Service Unavailable with Retry-After while models are loading.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.app_state import is_loading

_BYPASS_PREFIXES = ("/health", "/static")
_BYPASS_EXACT = ("/",)


class StartupReadinessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if is_loading():
            path = request.url.path
            if path not in _BYPASS_EXACT and not any(path.startswith(p) for p in _BYPASS_PREFIXES):
                return JSONResponse(
                    status_code=503,
                    content={"detail": "서비스 준비 중입니다. 잠시 후 다시 시도해주세요."},
                    headers={"Retry-After": "60"},
                )
        return await call_next(request)
