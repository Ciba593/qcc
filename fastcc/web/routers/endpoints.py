"""
EndpointGroup 管理 API 路由

提供 EndpointGroup（高可用代理组）的 CRUD 操作。
EndpointGroup 包含主节点和副节点，支持自动故障切换。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from ..models import ApiResponse
from fastcc.core.config import ConfigManager
from fastcc.core.endpoint_group_manager import EndpointGroupManager

router = APIRouter()


# ========== Request/Response Models ==========

class CreateEndpointGroupRequest(BaseModel):
    """创建 EndpointGroup 请求"""
    name: str = Field(..., description="代理组名称（唯一标识）")
    description: str = Field(default="", description="描述信息")
    primary_configs: List[str] = Field(default_factory=list, description="主节点配置列表")
    secondary_configs: List[str] = Field(default_factory=list, description="副节点配置列表")
    enabled: bool = Field(default=True, description="是否启用")


class UpdateEndpointGroupRequest(BaseModel):
    """更新 EndpointGroup 请求"""
    description: Optional[str] = None
    primary_configs: Optional[List[str]] = None
    secondary_configs: Optional[List[str]] = None
    enabled: Optional[bool] = None


class AddConfigRequest(BaseModel):
    """添加配置节点请求"""
    config_name: str = Field(..., description="配置名称")


# ========== API Endpoints ==========

@router.get("")
async def list_endpoint_groups():
    """列出所有 EndpointGroup"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        groups = group_manager.list_groups()
        groups_data = [group.to_dict() for group in groups]

        return ApiResponse(
            success=True,
            data=groups_data,
            message=f"找到 {len(groups_data)} 个 EndpointGroup"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}")
async def get_endpoint_group(name: str):
    """获取指定的 EndpointGroup"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        group = group_manager.get_group(name)
        if not group:
            raise HTTPException(
                status_code=404,
                detail=f"EndpointGroup '{name}' 不存在"
            )

        return ApiResponse(
            success=True,
            data=group.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_endpoint_group(request: CreateEndpointGroupRequest):
    """创建新的 EndpointGroup"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        # 创建 EndpointGroup
        group = group_manager.create_group(
            name=request.name,
            description=request.description,
            primary_configs=request.primary_configs,
            secondary_configs=request.secondary_configs,
            enabled=request.enabled
        )

        if not group:
            raise HTTPException(
                status_code=400,
                detail="创建 EndpointGroup 失败"
            )

        return ApiResponse(
            success=True,
            data=group.to_dict(),
            message=f"EndpointGroup '{request.name}' 创建成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"创建 EndpointGroup 失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.put("/{name}")
async def update_endpoint_group(name: str, request: UpdateEndpointGroupRequest):
    """更新 EndpointGroup"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        # 构建更新参数（只包含非 None 的字段）
        update_data = {
            k: v for k, v in request.model_dump().items()
            if v is not None
        }

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供要更新的字段"
            )

        # 更新 EndpointGroup
        success = group_manager.update_group(name, **update_data)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"EndpointGroup '{name}' 不存在或更新失败"
            )

        # 返回更新后的数据
        group = group_manager.get_group(name)
        return ApiResponse(
            success=True,
            data=group.to_dict(),
            message=f"EndpointGroup '{name}' 更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"更新 EndpointGroup 失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.delete("/{name}")
async def delete_endpoint_group(name: str):
    """删除 EndpointGroup"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        success = group_manager.delete_group(name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"EndpointGroup '{name}' 不存在"
            )

        return ApiResponse(
            success=True,
            message=f"EndpointGroup '{name}' 已删除"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"删除 EndpointGroup 失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


# ========== 主节点管理 ==========

@router.post("/{name}/primary")
async def add_primary_config(name: str, request: AddConfigRequest):
    """添加主节点配置"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        success = group_manager.add_primary_config(name, request.config_name)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"添加主节点失败"
            )

        # 返回更新后的数据
        group = group_manager.get_group(name)
        return ApiResponse(
            success=True,
            data=group.to_dict(),
            message=f"已为 '{name}' 添加主节点: {request.config_name}"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"添加主节点失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.delete("/{name}/primary/{config_name}")
async def remove_primary_config(name: str, config_name: str):
    """移除主节点配置"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        success = group_manager.remove_primary_config(name, config_name)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"移除主节点失败"
            )

        # 返回更新后的数据
        group = group_manager.get_group(name)
        return ApiResponse(
            success=True,
            data=group.to_dict(),
            message=f"已从 '{name}' 移除主节点: {config_name}"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"移除主节点失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


# ========== 副节点管理 ==========

@router.post("/{name}/secondary")
async def add_secondary_config(name: str, request: AddConfigRequest):
    """添加副节点配置"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        success = group_manager.add_secondary_config(name, request.config_name)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"添加副节点失败"
            )

        # 返回更新后的数据
        group = group_manager.get_group(name)
        return ApiResponse(
            success=True,
            data=group.to_dict(),
            message=f"已为 '{name}' 添加副节点: {request.config_name}"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"添加副节点失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.delete("/{name}/secondary/{config_name}")
async def remove_secondary_config(name: str, config_name: str):
    """移除副节点配置"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        success = group_manager.remove_secondary_config(name, config_name)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"移除副节点失败"
            )

        # 返回更新后的数据
        group = group_manager.get_group(name)
        return ApiResponse(
            success=True,
            data=group.to_dict(),
            message=f"已从 '{name}' 移除副节点: {config_name}"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"移除副节点失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)
