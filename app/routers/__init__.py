"""
路由模块
"""
from app.routers.generate import router as generate_router
from app.routers.openai import router as openai_router
from app.routers.cookies import router as cookies_router

__all__ = ["generate_router", "openai_router", "cookies_router"]