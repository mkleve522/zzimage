"""
数据库模型和管理
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from app.config import BASE_DIR


@dataclass
class Cookie:
    """Cookie数据模型"""
    id: Optional[int] = None
    name: str = ""  # 建议使用Gitee用户名
    cookie_value: str = ""  # API Token (Bearer Token)
    socks5_proxy: Optional[str] = None  # 格式: socks5://user:pass@host:port
    is_active: bool = True
    last_used: Optional[str] = None
    use_count: int = 0
    error_count: int = 0
    daily_used: int = 0  # 今日已使用次数
    daily_date: Optional[str] = None  # 今日日期 (YYYY-MM-DD)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApiKey:
    """API密钥数据模型"""
    id: Optional[int] = None
    key: str = ""
    name: str = ""
    is_active: bool = True
    created_at: Optional[str] = None


@dataclass
class GenerationLog:
    """生成日志数据模型"""
    id: Optional[int] = None
    prompt: str = ""
    width: int = 0
    height: int = 0
    cookie_id: Optional[int] = None
    api_key_id: Optional[int] = None
    status: str = ""  # success, failed
    error_message: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class ModelConfig:
    """模型配置数据模型"""
    id: Optional[int] = None
    name: str = ""  # 模型名称，用于OpenAI Chat接口
    width: int = 1024  # 默认宽度
    height: int = 1024  # 默认高度
    steps: int = 9  # 推理步数
    description: Optional[str] = None  # 描述
    is_default: bool = False  # 是否为默认模型
    use_markdown: bool = True  # 是否使用Markdown图片格式
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(BASE_DIR / "data" / "zzimage.db")
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()
    
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Cookie表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cookies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    cookie_value TEXT NOT NULL,
                    socks5_proxy TEXT,
                    is_active INTEGER DEFAULT 1,
                    last_used TEXT,
                    use_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    daily_used INTEGER DEFAULT 0,
                    daily_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 检查是否需要添加新列（兼容旧数据库）
            cursor.execute("PRAGMA table_info(cookies)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'daily_used' not in columns:
                cursor.execute("ALTER TABLE cookies ADD COLUMN daily_used INTEGER DEFAULT 0")
            if 'daily_date' not in columns:
                cursor.execute("ALTER TABLE cookies ADD COLUMN daily_date TEXT")
            
            # API密钥表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 生成日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    cookie_id INTEGER,
                    api_key_id INTEGER,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    image_url TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cookie_id) REFERENCES cookies(id),
                    FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
                )
            """)
            
            # 模型配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    width INTEGER DEFAULT 1024,
                    height INTEGER DEFAULT 1024,
                    steps INTEGER DEFAULT 9,
                    description TEXT,
                    is_default INTEGER DEFAULT 0,
                    use_markdown INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 检查是否需要添加新列（兼容旧数据库）
            cursor.execute("PRAGMA table_info(model_configs)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'use_markdown' not in columns:
                cursor.execute("ALTER TABLE model_configs ADD COLUMN use_markdown INTEGER DEFAULT 1")
            
            # Session表（持久化登录状态）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    expires TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    # Cookie操作
    def add_cookie(self, cookie: Cookie) -> int:
        """添加Cookie"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cookies (name, cookie_value, socks5_proxy, is_active)
                VALUES (?, ?, ?, ?)
            """, (cookie.name, cookie.cookie_value,
                  cookie.socks5_proxy, 1 if cookie.is_active else 0))
            return cursor.lastrowid
    
    def get_cookie(self, cookie_id: int) -> Optional[Cookie]:
        """获取单个Cookie"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cookies WHERE id = ?", (cookie_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_cookie(row)
            return None
    
    def _row_to_cookie(self, row) -> Cookie:
        """将数据库行转换为Cookie对象"""
        columns = row.keys()
        return Cookie(
            id=row['id'],
            name=row['name'],
            cookie_value=row['cookie_value'],
            socks5_proxy=row['socks5_proxy'],
            is_active=bool(row['is_active']),
            last_used=row['last_used'],
            use_count=row['use_count'],
            error_count=row['error_count'],
            daily_used=row['daily_used'] if 'daily_used' in columns else 0,
            daily_date=row['daily_date'] if 'daily_date' in columns else None,
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def get_all_cookies(self, active_only: bool = False) -> List[Cookie]:
        """获取所有Cookie"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("SELECT * FROM cookies WHERE is_active = 1 ORDER BY use_count ASC")
            else:
                cursor.execute("SELECT * FROM cookies ORDER BY id DESC")
            rows = cursor.fetchall()
            return [self._row_to_cookie(row) for row in rows]
    
    def update_cookie(self, cookie: Cookie) -> bool:
        """更新Cookie"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE cookies
                SET name = ?, cookie_value = ?, socks5_proxy = ?, is_active = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (cookie.name, cookie.cookie_value, cookie.socks5_proxy,
                  1 if cookie.is_active else 0, cookie.id))
            return cursor.rowcount > 0
    
    def update_cookie_usage(self, cookie_id: int, success: bool = True):
        """更新Cookie使用统计"""
        today = datetime.now().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 先检查是否需要重置每日计数
            cursor.execute("SELECT daily_date FROM cookies WHERE id = ?", (cookie_id,))
            row = cursor.fetchone()
            if row and row['daily_date'] != today:
                # 新的一天，重置每日计数
                cursor.execute("""
                    UPDATE cookies SET daily_used = 0, daily_date = ? WHERE id = ?
                """, (today, cookie_id))
            
            if success:
                cursor.execute("""
                    UPDATE cookies
                    SET use_count = use_count + 1, daily_used = daily_used + 1,
                        daily_date = ?, last_used = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (today, cookie_id))
            else:
                cursor.execute("""
                    UPDATE cookies
                    SET error_count = error_count + 1, last_used = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (cookie_id,))
    
    def get_cookie_daily_usage(self, cookie_id: int) -> int:
        """获取Cookie今日使用次数"""
        today = datetime.now().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT daily_used, daily_date FROM cookies WHERE id = ?
            """, (cookie_id,))
            row = cursor.fetchone()
            if row:
                if row['daily_date'] == today:
                    return row['daily_used'] or 0
            return 0
    
    def reset_daily_usage_if_needed(self, cookie_id: int):
        """如果是新的一天，重置每日使用计数"""
        today = datetime.now().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE cookies SET daily_used = 0, daily_date = ?
                WHERE id = ? AND (daily_date IS NULL OR daily_date != ?)
            """, (today, cookie_id, today))
    
    def delete_cookie(self, cookie_id: int) -> bool:
        """删除Cookie"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cookies WHERE id = ?", (cookie_id,))
            return cursor.rowcount > 0
    
    # API密钥操作
    def add_api_key(self, api_key: ApiKey) -> int:
        """添加API密钥"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO api_keys (key, name, is_active)
                VALUES (?, ?, ?)
            """, (api_key.key, api_key.name, 1 if api_key.is_active else 0))
            return cursor.lastrowid
    
    def get_api_key_by_key(self, key: str) -> Optional[ApiKey]:
        """通过key获取API密钥"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM api_keys WHERE key = ? AND is_active = 1", (key,))
            row = cursor.fetchone()
            if row:
                return ApiKey(
                    id=row['id'],
                    key=row['key'],
                    name=row['name'],
                    is_active=bool(row['is_active']),
                    created_at=row['created_at']
                )
            return None
    
    def get_all_api_keys(self) -> List[ApiKey]:
        """获取所有API密钥"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM api_keys ORDER BY id DESC")
            rows = cursor.fetchall()
            return [ApiKey(
                id=row['id'],
                key=row['key'],
                name=row['name'],
                is_active=bool(row['is_active']),
                created_at=row['created_at']
            ) for row in rows]
    
    def delete_api_key(self, key_id: int) -> bool:
        """删除API密钥"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
            return cursor.rowcount > 0
    
    # 日志操作
    def add_generation_log(self, log: GenerationLog) -> int:
        """添加生成日志"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO generation_logs
                (prompt, width, height, cookie_id, api_key_id, status, error_message, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (log.prompt, log.width, log.height, log.cookie_id, log.api_key_id,
                  log.status, log.error_message, log.image_url))
            return cursor.lastrowid
    
    # 模型配置操作
    def add_model_config(self, model: ModelConfig) -> int:
        """添加模型配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 如果设为默认，先取消其他默认
            if model.is_default:
                cursor.execute("UPDATE model_configs SET is_default = 0")
            cursor.execute("""
                INSERT INTO model_configs (name, width, height, steps, description, is_default, use_markdown)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (model.name, model.width, model.height, model.steps,
                  model.description, 1 if model.is_default else 0, 1 if model.use_markdown else 0))
            return cursor.lastrowid
    
    def get_model_config(self, model_id: int) -> Optional[ModelConfig]:
        """获取单个模型配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM model_configs WHERE id = ?", (model_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_model_config(row)
            return None
    
    def get_model_config_by_name(self, name: str) -> Optional[ModelConfig]:
        """通过名称获取模型配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM model_configs WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return self._row_to_model_config(row)
            return None
    
    def get_default_model_config(self) -> Optional[ModelConfig]:
        """获取默认模型配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM model_configs WHERE is_default = 1 LIMIT 1")
            row = cursor.fetchone()
            if row:
                return self._row_to_model_config(row)
            return None
    
    def _row_to_model_config(self, row) -> ModelConfig:
        """将数据库行转换为ModelConfig对象"""
        columns = row.keys()
        return ModelConfig(
            id=row['id'],
            name=row['name'],
            width=row['width'],
            height=row['height'],
            steps=row['steps'],
            description=row['description'],
            is_default=bool(row['is_default']),
            use_markdown=bool(row['use_markdown']) if 'use_markdown' in columns else True,
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def get_all_model_configs(self) -> List[ModelConfig]:
        """获取所有模型配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM model_configs ORDER BY id DESC")
            rows = cursor.fetchall()
            return [self._row_to_model_config(row) for row in rows]
    
    def update_model_config(self, model: ModelConfig) -> bool:
        """更新模型配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 如果设为默认，先取消其他默认
            if model.is_default:
                cursor.execute("UPDATE model_configs SET is_default = 0 WHERE id != ?", (model.id,))
            cursor.execute("""
                UPDATE model_configs
                SET name = ?, width = ?, height = ?, steps = ?, description = ?, is_default = ?, use_markdown = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (model.name, model.width, model.height, model.steps,
                  model.description, 1 if model.is_default else 0, 1 if model.use_markdown else 0, model.id))
            return cursor.rowcount > 0
    
    def delete_model_config(self, model_id: int) -> bool:
        """删除模型配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM model_configs WHERE id = ?", (model_id,))
            return cursor.rowcount > 0


    # Session操作
    def save_session(self, token: str, username: str, expires: str):
        """保存会话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (token, username, expires)
                VALUES (?, ?, ?)
            """, (token, username, expires))
    
    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE token = ?", (token,))
            row = cursor.fetchone()
            if row:
                return {
                    "token": row["token"],
                    "username": row["username"],
                    "expires": row["expires"],
                    "created_at": row["created_at"]
                }
            return None
    
    def delete_session(self, token: str) -> bool:
        """删除会话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return cursor.rowcount > 0
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM sessions WHERE expires < datetime('now')
            """)


# 全局数据库实例
db = Database()


# 便捷函数，供auth模块使用
def save_session(token: str, username: str, expires: str):
    """保存会话"""
    db.save_session(token, username, expires)


def get_session(token: str) -> Optional[Dict[str, Any]]:
    """获取会话"""
    return db.get_session(token)


def delete_session(token: str) -> bool:
    """删除会话"""
    return db.delete_session(token)