"""
FastAPI主应用入口
"""
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import BASE_DIR
from app.routers import generate_router, openai_router, cookies_router
from app.routers.auth import router as auth_router, verify_session
from app.routers.models import router as models_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="ZZImage - 文生图服务",
    description="""
## 功能特性

- 🎨 **文生图**: 通过提示词生成图片
- 🔄 **Cookie池轮询**: 支持多Cookie负载均衡
- 🌐 **SOCKS5代理**: 每个Cookie可配置独立代理
- 🔌 **OpenAI兼容**: 提供标准OpenAI格式接口

## 接口说明

### 图片生成
- `POST /api/generate/` - 生成图片
- `GET /api/generate/presets` - 获取预设尺寸

### OpenAI兼容接口
- `POST /v1/images/generations` - OpenAI格式图片生成
- `GET /v1/models` - 列出模型

### 管理接口
- `GET/POST/PUT/DELETE /api/cookies` - Cookie管理
- `GET/POST/DELETE /api/keys` - API密钥管理
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(generate_router)
app.include_router(openai_router)
app.include_router(cookies_router)
app.include_router(models_router)

# 静态文件目录
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def root(request: Request):
    """返回前端页面，未登录则重定向到登录页"""
    # 检查是否已登录
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "ZZImage API",
        "version": __version__,
        "docs": "/docs"
    }


@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    """返回登录页面，已登录则重定向到主页"""
    # 检查是否已登录
    if verify_session(request):
        return RedirectResponse(url="/", status_code=302)
    
    login_file = static_dir / "login.html"
    if login_file.exists():
        return FileResponse(str(login_file))
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "version": __version__}


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"ZZImage v{__version__} 启动中...")
    
    # 确保数据目录存在
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 确保静态文件目录存在
    static_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("应用启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("应用正在关闭...")