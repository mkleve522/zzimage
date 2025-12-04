"""
图片生成路由 - 适配Gitee AI接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from app.config import PRESET_SIZES, MAX_IMAGE_SIZE, MIN_IMAGE_SIZE
from app.services.image_gen import image_generator

router = APIRouter(prefix="/api/generate", tags=["图片生成"])


class GenerateRequest(BaseModel):
    """生成请求"""
    prompt: str = Field(..., description="正向提示词", min_length=1, max_length=4000)
    negative_prompt: Optional[str] = Field(None, description="负向提示词", max_length=2000)
    width: int = Field(1024, description="图片宽度", ge=MIN_IMAGE_SIZE, le=MAX_IMAGE_SIZE)
    height: int = Field(1024, description="图片高度", ge=MIN_IMAGE_SIZE, le=MAX_IMAGE_SIZE)
    model: Optional[str] = Field("z-image-turbo", description="模型名称")
    num_inference_steps: Optional[int] = Field(9, description="推理步数", ge=1, le=50)


class GenerateResponse(BaseModel):
    """生成响应"""
    success: bool
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    error: Optional[str] = None


class PresetSize(BaseModel):
    """预设尺寸"""
    width: int
    height: int
    label: str


class SizePresetsResponse(BaseModel):
    """尺寸预设响应"""
    presets: dict
    max_size: int
    min_size: int


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    description: str


@router.post("/", response_model=GenerateResponse)
async def generate_image(request: GenerateRequest):
    """
    生成图片
    
    - **prompt**: 正向提示词，描述想要生成的图片内容
    - **negative_prompt**: 负向提示词，描述不想要的内容（可选）
    - **width**: 图片宽度，范围 256-2048
    - **height**: 图片高度，范围 256-2048
    - **model**: 模型名称，默认 z-image-turbo
    - **num_inference_steps**: 推理步数，默认 9
    """
    result = await image_generator.generate_with_retry(
        prompt=request.prompt,
        width=request.width,
        height=request.height,
        negative_prompt=request.negative_prompt,
        model=request.model,
        num_inference_steps=request.num_inference_steps
    )
    
    return GenerateResponse(
        success=result.success,
        image_url=result.image_url,
        image_base64=result.image_base64,
        error=result.error
    )


@router.get("/presets", response_model=SizePresetsResponse)
async def get_size_presets():
    """
    获取预设尺寸列表
    
    返回所有可用的预设尺寸比例和具体尺寸
    """
    return SizePresetsResponse(
        presets=PRESET_SIZES,
        max_size=MAX_IMAGE_SIZE,
        min_size=MIN_IMAGE_SIZE
    )


@router.get("/models")
async def get_available_models():
    """
    获取可用模型列表
    """
    return {
        "models": [
            {
                "id": "z-image-turbo",
                "name": "Z-Image Turbo",
                "description": "快速生成模型，推荐步数9"
            }
        ],
        "default": "z-image-turbo"
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "image-generator"}