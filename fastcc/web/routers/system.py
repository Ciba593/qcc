"""
系统配置 API 路由
提供模型配置、系统设置等接口
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from ..models import ApiResponse
from fastcc.core.config import ConfigManager
from fastcc.core.models import get_all_models_dict
from fastcc import __version__, __description__

router = APIRouter()

# 全局依赖（需要由应用启动时注入）
_config_manager: Optional[ConfigManager] = None


def set_config_manager(config_manager: ConfigManager):
    """设置配置管理器"""
    global _config_manager
    _config_manager = config_manager


# ============= 数据模型 =============

class ModelConfigRequest(BaseModel):
    """模型配置请求"""
    test_model: Optional[str] = None  # 健康检查使用的模型
    proxy_model_mode: Optional[str] = None  # 代理模型模式
    proxy_model_override: Optional[str] = None  # 强制替换的模型


# ============= API 路由 =============

@router.get("/version")
async def get_version():
    """获取系统版本信息"""
    try:
        return ApiResponse(
            success=True,
            data={
                'version': __version__,
                'description': __description__,
                'features': [
                    '✨ 多 Endpoint 代理服务',
                    '⚡ 智能负载均衡',
                    '🔄 自动故障转移',
                    '📊 实时健康监控',
                    '🎯 配置热更新',
                ]
            }
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取版本信息失败: {str(e)}"
        )


@router.get("/models")
async def get_available_models():
    """获取所有可用的 Claude 模型列表"""
    try:
        models = get_all_models_dict()
        return ApiResponse(
            success=True,
            data={
                'models': models,
                'total': len(models)
            }
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取模型列表失败: {str(e)}"
        )


@router.get("/model-config")
async def get_model_config():
    """获取当前模型配置"""
    if not _config_manager:
        raise HTTPException(status_code=500, detail="配置管理器未初始化")

    try:
        config = {
            'test_model': _config_manager.settings.get('test_model', 'claude-3-5-haiku-20241022'),
            'proxy_model_mode': _config_manager.settings.get('proxy_model_mode', 'passthrough'),
            'proxy_model_override': _config_manager.settings.get(
                'proxy_model_override',
                'claude-3-5-sonnet-20241022'
            )
        }

        return ApiResponse(
            success=True,
            data=config
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取模型配置失败: {str(e)}"
        )


@router.post("/model-config")
async def update_model_config(request: ModelConfigRequest):
    """更新模型配置（立即生效，无需重启）"""
    if not _config_manager:
        raise HTTPException(status_code=500, detail="配置管理器未初始化")

    try:
        # 更新配置
        if request.test_model is not None:
            _config_manager.settings['test_model'] = request.test_model

        if request.proxy_model_mode is not None:
            if request.proxy_model_mode not in ['passthrough', 'override']:
                return ApiResponse(
                    success=False,
                    message=f"无效的代理模型模式: {request.proxy_model_mode}"
                )
            _config_manager.settings['proxy_model_mode'] = request.proxy_model_mode

        if request.proxy_model_override is not None:
            _config_manager.settings['proxy_model_override'] = request.proxy_model_override

        # 保存配置到文件
        _config_manager._save_local_cache()

        # 热更新：通知代理服务器和健康监控器
        # 配置已经通过共享的 _config_manager 实例自动生效
        # 代理服务器在每次请求时都会读取最新的 settings
        # 健康监控器在下次检查时会使用新的 test_model

        return ApiResponse(
            success=True,
            message="模型配置已更新并立即生效！✨",
            data={
                'test_model': _config_manager.settings.get('test_model'),
                'proxy_model_mode': _config_manager.settings.get('proxy_model_mode'),
                'proxy_model_override': _config_manager.settings.get('proxy_model_override'),
                'note': '配置已立即生效，无需重启服务'
            }
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"更新模型配置失败: {str(e)}"
        )


@router.get("/settings")
async def get_system_settings():
    """获取系统设置"""
    if not _config_manager:
        raise HTTPException(status_code=500, detail="配置管理器未初始化")

    try:
        # 返回所有设置（隐藏敏感信息）
        settings = dict(_config_manager.settings)

        return ApiResponse(
            success=True,
            data=settings
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取系统设置失败: {str(e)}"
        )
