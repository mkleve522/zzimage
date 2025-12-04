"""
模型配置管理路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

from app.database import db, ModelConfig
from app.routers.auth import require_admin


router = APIRouter(prefix="/api/models", tags=["models"])


class ModelConfigCreate(BaseModel):
    """创建模型配置请求"""
    name: str
    width: int = 1024
    height: int = 1024
    steps: int = 9
    description: Optional[str] = None
    is_default: bool = False
    use_markdown: bool = True  # 是否使用Markdown图片格式


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求"""
    name: str
    width: int = 1024
    height: int = 1024
    steps: int = 9
    description: Optional[str] = None
    is_default: bool = False
    use_markdown: bool = True  # 是否使用Markdown图片格式


class ModelConfigResponse(BaseModel):
    """模型配置响应"""
    id: int
    name: str
    width: int
    height: int
    steps: int
    description: Optional[str]
    is_default: bool
    use_markdown: bool
    created_at: Optional[str]
    updated_at: Optional[str]


@router.get("")
async def list_models(_: bool = Depends(require_admin)):
    """获取所有模型配置"""
    models = db.get_all_model_configs()
    return {
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "width": m.width,
                "height": m.height,
                "steps": m.steps,
                "description": m.description,
                "is_default": m.is_default,
                "use_markdown": m.use_markdown,
                "created_at": m.created_at,
                "updated_at": m.updated_at
            }
            for m in models
        ]
    }


@router.get("/{model_id}")
async def get_model(model_id: int, _: bool = Depends(require_admin)):
    """获取单个模型配置"""
    model = db.get_model_config(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return {
        "id": model.id,
        "name": model.name,
        "width": model.width,
        "height": model.height,
        "steps": model.steps,
        "description": model.description,
        "is_default": model.is_default,
        "use_markdown": model.use_markdown,
        "created_at": model.created_at,
        "updated_at": model.updated_at
    }


@router.post("")
async def create_model(data: ModelConfigCreate, _: bool = Depends(require_admin)):
    """创建模型配置"""
    # 检查名称是否已存在
    existing = db.get_model_config_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="模型名称已存在")
    
    # 验证尺寸
    if data.width < 256 or data.width > 2048:
        raise HTTPException(status_code=400, detail="宽度必须在256-2048之间")
    if data.height < 256 or data.height > 2048:
        raise HTTPException(status_code=400, detail="高度必须在256-2048之间")
    
    model = ModelConfig(
        name=data.name,
        width=data.width,
        height=data.height,
        steps=data.steps,
        description=data.description,
        is_default=data.is_default,
        use_markdown=data.use_markdown
    )
    
    model_id = db.add_model_config(model)
    return {"id": model_id, "message": "模型配置创建成功"}


@router.put("/{model_id}")
async def update_model(model_id: int, data: ModelConfigUpdate, _: bool = Depends(require_admin)):
    """更新模型配置"""
    model = db.get_model_config(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    
    # 检查名称是否与其他模型冲突
    existing = db.get_model_config_by_name(data.name)
    if existing and existing.id != model_id:
        raise HTTPException(status_code=400, detail="模型名称已存在")
    
    # 验证尺寸
    if data.width < 256 or data.width > 2048:
        raise HTTPException(status_code=400, detail="宽度必须在256-2048之间")
    if data.height < 256 or data.height > 2048:
        raise HTTPException(status_code=400, detail="高度必须在256-2048之间")
    
    model.name = data.name
    model.width = data.width
    model.height = data.height
    model.steps = data.steps
    model.description = data.description
    model.is_default = data.is_default
    model.use_markdown = data.use_markdown
    
    db.update_model_config(model)
    return {"message": "模型配置更新成功"}


@router.delete("/{model_id}")
async def delete_model(model_id: int, _: bool = Depends(require_admin)):
    """删除模型配置"""
    model = db.get_model_config(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    
    db.delete_model_config(model_id)
    return {"message": "模型配置删除成功"}