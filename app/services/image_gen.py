"""
图片生成服务 - 适配Gitee AI接口，支持SOCKS5代理
"""
import asyncio
import aiohttp
import base64
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

try:
    from aiohttp_socks import ProxyConnector
    HAS_SOCKS_SUPPORT = True
except ImportError:
    HAS_SOCKS_SUPPORT = False
    ProxyConnector = None

from app.config import REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, MAX_IMAGE_SIZE, MIN_IMAGE_SIZE
from app.database import db, Cookie, GenerationLog
from app.services.cookie_pool import cookie_pool

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    error: Optional[str] = None
    cookie_id: Optional[int] = None


class ImageGenerator:
    """图片生成器 - 适配Gitee AI接口"""
    
    # Gitee AI API配置
    API_BASE_URL = "https://ai.gitee.com"
    API_ENDPOINT = "/v1/images/generations"
    DEFAULT_MODEL = "z-image-turbo"
    DEFAULT_STEPS = 9
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _validate_size(self, width: int, height: int) -> Tuple[bool, str]:
        """验证图片尺寸"""
        if width < MIN_IMAGE_SIZE or height < MIN_IMAGE_SIZE:
            return False, f"尺寸不能小于 {MIN_IMAGE_SIZE}x{MIN_IMAGE_SIZE}"
        if width > MAX_IMAGE_SIZE or height > MAX_IMAGE_SIZE:
            return False, f"尺寸不能大于 {MAX_IMAGE_SIZE}x{MAX_IMAGE_SIZE}"
        return True, ""
    
    def _create_connector(self, proxy: Optional[str] = None) -> Optional[Any]:
        """创建连接器（支持SOCKS5代理）"""
        if proxy and HAS_SOCKS_SUPPORT:
            try:
                return ProxyConnector.from_url(proxy)
            except Exception as e:
                logger.warning(f"创建代理连接器失败: {e}")
                return None
        return None
    
    async def _get_session(self, proxy: Optional[str] = None) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        connector = self._create_connector(proxy)
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        return aiohttp.ClientSession(connector=connector, timeout=timeout)
    
    async def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        negative_prompt: Optional[str] = None,
        model: str = None,
        num_inference_steps: int = None,
        api_key_id: Optional[int] = None
    ) -> GenerationResult:
        """
        生成图片
        
        Args:
            prompt: 正向提示词
            width: 图片宽度
            height: 图片高度
            negative_prompt: 负向提示词（可选）
            model: 模型名称（可选，默认z-image-turbo）
            num_inference_steps: 推理步数（可选，默认9）
            api_key_id: API密钥ID（用于日志记录）
            
        Returns:
            GenerationResult对象
        """
        # 验证尺寸
        valid, error_msg = self._validate_size(width, height)
        if not valid:
            return GenerationResult(success=False, error=error_msg)
        
        # 获取Cookie
        cookie = await cookie_pool.get_next_cookie()
        if not cookie:
            return GenerationResult(
                success=False, 
                error="没有可用的Cookie，请先添加Cookie"
            )
        
        # 尝试生成
        result = await self._do_generate(
            cookie=cookie,
            prompt=prompt,
            width=width,
            height=height,
            negative_prompt=negative_prompt,
            model=model or self.DEFAULT_MODEL,
            num_inference_steps=num_inference_steps or self.DEFAULT_STEPS
        )
        
        # 更新Cookie使用状态
        await cookie_pool.mark_cookie_used(cookie.id, result.success)
        
        # 记录日志
        log = GenerationLog(
            prompt=prompt,
            width=width,
            height=height,
            cookie_id=cookie.id,
            api_key_id=api_key_id,
            status="success" if result.success else "failed",
            error_message=result.error,
            image_url=result.image_url
        )
        db.add_generation_log(log)
        
        return result
    
    async def _do_generate(
        self,
        cookie: Cookie,
        prompt: str,
        width: int,
        height: int,
        negative_prompt: Optional[str] = None,
        model: str = "z-image-turbo",
        num_inference_steps: int = 9
    ) -> GenerationResult:
        """
        执行实际的图片生成请求 - 适配Gitee AI接口
        """
        session = None
        try:
            session = await self._get_session(cookie.socks5_proxy)
            
            # 构建请求头 - Gitee AI使用Bearer Token认证
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cookie.cookie_value}",
                "User-Agent": "ZZImage/1.0"
            }
            
            # 构建请求体 - Gitee AI格式
            payload = {
                "prompt": prompt,
                "model": model,
                "size": f"{width}x{height}",
                "num_inference_steps": num_inference_steps
            }
            
            # 如果有负向提示词，添加到payload
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
            
            logger.info(f"发送生成请求: model={model}, size={width}x{height}")
            
            # 发送请求（带重试）
            for attempt in range(MAX_RETRIES):
                try:
                    async with session.post(
                        f"{self.API_BASE_URL}{self.API_ENDPOINT}",
                        json=payload,
                        headers=headers
                    ) as response:
                        response_text = await response.text()
                        logger.debug(f"API响应 [{response.status}]: {response_text[:500]}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                            except:
                                # 如果JSON解析失败，尝试从文本解析
                                import json
                                data = json.loads(response_text)
                            
                            # 解析Gitee AI响应格式
                            # 响应格式: {"created": timestamp, "data": [{"b64_json": "...", "type": "image/png"}]}
                            if "data" in data and len(data["data"]) > 0:
                                image_data = data["data"][0]
                                image_base64 = image_data.get("b64_json")
                                image_type = image_data.get("type", "image/png")
                                
                                # 如果有url字段也获取
                                image_url = image_data.get("url")
                                
                                if image_base64:
                                    return GenerationResult(
                                        success=True,
                                        image_url=image_url,
                                        image_base64=image_base64,
                                        cookie_id=cookie.id
                                    )
                                elif image_url:
                                    return GenerationResult(
                                        success=True,
                                        image_url=image_url,
                                        image_base64=None,
                                        cookie_id=cookie.id
                                    )
                                else:
                                    return GenerationResult(
                                        success=False,
                                        error="API返回数据中没有图片",
                                        cookie_id=cookie.id
                                    )
                            else:
                                return GenerationResult(
                                    success=False,
                                    error="API返回数据格式异常",
                                    cookie_id=cookie.id
                                )
                        
                        elif response.status == 429:
                            # 速率限制，等待后重试
                            logger.warning(f"速率限制，等待重试 (尝试 {attempt + 1}/{MAX_RETRIES})")
                            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                        
                        elif response.status == 401:
                            # 认证失败
                            return GenerationResult(
                                success=False,
                                error="Cookie/Token无效或已过期",
                                cookie_id=cookie.id
                            )
                        
                        elif response.status == 400:
                            # 请求参数错误
                            try:
                                error_data = await response.json()
                                error_msg = error_data.get("error", {}).get("message", response_text)
                            except:
                                error_msg = response_text
                            return GenerationResult(
                                success=False,
                                error=f"请求参数错误: {error_msg}",
                                cookie_id=cookie.id
                            )
                        
                        else:
                            logger.error(f"API错误 {response.status}: {response_text}")
                            return GenerationResult(
                                success=False,
                                error=f"API错误: {response.status}",
                                cookie_id=cookie.id
                            )
                            
                except aiohttp.ClientError as e:
                    logger.warning(f"请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        return GenerationResult(
                            success=False,
                            error=f"请求失败: {str(e)}",
                            cookie_id=cookie.id
                        )
            
            return GenerationResult(
                success=False,
                error="超过最大重试次数",
                cookie_id=cookie.id
            )
            
        except Exception as e:
            logger.exception(f"生成图片时发生错误: {e}")
            return GenerationResult(
                success=False,
                error=f"内部错误: {str(e)}",
                cookie_id=cookie.id if cookie else None
            )
        finally:
            if session:
                await session.close()
    
    async def generate_with_retry(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        negative_prompt: Optional[str] = None,
        model: str = None,
        num_inference_steps: int = None,
        max_cookie_retries: int = 3,
        api_key_id: Optional[int] = None
    ) -> GenerationResult:
        """
        带Cookie重试的生成方法
        
        如果一个Cookie失败，会尝试使用其他Cookie
        """
        last_error = None
        
        for i in range(max_cookie_retries):
            result = await self.generate(
                prompt=prompt,
                width=width,
                height=height,
                negative_prompt=negative_prompt,
                model=model,
                num_inference_steps=num_inference_steps,
                api_key_id=api_key_id
            )
            
            if result.success:
                return result
            
            last_error = result.error
            logger.warning(f"Cookie重试 {i + 1}/{max_cookie_retries}: {last_error}")
        
        return GenerationResult(
            success=False,
            error=f"所有Cookie都失败: {last_error}"
        )


# 全局图片生成器实例
image_generator = ImageGenerator()