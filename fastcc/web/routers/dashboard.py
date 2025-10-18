"""
仪表盘 API 路由
提供系统概览和统计信息
"""

from fastapi import APIRouter, HTTPException
from ..models import ApiResponse
from ..utils import to_dict, to_dict_list
from fastcc.core.config import ConfigManager
from fastcc.core.endpoint_group_manager import EndpointGroupManager
import os

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary():
    """获取仪表盘概览数据"""
    try:
        config_manager = ConfigManager()
        group_manager = EndpointGroupManager(config_manager)

        # 第一步：安全地获取配置列表
        try:
            profiles = to_dict_list(config_manager.list_profiles())
        except Exception as e:
            raise Exception(f"获取配置列表失败: {str(e)}")

        # 第二步：安全地获取当前活跃配置（最近使用的配置）
        try:
            current_profile = None
            latest_time = None

            for profile in config_manager.list_profiles():
                if profile.last_used:
                    if latest_time is None or profile.last_used > latest_time:
                        latest_time = profile.last_used
                        current_profile = profile

            active_profile_dict = to_dict(current_profile) if current_profile else None
        except Exception as e:
            raise Exception(f"获取活跃配置失败: {str(e)}")

        # 统计信息
        total_configs = len(profiles)
        active_config = active_profile_dict.get('name') if active_profile_dict else None

        # 获取存储后端名称（友好显示）
        storage_backend_type = config_manager.settings.get('storage_backend_type', 'local')
        storage_backend_map = {
            'github': 'GitHub',
            'cloud': '云盘',
            'local': '本地',
            'jsonbin': 'JSONBin',
            'gist': 'GitHub Gist'
        }
        storage_backend = storage_backend_map.get(storage_backend_type, '本地')

        # 检查代理服务状态
        proxy_running = False
        proxy_pid = None
        try:
            import json
            import psutil
            pid_file = os.path.expanduser("~/.fastcc/proxy.pid")
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    content = f.read().strip()

                    # 尝试解析 JSON 格式 (新格式)
                    try:
                        pid_data = json.loads(content)
                        proxy_pid = pid_data['pid']
                    except (json.JSONDecodeError, KeyError):
                        # 回退到旧格式
                        if ':' in content:
                            proxy_pid = int(content.split(':')[0])
                        else:
                            proxy_pid = int(content)

                    # 检查进程是否存在
                    if psutil.pid_exists(proxy_pid):
                        proxy_running = True
        except Exception as e:
            # 代理状态检查失败不影响整体
            pass

        # Endpoint 健康统计 - 注意：这里不再统计，因为前端会直接调用 /api/health/status
        # 保留这个字段是为了向后兼容，但数据应该从健康监控 API 获取
        # 前端会使用 useQuery 调用 api.health.status 来获取准确的健康数据

        # 获取 EndpointGroup 列表
        endpoint_groups = []
        try:
            groups = group_manager.list_groups()
            for group in groups:
                endpoint_groups.append({
                    "name": group.name,
                    "description": group.description,
                    "primary_configs": group.primary_configs,
                    "secondary_configs": group.secondary_configs,
                    "created_at": group.created_at,
                    "updated_at": group.updated_at
                })
        except Exception as e:
            # EndpointGroup 获取失败不影响整体
            pass

        return ApiResponse(
            success=True,
            data={
                "total_configs": total_configs,
                "active_config": active_config,
                "storage_backend": storage_backend,
                "proxy_status": {
                    "running": proxy_running,
                    "pid": proxy_pid
                },
                "endpoint_groups": endpoint_groups
            }
        )
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/activity")
async def get_activity_log():
    """获取最近活动日志"""
    # TODO: 实现活动日志功能
    return ApiResponse(
        success=True,
        data=[]
    )
