"""
认证路由 - 使用数据库持久化session
"""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel

from app.config import ADMIN_USERNAME, ADMIN_PASSWORD
from app import database as db

router = APIRouter(prefix="/api/auth", tags=["认证"])

SESSION_EXPIRE_HOURS = 24 * 7  # 7天有效期


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    message: str


def generate_session_token() -> str:
    """生成会话token"""
    return secrets.token_urlsafe(32)


def verify_session(request: Request) -> bool:
    """验证会话"""
    token = request.cookies.get("session_token")
    if not token:
        return False
    
    session = db.get_session(token)
    if not session:
        return False
    
    # 检查是否过期
    expires = datetime.fromisoformat(session["expires"])
    if datetime.now() > expires:
        db.delete_session(token)
        return False
    
    return True


def require_admin(request: Request):
    """管理员权限依赖"""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="未登录或会话已过期")
    return True


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """管理员登录"""
    if request.username == ADMIN_USERNAME and request.password == ADMIN_PASSWORD:
        # 生成会话token
        token = generate_session_token()
        expires = datetime.now() + timedelta(hours=SESSION_EXPIRE_HOURS)
        
        # 保存到数据库
        db.save_session(token, request.username, expires.isoformat())
        
        # 设置cookie
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            max_age=SESSION_EXPIRE_HOURS * 3600,
            samesite="lax"
        )
        
        return LoginResponse(success=True, message="登录成功")
    else:
        raise HTTPException(status_code=401, detail="用户名或密码错误")


@router.post("/logout")
async def logout(request: Request, response: Response):
    """退出登录"""
    token = request.cookies.get("session_token")
    if token:
        db.delete_session(token)
    
    response.delete_cookie("session_token")
    return {"success": True, "message": "已退出登录"}


@router.get("/status")
async def check_auth(request: Request):
    """检查登录状态"""
    is_logged_in = verify_session(request)
    return {"authenticated": is_logged_in}