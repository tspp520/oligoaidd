"""JWT 认证中间件：保护 /api/*，白名单路径放行。"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.services.auth_service import verify_token

AUTH_WHITELIST = [
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/verify",
    "/api/health",
    "/api/modules",
    "/docs",
    "/openapi.json",
    "/redoc",
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # 非 API 请求（前端静态资源等）放行
        if not path.startswith("/api"):
            return await call_next(request)
        # 认证未启用 / OPTIONS 预检 放行
        if not settings.AUTH_ENABLED or method == "OPTIONS":
            return await call_next(request)
        # 白名单放行
        for w in AUTH_WHITELIST:
            if path.startswith(w):
                return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        token = auth_header.split(" ", 1)[1] if auth_header.startswith("Bearer ") else ""
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": {"code": "AUTH_REQUIRED",
                                    "message": "Authentication required, please log in first"}},
            )
        payload = verify_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": {"code": "AUTH_EXPIRED",
                                    "message": "Authentication expired, please log in again"}},
            )
        request.state.user = {
            "username": payload.get("sub", ""),
            "display_name": payload.get("display_name", ""),
        }
        return await call_next(request)
