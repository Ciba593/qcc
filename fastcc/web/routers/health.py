"""
健康监控 API 路由
对应 CLI: health test/metrics/status/history/config
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
from ..models import ApiResponse, HealthStatusModel
from ..utils import to_dict, to_dict_list
from fastcc.core.config import ConfigManager
from fastcc.core.endpoint_group_manager import EndpointGroupManager
from fastcc.proxy.health_monitor import HealthMonitor
import json
from pathlib import Path

router = APIRouter()

# 全局依赖（需要由应用启动时注入）
_config_manager: Optional[ConfigManager] = None
_health_monitor: Optional[HealthMonitor] = None
_failure_queue = None
_proxy_server = None


class MoveNodeRequest(BaseModel):
    """移动节点请求"""
    config_name: str
    to_type: str  # "primary", "secondary", "disabled", "retry_queue"


class AddNodeRequest(BaseModel):
    """添加节点请求"""
    config_name: str
    node_type: str  # "primary" or "secondary"


class RemoveNodeRequest(BaseModel):
    """移除节点请求"""
    config_name: str


class ReloadConfigRequest(BaseModel):
    """重新加载配置请求"""
    pass


def set_health_dependencies(
    config_manager: ConfigManager,
    health_monitor: HealthMonitor = None,
    failure_queue=None,
    proxy_server=None
):
    """设置健康监控依赖

    Args:
        config_manager: 配置管理器实例
        health_monitor: 健康监控器实例（可选）
        failure_queue: 失败队列实例（可选）
        proxy_server: 代理服务器实例（可选）
    """
    global _config_manager, _health_monitor, _failure_queue, _proxy_server
    _config_manager = config_manager
    _health_monitor = health_monitor
    _failure_queue = failure_queue
    _proxy_server = proxy_server


def get_config_manager() -> ConfigManager:
    """获取配置管理器"""
    if _config_manager is None:
        raise HTTPException(status_code=500, detail="配置管理器未初始化")
    return _config_manager


def get_health_monitor() -> Optional[HealthMonitor]:
    """获取健康监控器"""
    return _health_monitor


def get_failure_queue():
    """获取失败队列"""
    return _failure_queue


def get_proxy_server():
    """获取代理服务器"""
    return _proxy_server


@router.get("/status")
async def get_health_status(
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """获取所有 endpoint 的健康状态

    Returns:
        健康状态统计和详细列表
    """
    try:
        import aiohttp

        # 1. 检查代理是否正在运行
        pid_file = Path.home() / '.fastcc' / 'proxy.pid'
        proxy_running = False

        if pid_file.exists():
            try:
                import psutil
                with open(pid_file, 'r') as f:
                    content = f.read().strip()
                    pid_data = json.loads(content)
                    pid = pid_data['pid']

                    if psutil.pid_exists(pid):
                        proxy_running = True
            except Exception:
                pass

        # 2. 如果代理运行中，从运行时获取健康数据
        if proxy_running:
            try:
                proxy_host = pid_data.get('host', '127.0.0.1')
                proxy_port = pid_data.get('port', 7860)
                proxy_stats_url = f"http://{proxy_host}:{proxy_port}/__qcc__/stats"

                async with aiohttp.ClientSession() as session:
                    async with session.get(proxy_stats_url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            stats = await response.json()

                            # 从统计数据中提取节点信息
                            all_endpoints = stats.get('endpoints', [])

                            # 统计健康状态
                            healthy_count = 0
                            degraded_count = 0
                            unhealthy_count = 0
                            unknown_count = 0

                            endpoint_status_list = []

                            for endpoint in all_endpoints:
                                health_status = endpoint.get('health_status', {})
                                status = health_status.get('status', 'unknown')

                                if status == 'healthy':
                                    healthy_count += 1
                                elif status == 'degraded':
                                    degraded_count += 1
                                elif status == 'unhealthy':
                                    unhealthy_count += 1
                                else:
                                    unknown_count += 1

                                endpoint_status_list.append({
                                    'endpoint_id': endpoint.get('id'),
                                    'base_url': endpoint.get('base_url'),
                                    'status': status,
                                    'enabled': endpoint.get('enabled', True),
                                    'last_check': health_status.get('last_check'),
                                    'consecutive_failures': health_status.get('consecutive_failures', 0),
                                    'success_rate': health_status.get('success_rate', 0.0),
                                    'avg_response_time': health_status.get('avg_response_time', 0.0),
                                    'total_requests': health_status.get('total_requests', 0),
                                    'failed_requests': health_status.get('failed_requests', 0),
                                    'priority': endpoint.get('priority', 1),
                                })

                            return ApiResponse(
                                success=True,
                                data={
                                    'summary': {
                                        'healthy': healthy_count,
                                        'degraded': degraded_count,
                                        'unhealthy': unhealthy_count,
                                        'unknown': unknown_count,
                                        'total': len(all_endpoints)
                                    },
                                    'endpoints': endpoint_status_list
                                }
                            )
            except Exception as e:
                # 如果获取运行时数据失败，返回空数据
                pass

        # 3. 代理未运行或获取失败，返回空数据
        return ApiResponse(
            success=True,
            data={
                'summary': {
                    'healthy': 0,
                    'degraded': 0,
                    'unhealthy': 0,
                    'unknown': 0,
                    'total': 0
                },
                'endpoints': []
            },
            message='代理服务未运行，无健康监控数据' if not proxy_running else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取健康状态失败: {str(e)}")


@router.post("/test")
async def test_health(
    endpoint_id: Optional[str] = None,
    config_manager: ConfigManager = Depends(get_config_manager),
    health_monitor: Optional[HealthMonitor] = Depends(get_health_monitor)
):
    """执行健康测试

    Args:
        endpoint_id: 可选，指定要测试的 endpoint ID，如果不指定则测试所有

    Returns:
        测试结果
    """
    try:
        # 获取所有 endpoints
        all_endpoints = []
        profiles = config_manager.list_profiles()

        for profile_name in profiles:
            profile = config_manager.get_profile(profile_name)
            if profile and hasattr(profile, 'endpoints') and profile.endpoints:
                all_endpoints.extend(profile.endpoints)

        if not all_endpoints:
            return ApiResponse(
                success=False,
                message="没有可用的 endpoint 进行测试"
            )

        # 过滤要测试的 endpoints
        if endpoint_id:
            test_endpoints = [ep for ep in all_endpoints if ep.id == endpoint_id]
            if not test_endpoints:
                raise HTTPException(status_code=404, detail=f"未找到 endpoint: {endpoint_id}")
        else:
            test_endpoints = [ep for ep in all_endpoints if ep.enabled]

        # 如果有健康监控器，使用它来测试
        if health_monitor:
            await health_monitor.perform_health_check(test_endpoints)

            # 收集测试结果
            results = []
            for endpoint in test_endpoints:
                results.append({
                    'endpoint_id': endpoint.id,
                    'base_url': endpoint.base_url,
                    'status': endpoint.health_status['status'],
                    'response_time': endpoint.health_status.get('avg_response_time', 0),
                    'last_check': endpoint.health_status.get('last_check')
                })

            return ApiResponse(
                success=True,
                data=results,
                message=f"成功测试 {len(test_endpoints)} 个 endpoint"
            )
        else:
            # 没有健康监控器，返回简单检查
            return ApiResponse(
                success=True,
                data=[{
                    'endpoint_id': ep.id,
                    'base_url': ep.base_url,
                    'status': 'unknown',
                    'message': '健康监控器未启用'
                } for ep in test_endpoints],
                message="健康监控器未启用，无法执行完整测试"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行健康测试失败: {str(e)}")


@router.get("/metrics")
async def get_metrics(
    endpoint_id: Optional[str] = None,
    health_monitor: Optional[HealthMonitor] = Depends(get_health_monitor)
):
    """获取性能指标

    Args:
        endpoint_id: 可选，指定 endpoint ID，如果不指定则返回所有指标

    Returns:
        性能指标数据
    """
    try:
        if not health_monitor:
            return ApiResponse(
                success=True,
                data=[],
                message="健康监控器未启用"
            )

        # 获取性能指标
        metrics = health_monitor.get_metrics(endpoint_id)

        if endpoint_id:
            # 单个 endpoint 的指标
            return ApiResponse(
                success=True,
                data=metrics
            )
        else:
            # 所有 endpoint 的指标
            metrics_list = [
                {
                    'endpoint_id': ep_id,
                    **metrics_data
                }
                for ep_id, metrics_data in metrics.items()
            ]

            return ApiResponse(
                success=True,
                data=metrics_list
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")


@router.get("/history")
async def get_health_history(
    endpoint_id: Optional[str] = None,
    limit: int = 100
):
    """获取健康检查历史

    Args:
        endpoint_id: 可选，指定 endpoint ID
        limit: 返回记录数限制

    Returns:
        历史记录
    """
    # TODO: 实现历史记录功能（需要持久化存储）
    return ApiResponse(
        success=True,
        data=[],
        message="历史记录功能开发中"
    )


@router.get("/runtime")
async def get_runtime_status(
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """获取当前代理运行时状态

    Returns:
        当前代理运行状态，包括：
        - 当前激活的 EndpointGroup
        - 主节点列表及状态（实时数据）
        - 副节点列表及状态（实时数据）
        - 失败队列中的节点
    """
    try:
        import aiohttp
        # 1. 检查代理是否正在运行
        pid_file = Path.home() / '.fastcc' / 'proxy.pid'
        proxy_running = False
        cluster_name = None

        if pid_file.exists():
            try:
                import psutil
                with open(pid_file, 'r') as f:
                    content = f.read().strip()
                    pid_data = json.loads(content)
                    pid = pid_data['pid']
                    cluster_name = pid_data.get('cluster_name')

                    if psutil.pid_exists(pid):
                        proxy_running = True
            except Exception as e:
                pass

        if not proxy_running:
            return ApiResponse(
                success=True,
                data={
                    'proxy_running': False,
                    'message': '代理服务未运行'
                }
            )

        # 1.5. 从代理服务器获取实时统计数据
        proxy_host = pid_data.get('host', '127.0.0.1')
        proxy_port = pid_data.get('port', 7860)
        proxy_stats_url = f"http://{proxy_host}:{proxy_port}/__qcc__/stats"

        proxy_stats = {}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(proxy_stats_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        proxy_stats = await resp.json()
        except Exception as e:
            # 如果无法获取统计数据，记录日志但继续
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"无法从代理服务器获取统计数据: {e}")

        # 构建 endpoint 到实时状态的映射（同时使用 id 和 base_url）
        endpoints_runtime_map_by_id = {}
        endpoints_runtime_map_by_url = {}
        last_used_endpoint_id = None
        if proxy_stats and 'endpoints' in proxy_stats:
            for ep_stat in proxy_stats['endpoints']:
                endpoints_runtime_map_by_id[ep_stat['id']] = ep_stat
                # 使用 base_url 作为备用匹配键
                endpoints_runtime_map_by_url[ep_stat['base_url']] = ep_stat
            # 获取最后使用的 endpoint ID
            last_used_endpoint_id = proxy_stats.get('last_used_endpoint_id')

        # 2. 获取 EndpointGroup 信息
        group_manager = EndpointGroupManager(config_manager)

        if not cluster_name:
            return ApiResponse(
                success=True,
                data={
                    'proxy_running': True,
                    'message': '代理正在运行，但未使用 EndpointGroup'
                }
            )

        group = group_manager.get_group(cluster_name)
        if not group:
            return ApiResponse(
                success=False,
                message=f'未找到 EndpointGroup: {cluster_name}'
            )

        # 辅助函数：构建节点信息，添加 is_active 标识
        def build_node_info(endpoint_id, base_url, config_name, runtime_data=None, static_data=None):
            """构建节点信息字典"""
            node_info = {
                'config_name': config_name,
                'endpoint_id': endpoint_id,
                'base_url': base_url,
                'is_active': endpoint_id == last_used_endpoint_id  # 是否为当前激活的节点
            }

            if runtime_data:
                # 使用实时数据
                health = runtime_data.get('health_status', {})
                node_info.update({
                    'enabled': runtime_data.get('enabled', True),
                    'status': health.get('status', 'unknown'),
                    'success_rate': health.get('success_rate', 0.0),
                    'avg_response_time': health.get('avg_response_time', 0.0),
                    'total_requests': health.get('total_requests', 0),
                    'failed_requests': health.get('failed_requests', 0),
                    'consecutive_failures': health.get('consecutive_failures', 0),
                    'last_check': health.get('last_check'),
                    'last_error': health.get('last_error'),
                    'priority': runtime_data.get('priority', 0)
                })
            elif static_data:
                # 使用静态配置
                node_info.update({
                    'enabled': static_data.get('enabled', True),
                    'status': static_data.get('status', 'unknown'),
                    'success_rate': static_data.get('success_rate', 0.0),
                    'avg_response_time': static_data.get('avg_response_time', 0.0),
                    'total_requests': static_data.get('total_requests', 0),
                    'failed_requests': static_data.get('failed_requests', 0),
                    'consecutive_failures': static_data.get('consecutive_failures', 0),
                    'last_check': static_data.get('last_check'),
                    'last_error': static_data.get('last_error'),
                    'priority': static_data.get('priority', 0)
                })
            else:
                # 默认值
                node_info.update({
                    'enabled': True,
                    'status': 'unknown',
                    'success_rate': 0.0,
                    'avg_response_time': 0.0,
                    'total_requests': 0,
                    'failed_requests': 0,
                    'consecutive_failures': 0,
                    'last_check': None,
                    'last_error': None,
                    'priority': 0
                })

            return node_info

        # 3. 收集主节点状态（优先使用实时数据）
        primary_nodes = []
        for config_name in group.primary_configs:
            profile = config_manager.get_profile(config_name)
            if not profile:
                continue

            # 兼容两种模式：新模式(有endpoints列表) 和 旧模式(只有base_url)
            if profile.endpoints:
                # 新模式：有 endpoints 列表
                for endpoint in profile.endpoints:
                    # 优先使用代理服务器的实时数据，先用 ID 匹配，再用 base_url 匹配
                    runtime_data = endpoints_runtime_map_by_id.get(endpoint.id)
                    if not runtime_data:
                        runtime_data = endpoints_runtime_map_by_url.get(endpoint.base_url)

                    # 使用辅助函数构建节点信息
                    node_info = build_node_info(
                        endpoint_id=endpoint.id,
                        base_url=endpoint.base_url,
                        config_name=config_name,
                        runtime_data=runtime_data
                    )
                    primary_nodes.append(node_info)
            else:
                # 旧模式：只有 base_url 和 api_key，需要生成与 Endpoint 类相同的稳定 ID
                import hashlib
                # 使用与 Endpoint._generate_stable_id 相同的逻辑
                content = f"{profile.base_url}|{profile.api_key}".encode('utf-8')
                endpoint_id = hashlib.sha256(content).hexdigest()[:8]

                # 尝试从实时数据中查找
                runtime_data = endpoints_runtime_map_by_id.get(endpoint_id)
                if not runtime_data:
                    runtime_data = endpoints_runtime_map_by_url.get(profile.base_url)

                # 使用辅助函数构建节点信息
                node_info = build_node_info(
                    endpoint_id=endpoint_id,
                    base_url=profile.base_url,
                    config_name=config_name,
                    runtime_data=runtime_data
                )
                primary_nodes.append(node_info)

        # 4. 收集副节点状态（优先使用实时数据）
        secondary_nodes = []
        for config_name in group.secondary_configs:
            profile = config_manager.get_profile(config_name)
            if not profile:
                continue

            # 兼容两种模式
            if profile.endpoints:
                # 新模式：有 endpoints 列表
                for endpoint in profile.endpoints:
                    # 优先使用代理服务器的实时数据，先用 ID 匹配，再用 base_url 匹配
                    runtime_data = endpoints_runtime_map_by_id.get(endpoint.id)
                    if not runtime_data:
                        runtime_data = endpoints_runtime_map_by_url.get(endpoint.base_url)

                    # 使用辅助函数构建节点信息
                    node_info = build_node_info(
                        endpoint_id=endpoint.id,
                        base_url=endpoint.base_url,
                        config_name=config_name,
                        runtime_data=runtime_data
                    )
                    secondary_nodes.append(node_info)
            else:
                # 旧模式：只有 base_url 和 api_key，需要生成与 Endpoint 类相同的稳定 ID
                import hashlib
                # 使用与 Endpoint._generate_stable_id 相同的逻辑
                content = f"{profile.base_url}|{profile.api_key}".encode('utf-8')
                endpoint_id = hashlib.sha256(content).hexdigest()[:8]

                # 尝试从实时数据中查找
                runtime_data = endpoints_runtime_map_by_id.get(endpoint_id)
                if not runtime_data:
                    runtime_data = endpoints_runtime_map_by_url.get(profile.base_url)

                # 使用辅助函数构建节点信息
                node_info = build_node_info(
                    endpoint_id=endpoint_id,
                    base_url=profile.base_url,
                    config_name=config_name,
                    runtime_data=runtime_data
                )
                secondary_nodes.append(node_info)

        # 5. 获取失败队列信息（从代理服务器的内存中获取）
        retry_queue = []
        failed_endpoint_ids = proxy_stats.get('failed_endpoints', []) if proxy_stats else []
        endpoint_verify_counts = proxy_stats.get('endpoint_verify_counts', {}) if proxy_stats else {}

        if failed_endpoint_ids:
            # 从实时数据中查找失败的节点
            for endpoint_id in failed_endpoint_ids:
                # 先从实时数据映射中查找
                runtime_data = endpoints_runtime_map_by_id.get(endpoint_id)
                if not runtime_data:
                    runtime_data = endpoints_runtime_map_by_url.get(endpoint_id)

                if runtime_data:
                    # 查找对应的 config_name（从 primary 和 secondary 配置中查找）
                    config_name = 'unknown'
                    base_url = runtime_data.get('base_url', 'unknown')

                    # 遍历所有配置查找匹配的 endpoint
                    all_config_names = group.primary_configs + group.secondary_configs
                    for cfg_name in all_config_names:
                        profile = config_manager.get_profile(cfg_name)
                        if not profile:
                            continue

                        # 检查是否匹配
                        if profile.endpoints:
                            # 新模式：检查 endpoints 列表
                            for endpoint in profile.endpoints:
                                if endpoint.id == endpoint_id or endpoint.base_url == base_url:
                                    config_name = cfg_name
                                    break
                        else:
                            # 旧模式：检查 base_url
                            if profile.base_url == base_url:
                                config_name = cfg_name
                                break

                        if config_name != 'unknown':
                            break

                    # 使用 build_node_info 辅助函数构建完整的节点信息
                    node_info = build_node_info(
                        endpoint_id=endpoint_id,
                        base_url=base_url,
                        config_name=config_name,
                        runtime_data=runtime_data
                    )
                    # 失败节点特定字段
                    node_info['is_active'] = False  # 失败节点不会是激活状态
                    # 从 endpoint_verify_counts 获取真实的验证次数
                    node_info['retry_count'] = endpoint_verify_counts.get(endpoint_id, 0)
                    node_info['next_retry'] = None  # 固定60秒后重试

                    retry_queue.append(node_info)

        return ApiResponse(
            success=True,
            data={
                'proxy_running': True,
                'cluster_name': cluster_name,
                'endpoint_group': {
                    'name': group.name,
                    'description': group.description,
                    'enabled': group.enabled
                },
                'primary_nodes': primary_nodes,
                'secondary_nodes': secondary_nodes,
                'retry_queue': retry_queue,
                'summary': {
                    'primary_count': len(primary_nodes),
                    'secondary_count': len(secondary_nodes),
                    'retry_count': len(retry_queue),
                    'primary_healthy': sum(1 for n in primary_nodes if n['status'] == 'healthy'),
                    'secondary_healthy': sum(1 for n in secondary_nodes if n['status'] == 'healthy')
                }
            }
        )

    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"获取运行时状态失败: {str(e)}\n\n{traceback.format_exc()}"
        )


@router.post("/runtime/move-node")
async def move_node(
    request: MoveNodeRequest,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """移动节点到不同的位置

    Args:
        request: 移动请求，包含 config_name 和 to_type

    Returns:
        操作结果
    """
    try:
        # 获取当前运行的 cluster
        pid_file = Path.home() / '.fastcc' / 'proxy.pid'
        if not pid_file.exists():
            raise HTTPException(status_code=400, detail="代理服务未运行")

        with open(pid_file, 'r') as f:
            pid_data = json.loads(f.read().strip())
            cluster_name = pid_data.get('cluster_name')

        if not cluster_name:
            raise HTTPException(status_code=400, detail="代理未使用 EndpointGroup")

        group_manager = EndpointGroupManager(config_manager)
        group = group_manager.get_group(cluster_name)

        if not group:
            raise HTTPException(status_code=404, detail=f"未找到 EndpointGroup: {cluster_name}")

        config_name = request.config_name
        to_type = request.to_type

        # 从当前位置移除
        if config_name in group.primary_configs:
            group.remove_primary_config(config_name)
        if config_name in group.secondary_configs:
            group.remove_secondary_config(config_name)

        # 移动到新位置
        if to_type == "primary":
            group.add_primary_config(config_name)
        elif to_type == "secondary":
            group.add_secondary_config(config_name)
        elif to_type == "disabled":
            # 禁用 endpoint
            profile = config_manager.get_profile(config_name)
            if profile and profile.endpoints:
                for endpoint in profile.endpoints:
                    endpoint.enabled = False
            config_manager._save_local_cache()
        elif to_type == "retry_queue":
            # 手动添加到重试队列
            failure_queue = get_failure_queue()
            if failure_queue:
                profile = config_manager.get_profile(config_name)
                if profile and profile.endpoints:
                    for endpoint in profile.endpoints:
                        import asyncio
                        asyncio.create_task(
                            failure_queue.add_failed_endpoint(endpoint.id, "手动移动")
                        )

        # 保存更改
        group_manager.save_group(group)

        # 同步到远程
        if config_manager.settings.get('auto_sync'):
            try:
                config_manager.sync_to_cloud()
            except:
                pass

        return ApiResponse(
            success=True,
            message=f"成功将 {config_name} 移动到 {to_type}"
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"移动节点失败: {str(e)}\n\n{traceback.format_exc()}"
        )


@router.post("/runtime/add-node")
async def add_node(
    request: AddNodeRequest,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """添加节点到主节点或副节点

    Args:
        request: 添加请求，包含 config_name 和 node_type

    Returns:
        操作结果
    """
    try:
        # 获取当前运行的 cluster
        pid_file = Path.home() / '.fastcc' / 'proxy.pid'
        if not pid_file.exists():
            raise HTTPException(status_code=400, detail="代理服务未运行")

        with open(pid_file, 'r') as f:
            pid_data = json.loads(f.read().strip())
            cluster_name = pid_data.get('cluster_name')

        if not cluster_name:
            raise HTTPException(status_code=400, detail="代理未使用 EndpointGroup")

        group_manager = EndpointGroupManager(config_manager)
        group = group_manager.get_group(cluster_name)

        if not group:
            raise HTTPException(status_code=404, detail=f"未找到 EndpointGroup: {cluster_name}")

        config_name = request.config_name
        node_type = request.node_type

        # 检查配置是否存在
        profile = config_manager.get_profile(config_name)
        if not profile:
            raise HTTPException(status_code=404, detail=f"配置 {config_name} 不存在")

        # 添加到指定位置
        if node_type == "primary":
            if config_name in group.primary_configs:
                raise HTTPException(status_code=400, detail=f"{config_name} 已在主节点列表中")
            # 从副节点移除（如果存在）
            if config_name in group.secondary_configs:
                group.remove_secondary_config(config_name)
            group.add_primary_config(config_name)
        elif node_type == "secondary":
            if config_name in group.secondary_configs:
                raise HTTPException(status_code=400, detail=f"{config_name} 已在副节点列表中")
            # 从主节点移除（如果存在）
            if config_name in group.primary_configs:
                group.remove_primary_config(config_name)
            group.add_secondary_config(config_name)
        else:
            raise HTTPException(status_code=400, detail=f"无效的节点类型: {node_type}")

        # 保存更改
        group_manager.save_group(group)

        # 同步到远程
        if config_manager.settings.get('auto_sync'):
            try:
                config_manager.sync_to_cloud()
            except:
                pass

        return ApiResponse(
            success=True,
            message=f"成功将 {config_name} 添加到 {node_type}"
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"添加节点失败: {str(e)}\n\n{traceback.format_exc()}"
        )


@router.post("/runtime/remove-node")
async def remove_node(
    request: RemoveNodeRequest,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """从当前 EndpointGroup 中删除节点

    Args:
        request: 删除请求，包含 config_name

    Returns:
        操作结果
    """
    try:
        # 获取当前运行的 cluster
        pid_file = Path.home() / '.fastcc' / 'proxy.pid'
        if not pid_file.exists():
            raise HTTPException(status_code=400, detail="代理服务未运行")

        with open(pid_file, 'r') as f:
            pid_data = json.loads(f.read().strip())
            cluster_name = pid_data.get('cluster_name')

        if not cluster_name:
            raise HTTPException(status_code=400, detail="代理未使用 EndpointGroup")

        group_manager = EndpointGroupManager(config_manager)
        group = group_manager.get_group(cluster_name)

        if not group:
            raise HTTPException(status_code=404, detail=f"未找到 EndpointGroup: {cluster_name}")

        config_name = request.config_name

        # 从主节点或副节点中移除
        removed = False
        if config_name in group.primary_configs:
            group.remove_primary_config(config_name)
            removed = True
        if config_name in group.secondary_configs:
            group.remove_secondary_config(config_name)
            removed = True

        if not removed:
            raise HTTPException(status_code=404, detail=f"节点 {config_name} 不在当前 EndpointGroup 中")

        # 保存更改
        group_manager.save_group(group)

        # 同步到远程
        if config_manager.settings.get('auto_sync'):
            try:
                config_manager.sync_to_cloud()
            except:
                pass

        return ApiResponse(
            success=True,
            message=f"成功从 EndpointGroup 中删除节点 {config_name}"
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"删除节点失败: {str(e)}\n\n{traceback.format_exc()}"
        )
