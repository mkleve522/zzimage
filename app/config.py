"""
配置管理模块
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/zzimage.db")

# 服务配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# 管理员认证配置
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# 热重载（仅开发环境建议开启）
RELOAD = os.getenv("RELOAD", "false").lower() in {"1", "true", "t", "yes", "on"}

# 图片尺寸限制
MAX_IMAGE_SIZE = 2048
MIN_IMAGE_SIZE = 256

# 预设尺寸比例
PRESET_SIZES = {
    "1:1": [(512, 512), (1024, 1024)],
    "4:3": [(512, 384), (1024, 768)],
    "3:4": [(384, 512), (768, 1024)],
    "16:9": [(512, 288), (1024, 576), (1920, 1080)],
    "9:16": [(288, 512), (576, 1024), (1080, 1920)],
    "3:2": [(512, 341), (1024, 683)],
    "2:3": [(341, 512), (683, 1024)],
}

# API密钥配置（用于OpenAI兼容接口的认证）
API_KEYS_FILE = os.getenv("API_KEYS_FILE", str(BASE_DIR / "data" / "api_keys.json"))

# 请求超时配置
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 120))

# 重试配置
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", 1.0))

# 每日额度配置（每个Cookie每天可用次数）
DAILY_QUOTA = int(os.getenv("DAILY_QUOTA", 100))
