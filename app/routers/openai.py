"""
OpenAI兼容接口路由
提供与OpenAI Images API和Chat API兼容的接口，方便其他工具调用
"""
import time
import uuid
import json
import re
import logging
from fastapi import APIRouter, HTTPException, Header, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Union

from app.database import db
from app.services.image_gen import image_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["OpenAI兼容接口"])


# OpenAI格式的请求/响应模型
class ImageGenerationRequest(BaseModel):
    """OpenAI图片生成请求格式"""
    model: str = Field(default="dall-e-3", description="模型名称")
    prompt: str = Field(..., description="提示词", min_length=1, max_length=4000)
    n: int = Field(default=1, description="生成数量", ge=1, le=1)  # 目前只支持1张
    size: str = Field(default="1024x1024", description="图片尺寸")
    quality: str = Field(default="standard", description="图片质量")
    response_format: Literal["url", "b64_json"] = Field(
        default="url", 
        description="响应格式"
    )
    style: Optional[str] = Field(default="vivid", description="风格")
    user: Optional[str] = Field(default=None, description="用户标识")


class ImageData(BaseModel):
    """图片数据"""
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    """OpenAI图片生成响应格式"""
    created: int
    data: List[ImageData]


class ErrorDetail(BaseModel):
    """错误详情"""
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    error: ErrorDetail


# Chat相关模型
class ChatMessage(BaseModel):
    """聊天消息"""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat Completion请求"""
    model: str = Field(default="z-image", description="模型名称")
    messages: List[ChatMessage] = Field(..., description="消息列表")
    temperature: float = Field(default=1.0, description="温度")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")
    stream: bool = Field(default=False, description="是否流式输出")
    user: Optional[str] = Field(default=None, description="用户标识")


class ChatChoice(BaseModel):
    """Chat选项"""
    index: int
    message: ChatMessage
    finish_reason: str


class ChatUsage(BaseModel):
    """使用统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Chat Completion响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: ChatUsage


def parse_size(size: str) -> tuple:
    """解析尺寸字符串"""
    try:
        parts = size.lower().split("x")
        if len(parts) != 2:
            raise ValueError("Invalid size format")
        width = int(parts[0])
        height = int(parts[1])
        return width, height
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"Invalid size format: {size}. Expected format: WIDTHxHEIGHT (e.g., 1024x1024)",
                    "type": "invalid_request_error",
                    "param": "size",
                    "code": "invalid_size"
                }
            }
        )


async def verify_api_key(authorization: Optional[str] = Header(None)):
    """验证API密钥"""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Missing Authorization header",
                    "type": "invalid_request_error",
                    "code": "missing_api_key"
                }
            }
        )
    
    # 提取Bearer token
    if authorization.startswith("Bearer "):
        api_key = authorization[7:]
    else:
        api_key = authorization
    
    # 验证API密钥
    key_record = db.get_api_key_by_key(api_key)
    if not key_record:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid API key",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key"
                }
            }
        )
    
    return key_record


@router.post("/images/generations", response_model=ImageGenerationResponse)
async def create_image(
    request: ImageGenerationRequest,
    api_key = Depends(verify_api_key)
):
    """
    创建图片 - OpenAI兼容接口
    
    与OpenAI的 /v1/images/generations 接口兼容
    
    支持的参数:
    - **model**: 模型名称（目前忽略，使用内置模型）
    - **prompt**: 提示词
    - **n**: 生成数量（目前只支持1）
    - **size**: 图片尺寸，格式为 WIDTHxHEIGHT
    - **quality**: 图片质量（目前忽略）
    - **response_format**: 响应格式，url 或 b64_json
    - **style**: 风格（目前忽略）
    """
    # 解析尺寸
    width, height = parse_size(request.size)
    
    # 验证尺寸范围
    if width < 256 or height < 256:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": "Size must be at least 256x256",
                    "type": "invalid_request_error",
                    "param": "size",
                    "code": "invalid_size"
                }
            }
        )
    
    if width > 2048 or height > 2048:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": "Size must not exceed 2048x2048",
                    "type": "invalid_request_error",
                    "param": "size",
                    "code": "invalid_size"
                }
            }
        )
    
    # 生成图片
    result = await image_generator.generate_with_retry(
        prompt=request.prompt,
        width=width,
        height=height,
        api_key_id=api_key.id
    )
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": result.error or "Image generation failed",
                    "type": "server_error",
                    "code": "generation_failed"
                }
            }
        )
    
    # 构建响应
    image_data = ImageData(revised_prompt=request.prompt)
    
    if request.response_format == "b64_json":
        image_data.b64_json = result.image_base64
    else:
        image_data.url = result.image_url
    
    return ImageGenerationResponse(
        created=int(time.time()),
        data=[image_data]
    )


@router.get("/models")
async def list_models(request: Request):
    """
    列出可用模型 - OpenAI兼容接口
    
    只返回数据库中配置的自定义模型
    """
    logger.info(f"[/v1/models] 收到请求 - 路径: {request.url.path}, 方法: {request.method}")
    logger.info(f"[/v1/models] 请求头: {dict(request.headers)}")
    
    models = []
    
    # 获取用户自定义模型
    custom_models = db.get_all_model_configs()
    for model in custom_models:
        try:
            created_ts = int(time.mktime(time.strptime(model.created_at[:19], "%Y-%m-%d %H:%M:%S"))) if model.created_at else int(time.time())
        except:
            created_ts = int(time.time())
        
        models.append({
            "id": model.name,
            "object": "model",
            "created": created_ts,
            "owned_by": "user",
            "description": model.description or f"自定义模型 ({model.width}x{model.height}, {model.steps}步)",
            "metadata": {
                "width": model.width,
                "height": model.height,
                "steps": model.steps,
                "is_default": model.is_default
            }
        })
    
    logger.info(f"[/v1/models] 返回 {len(models)} 个模型: {[m['id'] for m in models]}")
    
    return {
        "object": "list",
        "data": models
    }


@router.get("/models/{model_id}")
async def get_model(model_id: str, request: Request):
    """
    获取模型信息 - OpenAI兼容接口
    """
    logger.info(f"[/v1/models/{model_id}] 收到请求 - 路径: {request.url.path}")
    
    # 检查是否是自定义模型
    custom_model = db.get_model_config_by_name(model_id)
    if custom_model:
        try:
            created_ts = int(time.mktime(time.strptime(custom_model.created_at[:19], "%Y-%m-%d %H:%M:%S"))) if custom_model.created_at else int(time.time())
        except:
            created_ts = int(time.time())
        
        return {
            "id": custom_model.name,
            "object": "model",
            "created": created_ts,
            "owned_by": "user",
            "description": custom_model.description or f"自定义模型 ({custom_model.width}x{custom_model.height}, {custom_model.steps}步)",
            "metadata": {
                "width": custom_model.width,
                "height": custom_model.height,
                "steps": custom_model.steps,
                "is_default": custom_model.is_default
            }
        }
    
    # 模型不存在
    raise HTTPException(
        status_code=404,
        detail={
            "error": {
                "message": f"Model '{model_id}' not found",
                "type": "invalid_request_error",
                "code": "model_not_found"
            }
        }
    )


def extract_image_params_from_messages(messages: List[ChatMessage], model: str) -> dict:
    """从消息中提取图片生成参数"""
    # 获取最后一条用户消息作为提示词
    prompt = ""
    for msg in reversed(messages):
        if msg.role == "user":
            prompt = msg.content
            break
    
    if not prompt:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": "No user message found",
                    "type": "invalid_request_error",
                    "code": "missing_prompt"
                }
            }
        )
    
    # 默认参数
    width = 1024
    height = 1024
    steps = 9
    use_markdown = True  # 默认使用Markdown格式
    
    # 尝试从模型配置获取参数
    model_config = db.get_model_config_by_name(model)
    if model_config:
        width = model_config.width
        height = model_config.height
        steps = model_config.steps
        use_markdown = model_config.use_markdown
    else:
        # 尝试获取默认模型配置
        default_config = db.get_default_model_config()
        if default_config:
            width = default_config.width
            height = default_config.height
            steps = default_config.steps
            use_markdown = default_config.use_markdown
    
    # 尝试从提示词中解析尺寸（支持格式如 --size 1024x768 或 --width 1024 --height 768）
    size_match = re.search(r'--size\s+(\d+)x(\d+)', prompt, re.IGNORECASE)
    if size_match:
        width = int(size_match.group(1))
        height = int(size_match.group(2))
        prompt = re.sub(r'--size\s+\d+x\d+', '', prompt, flags=re.IGNORECASE).strip()
    else:
        width_match = re.search(r'--width\s+(\d+)', prompt, re.IGNORECASE)
        height_match = re.search(r'--height\s+(\d+)', prompt, re.IGNORECASE)
        if width_match:
            width = int(width_match.group(1))
            prompt = re.sub(r'--width\s+\d+', '', prompt, flags=re.IGNORECASE).strip()
        if height_match:
            height = int(height_match.group(1))
            prompt = re.sub(r'--height\s+\d+', '', prompt, flags=re.IGNORECASE).strip()
    
    # 尝试从提示词中解析步数
    steps_match = re.search(r'--steps\s+(\d+)', prompt, re.IGNORECASE)
    if steps_match:
        steps = int(steps_match.group(1))
        prompt = re.sub(r'--steps\s+\d+', '', prompt, flags=re.IGNORECASE).strip()
    
    # 验证尺寸范围
    width = max(256, min(2048, width))
    height = max(256, min(2048, height))
    steps = max(1, min(50, steps))
    
    return {
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "use_markdown": use_markdown
    }


@router.post("/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    raw_request: Request,
    api_key = Depends(verify_api_key)
):
    """
    Chat Completion - OpenAI兼容接口
    
    将聊天消息转换为图片生成请求，返回生成的图片URL
    
    支持的参数:
    - **model**: 模型名称，必须是在"模型配置"中配置的模型
    - **messages**: 消息列表，最后一条用户消息作为提示词
    - **stream**: 是否流式输出（目前不支持真正的流式，会模拟）
    
    提示词中可以使用以下参数覆盖默认设置:
    - --size 1024x768: 设置图片尺寸
    - --width 1024: 设置宽度
    - --height 768: 设置高度
    - --steps 9: 设置推理步数
    """
    logger.info(f"[/v1/chat/completions] 收到请求")
    logger.info(f"[/v1/chat/completions] 请求路径: {raw_request.url.path}")
    logger.info(f"[/v1/chat/completions] 请求模型: {request.model}")
    logger.info(f"[/v1/chat/completions] 消息数量: {len(request.messages)}")
    logger.info(f"[/v1/chat/completions] 流式输出: {request.stream}")
    
    # 检查模型是否存在
    model_config = db.get_model_config_by_name(request.model)
    logger.info(f"[/v1/chat/completions] 查找模型 '{request.model}': {'找到' if model_config else '未找到'}")
    
    if not model_config:
        # 检查是否有默认模型
        default_config = db.get_default_model_config()
        logger.info(f"[/v1/chat/completions] 默认模型: {'找到' if default_config else '未找到'}")
        
        if not default_config:
            # 获取所有可用模型
            all_models = db.get_all_model_configs()
            available_models = [m.name for m in all_models] if all_models else []
            logger.warning(f"[/v1/chat/completions] 模型不存在，可用模型: {available_models}")
            
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "message": f"模型 '{request.model}' 不存在。请先在管理页面的'模型配置'中添加模型。" +
                                   (f" 可用模型: {', '.join(available_models)}" if available_models else " 当前没有配置任何模型。"),
                        "type": "invalid_request_error",
                        "code": "model_not_found"
                    }
                }
            )
    
    # 提取图片生成参数
    params = extract_image_params_from_messages(request.messages, request.model)
    logger.info(f"[/v1/chat/completions] 提取参数: prompt长度={len(params['prompt'])}, 尺寸={params['width']}x{params['height']}, 步数={params['steps']}")
    
    # 生成图片
    logger.info(f"[/v1/chat/completions] 开始生成图片...")
    result = await image_generator.generate_with_retry(
        prompt=params["prompt"],
        width=params["width"],
        height=params["height"],
        num_inference_steps=params["steps"],
        api_key_id=api_key.id
    )
    
    if not result.success:
        logger.error(f"[/v1/chat/completions] 生成失败: {result.error}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": result.error or "Image generation failed",
                    "type": "server_error",
                    "code": "generation_failed"
                }
            }
        )
    
    logger.info(f"[/v1/chat/completions] 生成成功!")
    
    # 构建响应内容
    image_url = result.image_url or f"data:image/png;base64,{result.image_base64}"
    
    # 根据模型配置决定是否使用Markdown格式
    if params["use_markdown"]:
        # 使用Markdown图片语法，在支持Markdown的工具中可以直接渲染显示
        response_content = f"![image]({image_url})"
    else:
        # 只返回图片URL
        response_content = image_url
    
    response_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created_time = int(time.time())
    
    if request.stream:
        # 流式响应
        async def generate_stream():
            # 发送开始
            chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            
            # 分块发送内容
            chunk_size = 50
            for i in range(0, len(response_content), chunk_size):
                content_chunk = response_content[i:i+chunk_size]
                chunk = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": content_chunk},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            
            # 发送结束
            chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    else:
        # 非流式响应
        return ChatCompletionResponse(
            id=response_id,
            object="chat.completion",
            created=created_time,
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=response_content
                    ),
                    finish_reason="stop"
                )
            ],
            usage=ChatUsage(
                prompt_tokens=len(params["prompt"]) // 4,
                completion_tokens=len(response_content) // 4,
                total_tokens=(len(params["prompt"]) + len(response_content)) // 4
            )
        )