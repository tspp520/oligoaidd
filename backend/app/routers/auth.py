"""认证路由：LDAP 域账号登录、Token 校验、登出。"""

from typing import Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.config import settings
from app.services.auth_service import ldap_authenticator, create_token, verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    display_name: str
    department: str
    email: str


class LoginResponse(BaseModel):
    success: bool
    code: Optional[str] = None
    message: str
    token: Optional[str] = None
    user: Optional[UserInfo] = None
    attempts_left: Optional[int] = None
    locked_until: Optional[float] = None


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    if not settings.AUTH_ENABLED:
        # 认证禁用时直接放行（开发/调试）
        user_info = {
            "username": req.username,
            "display_name": req.username,
            "department": "dev",
            "email": f"{req.username}@dev.local",
        }
        token = create_token(user_info)
        return LoginResponse(success=True, code="LOGIN_SUCCESS", message="Login successful",
                             token=token, user=UserInfo(**user_info))

    success, error, user_info = await ldap_authenticator.authenticate(req.username, req.password)
    if not success:
        resp = LoginResponse(success=False, code=error, message=error)
        if isinstance(user_info, dict):
            resp.attempts_left = user_info.get("attempts_left")
            resp.locked_until = user_info.get("locked_until")
        return resp

    assert user_info is not None  # success 时必有用户信息
    token = create_token(user_info)
    return LoginResponse(success=True, code="LOGIN_SUCCESS", message="Login successful",
                         token=token, user=UserInfo(**user_info))


@router.get("/verify")
async def verify(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"authenticated": False}
    payload = verify_token(authorization.split(" ", 1)[1])
    if not payload:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user": {
            "username": payload.get("sub", ""),
            "display_name": payload.get("display_name", ""),
            "department": payload.get("department", ""),
            "email": payload.get("email", ""),
        },
    }


@router.post("/logout")
async def logout():
    return {"success": True, "code": "LOGOUT_SUCCESS", "message": "Logged out"}
