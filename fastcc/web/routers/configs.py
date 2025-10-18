"""
配置管理 API 路由
对应 CLI: add, list, use, default, remove, sync
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..models import ApiResponse, ConfigProfileModel
from ..utils import to_dict, to_dict_list
from fastcc.core.config import ConfigManager, ConfigProfile

router = APIRouter()


class CreateConfigRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class UpdateConfigRequest(BaseModel):
    description: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("")
async def list_configs():
    """获取所有配置 - 对应 CLI: qcc list"""
    try:
        config_manager = ConfigManager()
        profiles = to_dict_list(config_manager.list_profiles())

        return ApiResponse(
            success=True,
            data=profiles,
            message=f"找到 {len(profiles)} 个配置"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_config(request: CreateConfigRequest):
    """创建新配置 - 对应 CLI: qcc add <name>"""
    try:
        config_manager = ConfigManager()

        # 使用 add_profile 方法（会自动保存和同步）
        success = config_manager.add_profile(
            name=request.name,
            description=request.description or "",
            base_url=request.base_url or "",
            api_key=request.api_key or ""
        )

        if not success:
            raise HTTPException(status_code=400, detail=f"配置 '{request.name}' 已存在")

        # 获取创建的配置
        profile = config_manager.get_profile(request.name)

        return ApiResponse(
            success=True,
            data=to_dict(profile),
            message=f"配置 '{request.name}' 创建成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/default")
async def get_default_config():
    """获取默认配置"""
    try:
        config_manager = ConfigManager()
        profile = config_manager.get_default_profile()

        if not profile:
            return ApiResponse(
                success=True,
                data=None,
                message="未设置默认配置"
            )

        return ApiResponse(
            success=True,
            data=to_dict(profile)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_config():
    """获取当前使用的配置（最近使用的配置）"""
    try:
        config_manager = ConfigManager()
        profiles = config_manager.list_profiles()

        # 找出 last_used 时间最新的配置
        current_profile = None
        latest_time = None

        for profile in profiles:
            if profile.last_used:
                if latest_time is None or profile.last_used > latest_time:
                    latest_time = profile.last_used
                    current_profile = profile

        if not current_profile:
            return ApiResponse(
                success=True,
                data=None,
                message="尚未使用任何配置"
            )

        return ApiResponse(
            success=True,
            data=to_dict(current_profile)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_configs():
    """手动同步配置 - 对应 CLI: qcc sync"""
    try:
        config_manager = ConfigManager()

        # 从云端同步
        try:
            config_manager.sync_from_cloud()
        except Exception as e:
            # 同步失败不影响继续
            pass

        # 同步到云端
        try:
            config_manager.sync_to_cloud()
        except Exception as e:
            # 同步失败不影响继续
            pass

        profiles = config_manager.list_profiles()

        return ApiResponse(
            success=True,
            data={
                "total": len(profiles),
                "synced_at": config_manager.settings.get('last_sync')
            },
            message="配置同步成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{config_name}")
async def get_config(config_name: str):
    """获取单个配置详情"""
    try:
        # 特殊处理：如果请求 "default"，返回默认配置而不是名为 "default" 的配置
        if config_name == "default":
            config_manager = ConfigManager()
            profile = config_manager.get_default_profile()
            if not profile:
                return ApiResponse(
                    success=True,
                    data=None,
                    message="未设置默认配置"
                )
            return ApiResponse(
                success=True,
                data=to_dict(profile)
            )

        config_manager = ConfigManager()
        profile = config_manager.get_profile(config_name)

        if not profile:
            raise HTTPException(status_code=404, detail=f"配置 '{config_name}' 不存在")

        return ApiResponse(
            success=True,
            data=to_dict(profile)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{config_name}")
async def update_config(config_name: str, request: UpdateConfigRequest):
    """更新配置"""
    try:
        config_manager = ConfigManager()
        profile = config_manager.get_profile(config_name)

        if not profile:
            raise HTTPException(status_code=404, detail=f"配置 '{config_name}' 不存在")

        # 更新字段
        if request.description is not None:
            profile.description = request.description
        if request.base_url is not None:
            profile.base_url = request.base_url
        if request.api_key is not None:
            profile.api_key = request.api_key
        if request.enabled is not None:
            profile.enabled = request.enabled

        # 保存更新
        config_manager._save_local_cache()
        if config_manager.settings.get('auto_sync'):
            try:
                config_manager.sync_to_cloud()
            except:
                pass

        return ApiResponse(
            success=True,
            data=to_dict(profile),
            message=f"配置 '{config_name}' 更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{config_name}")
async def delete_config(config_name: str):
    """删除配置 - 对应 CLI: qcc remove <name>"""
    try:
        config_manager = ConfigManager()

        if not config_manager.get_profile(config_name):
            raise HTTPException(status_code=404, detail=f"配置 '{config_name}' 不存在")

        # remove_profile 会自动保存和同步
        success = config_manager.remove_profile(config_name)

        if not success:
            raise HTTPException(status_code=500, detail=f"删除配置 '{config_name}' 失败")

        return ApiResponse(
            success=True,
            message=f"配置 '{config_name}' 已删除"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{config_name}/use")
async def use_config(config_name: str):
    """使用指定配置启动 Claude Code - 对应 CLI: qcc use <name>"""
    try:
        config_manager = ConfigManager()
        profile = config_manager.get_profile(config_name)

        if not profile:
            raise HTTPException(status_code=404, detail=f"配置 '{config_name}' 不存在")

        # 应用配置（会自动保存和同步）
        success = config_manager.apply_profile(config_name)

        if not success:
            raise HTTPException(status_code=500, detail=f"应用配置 '{config_name}' 失败")

        return ApiResponse(
            success=True,
            data=to_dict(profile),
            message=f"✅ 已应用配置 '{config_name}' 到 Claude Code"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"应用配置失败: {str(e)}\n\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/{config_name}/default")
async def set_default_config(config_name: str):
    """设置默认配置 - 对应 CLI: qcc default <name>"""
    try:
        config_manager = ConfigManager()
        profile = config_manager.get_profile(config_name)

        if not profile:
            raise HTTPException(status_code=404, detail=f"配置 '{config_name}' 不存在")

        # set_default_profile 会自动保存和同步
        success = config_manager.set_default_profile(config_name)

        if not success:
            raise HTTPException(status_code=500, detail=f"设置默认配置失败")

        return ApiResponse(
            success=True,
            message=f"已将 '{config_name}' 设为默认配置"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
