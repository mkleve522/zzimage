"""
Cookie池管理服务 - 支持轮询调度和每日额度管理
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.database import db, Cookie
from app.config import DAILY_QUOTA

logger = logging.getLogger(__name__)


class CookiePool:
    """Cookie池管理器 - 实现轮询调度"""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._current_index = 0
        self._cookies_cache: List[Cookie] = []
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 30  # 缓存30秒
    
    async def _refresh_cache(self, force: bool = False):
        """刷新Cookie缓存"""
        now = datetime.now()
        if force or self._cache_time is None or \
           (now - self._cache_time).total_seconds() > self._cache_ttl:
            self._cookies_cache = db.get_all_cookies(active_only=True)
            self._cache_time = now
            # 重置索引如果超出范围
            if self._current_index >= len(self._cookies_cache):
                self._current_index = 0
    
    async def get_next_cookie(self) -> Optional[Cookie]:
        """
        获取下一个可用Cookie（轮询调度，考虑每日额度）
        
        Returns:
            Cookie对象，如果没有可用Cookie则返回None
        """
        async with self._lock:
            await self._refresh_cache()
            
            if not self._cookies_cache:
                logger.warning("没有可用的Cookie")
                return None
            
            # 尝试找到一个有剩余额度的Cookie
            attempts = 0
            max_attempts = len(self._cookies_cache)
            
            while attempts < max_attempts:
                cookie = self._cookies_cache[self._current_index]
                self._current_index = (self._current_index + 1) % len(self._cookies_cache)
                
                # 检查每日额度
                daily_used = db.get_cookie_daily_usage(cookie.id)
                if daily_used < DAILY_QUOTA:
                    logger.info(f"分配Cookie: {cookie.name} (ID: {cookie.id}, 今日已用: {daily_used}/{DAILY_QUOTA})")
                    return cookie
                else:
                    logger.warning(f"Cookie {cookie.name} 今日额度已用完 ({daily_used}/{DAILY_QUOTA})")
                
                attempts += 1
            
            logger.error("所有Cookie今日额度已用完")
            return None
    
    def get_cookie_remaining_quota(self, cookie_id: int) -> int:
        """获取Cookie剩余额度"""
        daily_used = db.get_cookie_daily_usage(cookie_id)
        return max(0, DAILY_QUOTA - daily_used)
    
    async def mark_cookie_used(self, cookie_id: int, success: bool = True):
        """
        标记Cookie使用状态
        
        Args:
            cookie_id: Cookie ID
            success: 是否成功使用
        """
        db.update_cookie_usage(cookie_id, success)
        
        if not success:
            # 如果失败次数过多，可以考虑自动禁用
            cookie = db.get_cookie(cookie_id)
            if cookie and cookie.error_count >= 10:
                logger.warning(f"Cookie {cookie.name} 错误次数过多，建议检查")
        
        # 强制刷新缓存
        await self._refresh_cache(force=True)
    
    async def get_cookie_stats(self) -> dict:
        """获取Cookie池统计信息"""
        await self._refresh_cache()
        
        all_cookies = db.get_all_cookies()
        active_cookies = [c for c in all_cookies if c.is_active]
        
        total_uses = sum(c.use_count for c in all_cookies)
        total_errors = sum(c.error_count for c in all_cookies)
        
        return {
            "total": len(all_cookies),
            "active": len(active_cookies),
            "inactive": len(all_cookies) - len(active_cookies),
            "total_uses": total_uses,
            "total_errors": total_errors,
            "error_rate": total_errors / total_uses if total_uses > 0 else 0
        }
    
    def add_cookie(self, name: str, cookie_value: str,
                   socks5_proxy: Optional[str] = None) -> int:
        """
        添加新Cookie
        
        Args:
            name: Cookie名称
            cookie_value: API Token (Bearer Token)
            socks5_proxy: SOCKS5代理地址（可选）
            
        Returns:
            新Cookie的ID
        """
        cookie = Cookie(
            name=name,
            cookie_value=cookie_value,
            socks5_proxy=socks5_proxy,
            is_active=True
        )
        cookie_id = db.add_cookie(cookie)
        logger.info(f"添加Cookie: {name} (ID: {cookie_id})")
        return cookie_id
    
    def update_cookie(self, cookie_id: int, name: Optional[str] = None,
                      cookie_value: Optional[str] = None,
                      socks5_proxy: Optional[str] = None,
                      is_active: Optional[bool] = None) -> bool:
        """
        更新Cookie
        
        Args:
            cookie_id: Cookie ID
            name: 新名称（可选）
            cookie_value: 新API Token（可选）
            socks5_proxy: 新代理地址（可选）
            is_active: 是否激活（可选）
            
        Returns:
            是否更新成功
        """
        cookie = db.get_cookie(cookie_id)
        if not cookie:
            return False
        
        if name is not None:
            cookie.name = name
        if cookie_value is not None:
            cookie.cookie_value = cookie_value
        if socks5_proxy is not None:
            cookie.socks5_proxy = socks5_proxy
        if is_active is not None:
            cookie.is_active = is_active
        
        return db.update_cookie(cookie)
    
    def delete_cookie(self, cookie_id: int) -> bool:
        """删除Cookie"""
        return db.delete_cookie(cookie_id)
    
    def get_all_cookies(self) -> List[Cookie]:
        """获取所有Cookie"""
        return db.get_all_cookies()
    
    def get_cookie(self, cookie_id: int) -> Optional[Cookie]:
        """获取单个Cookie"""
        return db.get_cookie(cookie_id)


# 全局Cookie池实例
cookie_pool = CookiePool()