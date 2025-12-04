"""
Cookie管理路由
"""
import secrets
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List

from app.database import db, Cookie, ApiKey
from app.services.cookie_pool import cookie_pool
from app.config import DAILY_QUOTA
from app.routers.auth import require_admin

router = APIRouter(prefix="/api", tags=["管理"])


# Cookie相关模型
class CookieCreate(BaseModel):
    """创建Cookie请求"""
    name: str = Field(..., description="Cookie名称", min_length=1, max_length=100)
    cookie_value: str = Field(..., description="API Token (Bearer Token)", min_length=1)
    socks5_proxy: Optional[str] = Field(
        None,
        description="SOCKS5代理地址，格式: socks5://user:pass@host:port"
    )


class CookieUpdate(BaseModel):
    """更新Cookie请求"""
    name: Optional[str] = Field(None, description="Cookie名称", max_length=100)
    cookie_value: Optional[str] = Field(None, description="API Token")
    socks5_proxy: Optional[str] = Field(None, description="SOCKS5代理地址")
    is_active: Optional[bool] = Field(None, description="是否激活")


class CookieResponse(BaseModel):
    """Cookie响应"""
    id: int
    name: str
    cookie_value: str
    socks5_proxy: Optional[str]
    is_active: bool
    use_count: int
    error_count: int
    daily_used: int = 0  # 今日已使用次数
    daily_remaining: int = 100  # 今日剩余额度
    last_used: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class CookieListResponse(BaseModel):
    """Cookie列表响应"""
    cookies: List[CookieResponse]
    total: int


class CookieStatsResponse(BaseModel):
    """Cookie统计响应"""
    total: int
    active: int
    inactive: int
    total_uses: int
    total_errors: int
    error_rate: float


# API密钥相关模型
class ApiKeyCreate(BaseModel):
    """创建API密钥请求"""
    name: str = Field(..., description="密钥名称", min_length=1, max_length=100)


class ApiKeyResponse(BaseModel):
    """API密钥响应"""
    id: int
    key: str
    name: str
    is_active: bool
    created_at: Optional[str]


class ApiKeyListResponse(BaseModel):
    """API密钥列表响应"""
    keys: List[ApiKeyResponse]
    total: int


# Cookie路由
@router.get("/cookies", response_model=CookieListResponse)
async def list_cookies(admin: bool = Depends(require_admin)):
    """获取所有Cookie列表（需要管理员权限）"""
    cookies = cookie_pool.get_all_cookies()
    return CookieListResponse(
        cookies=[CookieResponse(
            id=c.id,
            name=c.name,
            cookie_value=c.cookie_value,
            socks5_proxy=c.socks5_proxy,
            is_active=c.is_active,
            use_count=c.use_count,
            error_count=c.error_count,
            daily_used=c.daily_used,
            daily_remaining=cookie_pool.get_cookie_remaining_quota(c.id),
            last_used=c.last_used,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in cookies],
        total=len(cookies)
    )


@router.post("/cookies", response_model=CookieResponse)
async def create_cookie(request: CookieCreate, admin: bool = Depends(require_admin)):
    """创建新Cookie（需要管理员权限）"""
    cookie_id = cookie_pool.add_cookie(
        name=request.name,
        cookie_value=request.cookie_value,
        socks5_proxy=request.socks5_proxy
    )
    
    cookie = cookie_pool.get_cookie(cookie_id)
    if not cookie:
        raise HTTPException(status_code=500, detail="创建Cookie失败")
    
    return CookieResponse(
        id=cookie.id,
        name=cookie.name,
        cookie_value=cookie.cookie_value,
        socks5_proxy=cookie.socks5_proxy,
        is_active=cookie.is_active,
        use_count=cookie.use_count,
        error_count=cookie.error_count,
        daily_used=cookie.daily_used,
        daily_remaining=cookie_pool.get_cookie_remaining_quota(cookie.id),
        last_used=cookie.last_used,
        created_at=cookie.created_at,
        updated_at=cookie.updated_at
    )


@router.get("/cookies/{cookie_id}", response_model=CookieResponse)
async def get_cookie(cookie_id: int, admin: bool = Depends(require_admin)):
    """获取单个Cookie（需要管理员权限）"""
    cookie = cookie_pool.get_cookie(cookie_id)
    if not cookie:
        raise HTTPException(status_code=404, detail="Cookie不存在")
    
    return CookieResponse(
        id=cookie.id,
        name=cookie.name,
        cookie_value=cookie.cookie_value,
        socks5_proxy=cookie.socks5_proxy,
        is_active=cookie.is_active,
        use_count=cookie.use_count,
        error_count=cookie.error_count,
        daily_used=cookie.daily_used,
        daily_remaining=cookie_pool.get_cookie_remaining_quota(cookie.id),
        last_used=cookie.last_used,
        created_at=cookie.created_at,
        updated_at=cookie.updated_at
    )


@router.put("/cookies/{cookie_id}", response_model=CookieResponse)
async def update_cookie(cookie_id: int, request: CookieUpdate, admin: bool = Depends(require_admin)):
    """更新Cookie（需要管理员权限）"""
    success = cookie_pool.update_cookie(
        cookie_id=cookie_id,
        name=request.name,
        cookie_value=request.cookie_value,
        socks5_proxy=request.socks5_proxy,
        is_active=request.is_active
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Cookie不存在")
    
    cookie = cookie_pool.get_cookie(cookie_id)
    return CookieResponse(
        id=cookie.id,
        name=cookie.name,
        cookie_value=cookie.cookie_value,
        socks5_proxy=cookie.socks5_proxy,
        is_active=cookie.is_active,
        use_count=cookie.use_count,
        error_count=cookie.error_count,
        daily_used=cookie.daily_used,
        daily_remaining=cookie_pool.get_cookie_remaining_quota(cookie.id),
        last_used=cookie.last_used,
        created_at=cookie.created_at,
        updated_at=cookie.updated_at
    )


@router.delete("/cookies/{cookie_id}")
async def delete_cookie(cookie_id: int, admin: bool = Depends(require_admin)):
    """删除Cookie（需要管理员权限）"""
    success = cookie_pool.delete_cookie(cookie_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cookie不存在")
    return {"message": "删除成功"}


@router.get("/cookies/stats/overview", response_model=CookieStatsResponse)
async def get_cookie_stats(admin: bool = Depends(require_admin)):
    """获取Cookie统计信息（需要管理员权限）"""
    stats = await cookie_pool.get_cookie_stats()
    return CookieStatsResponse(**stats)


@router.get("/config/quota")
async def get_quota_config():
    """获取每日额度配置"""
    return {"daily_quota": DAILY_QUOTA}


# API密钥路由
@router.get("/keys", response_model=ApiKeyListResponse)
async def list_api_keys(admin: bool = Depends(require_admin)):
    """获取所有API密钥（需要管理员权限）"""
    keys = db.get_all_api_keys()
    return ApiKeyListResponse(
        keys=[ApiKeyResponse(
            id=k.id,
            key=k.key,
            name=k.name,
            is_active=k.is_active,
            created_at=k.created_at
        ) for k in keys],
        total=len(keys)
    )


@router.post("/keys", response_model=ApiKeyResponse)
async def create_api_key(request: ApiKeyCreate, admin: bool = Depends(require_admin)):
    """创建新API密钥（需要管理员权限）"""
    # 生成随机密钥
    key = f"sk-{secrets.token_urlsafe(32)}"
    
    api_key = ApiKey(
        key=key,
        name=request.name,
        is_active=True
    )
    
    try:
        key_id = db.add_api_key(api_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建失败: {str(e)}")
    
    return ApiKeyResponse(
        id=key_id,
        key=key,
        name=request.name,
        is_active=True,
        created_at=None
    )


@router.delete("/keys/{key_id}")
async def delete_api_key(key_id: int, admin: bool = Depends(require_admin)):
    """删除API密钥（需要管理员权限）"""
    success = db.delete_api_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API密钥不存在")
    return {"message": "删除成功"}