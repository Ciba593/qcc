"""QCC Proxy Server - 代理服务器主逻辑"""

import asyncio
import json
import logging
import os
from typing import Optional, Dict, Any
from aiohttp import web, ClientSession, ClientTimeout
from datetime import datetime
from pathlib import Path
import signal

logger = logging.getLogger(__name__)


class ProxyServer:
    """QCC 代理服务器

    拦截 Claude Code 的 API 请求并转发到配置的后端 endpoint。
    支持多 endpoint 负载均衡、健康检测和自动故障转移。
    """

    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 7860,
        config_manager=None,
        load_balancer=None,
        priority_manager=None,
        failover_manager=None,
        health_monitor=None,
        failure_queue=None,
        cluster_name: str = None
    ):
        """初始化代理服务器

        Args:
            host: 监听地址 (默认 127.0.0.1)
            port: 监听端口 (默认 7860)
            config_manager: 配置管理器实例
            load_balancer: 负载均衡器实例
            priority_manager: 优先级管理器实例
            failover_manager: 故障转移管理器实例
            health_monitor: 健康监控器实例
            failure_queue: 失败队列实例
            cluster_name: 集群配置名称（可选）
        """
        self.host = host
        self.port = port
        self.config_manager = config_manager
        self.load_balancer = load_balancer
        self.priority_manager = priority_manager
        self.failover_manager = failover_manager
        self.health_monitor = health_monitor
        self.failure_queue = failure_queue
        self.cluster_name = cluster_name

        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.client_session: Optional[ClientSession] = None
        self.running = False
        self._shutting_down = False  # 防止重复关闭

        # 后台任务
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._failover_manager_task: Optional[asyncio.Task] = None
        self._failure_queue_task: Optional[asyncio.Task] = None

        # 关闭事件（延迟初始化，在 start() 中创建）
        self._shutdown_event: Optional[asyncio.Event] = None

        # PID 文件路径
        self.pid_file = Path.home() / '.fastcc' / 'proxy.pid'
        self.log_file = Path.home() / '.fastcc' / 'proxy.log'

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': None,
            'uptime': 0,
            'last_used_endpoint_id': None  # 最后使用的 endpoint ID
        }

        self._setup_routes()
        self._setup_signal_handlers()

    def _setup_routes(self):
        """设置路由"""
        # 添加日志查看 API（使用特殊前缀避免与代理路径冲突）
        self.app.router.add_get('/__qcc__/logs', self.handle_logs)
        self.app.router.add_get('/__qcc__/stats', self.handle_stats_api)

        # 特殊处理：count_tokens 接口（本地实现，不转发到后端）
        self.app.router.add_post('/v1/messages/count_tokens', self.handle_count_tokens)

        # 捕获所有其他路径的所有 HTTP 方法（代理功能）
        # 主要是 /v1/messages 接口
        self.app.router.add_route('*', '/{path:.*}', self.handle_request)

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            if self._shutting_down:
                logger.debug(f"已在关闭中，忽略信号 {signum}")
                return
            logger.info(f"收到信号 {signum}，准备关闭服务器...")
            self._shutting_down = True
            self.running = False

            # 触发关闭事件，唤醒主循环
            try:
                # 尝试多种方式获取事件循环
                loop = None

                # 方法1: 尝试获取运行中的循环
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    pass

                # 方法2: 尝试获取事件循环
                if loop is None:
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        pass

                # 如果找到了循环，触发关闭事件
                if loop and loop.is_running() and self._shutdown_event:
                    logger.info("触发关闭事件...")
                    loop.call_soon_threadsafe(self._shutdown_event.set)
                else:
                    logger.warning("无法获取运行中的事件循环，尝试直接设置事件")
                    # 即使没有循环，也尝试设置事件（可能在某些情况下有用）
                    if self._shutdown_event:
                        self._shutdown_event.set()
            except Exception as e:
                logger.error(f"触发关闭事件失败: {e}", exc_info=True)
                # 失败时也设置事件
                try:
                    if self._shutdown_event:
                        self._shutdown_event.set()
                except:
                    pass

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def handle_request(self, request: web.Request) -> web.Response:
        """处理代理请求，支持自动重试和故障转移

        Args:
            request: 客户端请求

        Returns:
            代理响应
        """
        self.stats['total_requests'] += 1
        request_id = f"req-{self.stats['total_requests']}"

        try:
            logger.info(f"[{request_id}] {request.method} {request.path}")

            # 1. 读取请求体
            body = await request.read()

            # 记录请求参数
            try:
                request_data = json.loads(body.decode('utf-8')) if body else {}
                model = request_data.get('model', 'N/A')
                max_tokens = request_data.get('max_tokens', 'N/A')

                # 记录请求详情
                logger.info(f"[{request_id}] 请求参数: model={model}, max_tokens={max_tokens}")

                # 记录消息摘要（避免日志过长）
                if 'messages' in request_data:
                    msg_count = len(request_data['messages'])
                    logger.info(f"[{request_id}] 消息数量: {msg_count}")
            except Exception as e:
                logger.debug(f"[{request_id}] 解析请求参数失败: {e}")

            # 2. 检查是否需要替换模型（仅对 /v1/messages 请求）
            original_model = None
            if request.path == '/v1/messages' and self.config_manager:
                try:
                    request_data = json.loads(body.decode('utf-8'))
                    original_model = request_data.get('model')
                except:
                    pass
                body = self._maybe_override_model(body)

            # 2. 重试逻辑：尝试所有可用的 endpoint
            max_total_attempts = 5  # 总共最多尝试 5 次（跨多个 endpoint）
            max_per_endpoint = 2   # 单个 endpoint 最多尝试 2 次

            last_response = None
            last_endpoint = None
            failed_endpoints = {}  # {endpoint_id: 失败次数}
            excluded_endpoints = set()  # 已被排除的 endpoint

            for attempt in range(max_total_attempts):
                # 选择 endpoint，排除已失败的
                endpoint = await self._select_endpoint(exclude_ids=excluded_endpoints)
                if not endpoint:
                    logger.warning(f"[{request_id}] 没有更多可用的 endpoint（已排除 {len(excluded_endpoints)} 个）")
                    break  # 没有更多 endpoint 可尝试了

                # 记录尝试次数
                endpoint_id = endpoint.id
                failed_endpoints[endpoint_id] = failed_endpoints.get(endpoint_id, 0)

                if attempt > 0:
                    logger.info(f"[{request_id}] 尝试 {attempt + 1}/{max_total_attempts}, endpoint: {endpoint.id} ({endpoint.base_url})")
                else:
                    logger.info(f"[{request_id}] 选中 endpoint: {endpoint.id} ({endpoint.base_url})")

                # 记录模型信息
                if original_model:
                    try:
                        current_data = json.loads(body.decode('utf-8'))
                        current_model = current_data.get('model', 'N/A')
                        if original_model != current_model:
                            logger.info(f"[{request_id}] 模型已替换: {original_model} -> {current_model}")
                    except:
                        pass

                # 记录最后使用的 endpoint
                self.stats['last_used_endpoint_id'] = endpoint.id
                last_endpoint = endpoint

                # 3. 转发请求
                response = await self._forward_request(
                    endpoint=endpoint,
                    method=request.method,
                    path=request.path,
                    headers=dict(request.headers),
                    body=body,
                    request_id=request_id,
                    original_request=request
                )

                if response:
                    last_response = response
                    # 检查是否成功（只有 200 才算成功）
                    if response.status == 200:
                        self.stats['successful_requests'] += 1
                        logger.info(f"[{request_id}] ✓ 请求成功: HTTP {response.status}, endpoint: {endpoint.id}")
                        return response
                    else:
                        # 非 200 状态码，记录失败
                        failed_endpoints[endpoint_id] += 1
                        logger.warning(
                            f"[{request_id}] ✗ 收到非成功响应: HTTP {response.status}, endpoint: {endpoint.id}"
                        )

                        # 如果这个 endpoint 失败次数达到上限，排除它
                        if failed_endpoints[endpoint_id] >= max_per_endpoint:
                            excluded_endpoints.add(endpoint_id)
                            logger.warning(
                                f"[{request_id}] Endpoint {endpoint.id} 失败 {failed_endpoints[endpoint_id]} 次，"
                                f"暂时排除，尝试其他 endpoint"
                            )
                        continue  # 继续尝试
                else:
                    # 请求失败（超时或异常）
                    failed_endpoints[endpoint_id] += 1
                    logger.error(f"[{request_id}] ✗ 请求失败（无响应），endpoint: {endpoint.id}")

                    # 如果这个 endpoint 失败次数达到上限，排除它
                    if failed_endpoints[endpoint_id] >= max_per_endpoint:
                        excluded_endpoints.add(endpoint_id)
                        logger.warning(
                            f"[{request_id}] Endpoint {endpoint.id} 失败 {failed_endpoints[endpoint_id]} 次，"
                            f"暂时排除，尝试其他 endpoint"
                        )
                    continue  # 继续尝试

            # 所有尝试都失败了
            self.stats['failed_requests'] += 1
            if last_response:
                logger.error(
                    f"[{request_id}] ✗ 尝试了 {len(failed_endpoints)} 个 endpoint，"
                    f"共 {sum(failed_endpoints.values())} 次，全部失败，返回最后响应"
                )
                return last_response
            else:
                logger.error(
                    f"[{request_id}] ✗ 尝试了 {len(failed_endpoints)} 个 endpoint，"
                    f"共 {sum(failed_endpoints.values())} 次，全部失败"
                )
                return web.Response(
                    status=502,
                    text=json.dumps({'error': f'All {len(failed_endpoints)} endpoints failed'}),
                    content_type='application/json'
                )

        except Exception as e:
            self.stats['failed_requests'] += 1
            logger.error(f"[{request_id}] 处理请求异常: {e}", exc_info=True)
            return web.Response(
                status=500,
                text=json.dumps({'error': str(e)}),
                content_type='application/json'
            )

    async def _select_endpoint(self, exclude_ids: set = None):
        """选择 endpoint（通过负载均衡器）

        Args:
            exclude_ids: 要排除的 endpoint ID 集合

        Returns:
            选中的 endpoint，如果没有可用的返回 None
        """
        exclude_ids = exclude_ids or set()

        if self.load_balancer and self.config_manager:
            # 获取当前活跃配置的所有 endpoint
            endpoints = self._get_active_endpoints()

            # 过滤掉被排除的 endpoint
            if exclude_ids:
                endpoints = [ep for ep in endpoints if ep.id not in exclude_ids]
                logger.debug(f"排除 {len(exclude_ids)} 个 endpoint 后，剩余 {len(endpoints)} 个")

            logger.debug(f"可用 endpoints 数量: {len(endpoints)}")
            for ep in endpoints:
                logger.debug(f"  - Endpoint {ep.id}: {ep.base_url}, 健康: {ep.is_healthy()}, 优先级: {ep.priority}")

            if endpoints:
                selected = await self.load_balancer.select_endpoint(endpoints)
                logger.debug(f"负载均衡器选择: {selected.id if selected else 'None'}")
                return selected
            else:
                logger.warning("没有可用的健康 endpoint")

        # 如果没有负载均衡器，使用简单的单配置模式
        if self.config_manager:
            default_profile = self.config_manager.get_default_profile()
            if default_profile:
                # 如果配置有 endpoints，使用第一个未被排除的
                if hasattr(default_profile, 'endpoints') and default_profile.endpoints:
                    for ep in default_profile.endpoints:
                        if ep.id not in exclude_ids:
                            logger.debug(f"使用默认配置的 endpoint: {ep.id}")
                            return ep
                    logger.warning("所有 endpoint 都被排除了")
                    return None
                # 否则从传统字段创建临时 endpoint
                from fastcc.core.endpoint import Endpoint
                temp_ep = Endpoint(
                    base_url=default_profile.base_url,
                    api_key=default_profile.api_key
                )
                if temp_ep.id not in exclude_ids:
                    logger.debug(f"从默认配置创建临时 endpoint")
                    return temp_ep
                else:
                    logger.warning("临时 endpoint 被排除")
                    return None

        logger.error("无法选择 endpoint：没有负载均衡器或配置管理器")
        return None

    def _get_active_endpoints(self):
        """获取当前活跃配置的所有健康 endpoint"""
        endpoints = []
        if not self.config_manager:
            logger.warning("没有 config_manager，无法获取 endpoints")
            return endpoints

        # 如果指定了集群配置，使用该配置的 endpoints
        if self.cluster_name:
            logger.debug(f"使用集群配置: {self.cluster_name}")
            profile = self.config_manager.get_profile(self.cluster_name)
            if profile and hasattr(profile, 'endpoints') and profile.endpoints:
                total_count = len(profile.endpoints)
                # 只返回启用且健康的 endpoint
                endpoints = [
                    ep for ep in profile.endpoints
                    if ep.enabled and ep.is_healthy()
                ]
                logger.info(f"集群 '{self.cluster_name}': 总 {total_count} 个 endpoint, 健康 {len(endpoints)} 个")
                for ep in profile.endpoints:
                    logger.debug(f"  Endpoint {ep.id}: enabled={ep.enabled}, healthy={ep.is_healthy()}, status={ep.health_status}")
                return endpoints
            else:
                logger.warning(f"集群配置 '{self.cluster_name}' 没有 endpoints")

        # 否则，优先使用 priority_manager 获取活跃配置
        profile_name = None
        if self.priority_manager:
            profile_name = self.priority_manager.get_active_profile()
            logger.debug(f"priority_manager 活跃配置: {profile_name}")

        # 如果没有优先级配置，使用默认配置
        if not profile_name:
            profile = self.config_manager.get_default_profile()
            logger.debug(f"使用默认配置: {profile.name if profile else 'None'}")
        else:
            profile = self.config_manager.get_profile(profile_name)

        if not profile:
            logger.warning("没有可用的配置")
            return endpoints

        # 获取配置的 endpoints
        if hasattr(profile, 'endpoints') and profile.endpoints:
            total_count = len(profile.endpoints)
            # 只返回启用且健康的 endpoint
            endpoints = [
                ep for ep in profile.endpoints
                if ep.enabled and ep.is_healthy()
            ]
            logger.info(f"配置 '{profile.name}': 总 {total_count} 个 endpoint, 健康 {len(endpoints)} 个")
            for ep in profile.endpoints:
                logger.debug(f"  Endpoint {ep.id}: enabled={ep.enabled}, healthy={ep.is_healthy()}, status={ep.health_status}")
        else:
            logger.debug(f"配置 '{profile.name}' 没有 endpoints 属性")

        return endpoints

    def _get_all_endpoints(self):
        """获取所有 endpoint（包括不健康的）

        Returns:
            所有 endpoint 列表
        """
        endpoints = []
        if not self.config_manager:
            return endpoints

        # 如果指定了集群配置，使用该配置的 endpoints
        if self.cluster_name:
            profile = self.config_manager.get_profile(self.cluster_name)
            if profile and hasattr(profile, 'endpoints') and profile.endpoints:
                # 返回所有 endpoint（不过滤健康状态）
                return list(profile.endpoints)

        # 否则，优先使用 priority_manager 获取活跃配置
        profile_name = None
        if self.priority_manager:
            profile_name = self.priority_manager.get_active_profile()

        # 如果没有优先级配置，使用默认配置
        if not profile_name:
            profile = self.config_manager.get_default_profile()
        else:
            profile = self.config_manager.get_profile(profile_name)

        if not profile:
            return endpoints

        # 获取配置的 endpoints
        if hasattr(profile, 'endpoints') and profile.endpoints:
            # 返回所有 endpoint（不过滤健康状态）
            endpoints = list(profile.endpoints)

        return endpoints

    async def _forward_request(
        self,
        endpoint,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: bytes,
        request_id: str,
        original_request: web.Request = None
    ) -> Optional[web.Response]:
        """转发请求到目标 endpoint

        Args:
            endpoint: 目标 endpoint
            method: HTTP 方法
            path: 请求路径
            headers: 请求头
            body: 请求体
            request_id: 请求 ID
            original_request: 原始 Request 对象（用于流式响应）

        Returns:
            代理响应，失败返回 None
        """
        # 检查 session 是否存在且未关闭
        if not self.client_session or self.client_session.closed:
            # 如果旧 session 存在但已关闭，先清理
            if self.client_session:
                try:
                    await self.client_session.close()
                except:
                    pass

            # 创建新的 session，配置连接池避免连接问题
            from aiohttp import TCPConnector
            self.client_session = ClientSession(
                timeout=ClientTimeout(total=300),  # 总超时 5 分钟
                connector=TCPConnector(
                    limit=100,  # 最大连接数
                    limit_per_host=10,  # 每个主机最大连接数（降低以避免复用冲突）
                    ttl_dns_cache=300,  # DNS 缓存 5 分钟
                    force_close=True,  # 不复用连接，避免 "closing transport" 错误
                    enable_cleanup_closed=True  # 自动清理关闭的连接
                    # 注意：force_close=True 时不能设置 keepalive_timeout
                )
            )
            logger.debug(f"[{request_id}] 创建新的 ClientSession (force_close=True)")

        try:
            # 构建目标 URL
            target_url = f"{endpoint.base_url}{path}"

            # 记录完整请求信息
            logger.info(f"[{request_id}] 转发到: {target_url}")

            # 解析并记录请求模型
            try:
                if body:
                    request_data = json.loads(body.decode('utf-8'))
                    request_model = request_data.get('model', 'N/A')
                    logger.info(f"[{request_id}] 使用模型: {request_model}")
            except:
                pass

            # 修改请求头：同时支持 Anthropic 和 OpenAI 格式
            forward_headers = headers.copy()

            # 同时发送两种认证方式，确保兼容性
            # Anthropic 原生格式
            forward_headers['x-api-key'] = endpoint.api_key
            forward_headers['anthropic-version'] = '2023-06-01'

            # OpenAI 兼容格式
            forward_headers['Authorization'] = f'Bearer {endpoint.api_key}'

            # 移除不需要的头
            forward_headers.pop('Host', None)
            forward_headers.pop('Connection', None)

            # 记录请求开始时间
            start_time = datetime.now()

            # 发送请求
            async with self.client_session.request(
                method=method,
                url=target_url,
                headers=forward_headers,
                data=body,
                timeout=ClientTimeout(total=300, sock_read=60)  # 总超时 5 分钟，读取超时 1 分钟
            ) as response:
                # 检查是否为流式响应
                is_streaming = (
                    response.headers.get('Content-Type', '').startswith('text/event-stream') or
                    response.headers.get('Transfer-Encoding') == 'chunked' or
                    'stream' in response.headers.get('Content-Type', '').lower()
                )

                if is_streaming and original_request:
                    # 流式响应：创建 StreamResponse 并逐块转发
                    proxy_response = web.StreamResponse(
                        status=response.status,
                        headers=dict(response.headers)
                    )
                    await proxy_response.prepare(original_request)

                    try:
                        # 逐块读取并转发
                        async for chunk in response.content.iter_chunked(8192):
                            await proxy_response.write(chunk)

                        await proxy_response.write_eof()

                        # 计算响应时间
                        response_time = (datetime.now() - start_time).total_seconds() * 1000

                        # 更新 endpoint 健康状态
                        await endpoint.update_health_status(
                            status='healthy',
                            increment_requests=True,
                            is_failure=False,
                            response_time=response_time
                        )

                        logger.info(
                            f"[{request_id}] ✓ 流式响应完成: HTTP {response.status}, "
                            f"耗时: {response_time:.2f}ms, endpoint: {endpoint.id}"
                        )

                        return proxy_response

                    except Exception as stream_error:
                        # 流式传输过程中出错
                        logger.warning(
                            f"[{request_id}] ⚠ 流式传输中断: {str(stream_error)}, "
                            f"endpoint: {endpoint.id}"
                        )
                        # 尝试结束响应
                        try:
                            await proxy_response.write_eof()
                        except:
                            pass
                        # 返回 None，让上层重试
                        return None
                else:
                    # 非流式响应：一次性读取
                    response_body = await response.read()

                    # 计算响应时间
                    response_time = (datetime.now() - start_time).total_seconds() * 1000

                    # 检查状态码，只有 200 才算成功
                    is_success = response.status == 200

                    # 更新 endpoint 健康状态
                    if is_success:
                        await endpoint.update_health_status(
                            status='healthy',
                            increment_requests=True,
                            is_failure=False,
                            response_time=response_time
                        )
                        # 记录成功响应的部分信息
                        try:
                            response_json = json.loads(response_body.decode('utf-8'))
                            response_model = response_json.get('model', 'N/A')
                            usage = response_json.get('usage', {})
                            input_tokens = usage.get('input_tokens', 0)
                            output_tokens = usage.get('output_tokens', 0)
                            logger.info(
                                f"[{request_id}] ✓ 响应成功: HTTP {response.status}, "
                                f"耗时: {response_time:.2f}ms, endpoint: {endpoint.id}, "
                                f"模型: {response_model}, "
                                f"tokens: {input_tokens} in / {output_tokens} out"
                            )
                        except:
                            logger.info(
                                f"[{request_id}] ✓ 响应成功: HTTP {response.status}, "
                                f"耗时: {response_time:.2f}ms, endpoint: {endpoint.id}"
                            )
                    else:
                        error_msg = f"HTTP {response.status}"
                        # 尝试解析错误详情
                        try:
                            error_body = response_body.decode('utf-8')
                            # 记录完整的错误信息到日志
                            if len(error_body) < 500:
                                error_msg = f"HTTP {response.status}: {error_body}"
                                logger.error(
                                    f"[{request_id}] ✗ 响应失败: HTTP {response.status}, "
                                    f"耗时: {response_time:.2f}ms, endpoint: {endpoint.id}, "
                                    f"错误: {error_body}"
                                )
                            else:
                                # 错误信息过长，截断记录
                                error_msg = f"HTTP {response.status}: {error_body[:500]}..."
                                logger.error(
                                    f"[{request_id}] ✗ 响应失败: HTTP {response.status}, "
                                    f"耗时: {response_time:.2f}ms, endpoint: {endpoint.id}, "
                                    f"错误: {error_body[:500]}..."
                                )
                        except Exception as e:
                            logger.error(
                                f"[{request_id}] ✗ 响应失败: HTTP {response.status}, "
                                f"耗时: {response_time:.2f}ms, endpoint: {endpoint.id}, "
                                f"无法解析错误信息: {e}"
                            )

                        await endpoint.update_health_status(
                            status='unhealthy',
                            increment_requests=True,
                            is_failure=True,
                            response_time=response_time,
                            error_message=error_msg
                        )
                        # 将失败的 endpoint 加入验证队列
                        if self.failure_queue:
                            await self.failure_queue.add_failed_endpoint(
                                endpoint.id,
                                error_msg
                            )

                    # 构建代理响应
                    # 注意：aiohttp 会自动解压响应体，所以需要移除压缩相关的响应头
                    response_headers = dict(response.headers)
                    # 移除压缩相关的头，避免客户端尝试再次解压
                    response_headers.pop('Content-Encoding', None)
                    response_headers.pop('Content-Length', None)  # 长度已变化

                    proxy_response = web.Response(
                        status=response.status,
                        body=response_body,
                        headers=response_headers
                    )

                    return proxy_response

        except asyncio.TimeoutError:
            error_msg = f"请求超时 (>{endpoint.timeout}s)"
            logger.error(
                f"[{request_id}] ✗ {error_msg}, "
                f"URL: {target_url}, endpoint: {endpoint.id}"
            )
            await endpoint.update_health_status(
                status='unhealthy',
                increment_requests=True,
                is_failure=True,
                error_message=error_msg
            )
            # 将失败请求加入队列
            if self.failure_queue:
                # 将失败的 endpoint 加入验证队列
                await self.failure_queue.add_failed_endpoint(
                    endpoint.id,
                    error_msg
                )
            return None

        except Exception as e:
            error_str = str(e)
            error_lower = error_str.lower()

            # 定义暂时性网络错误（不应标记 endpoint 为失败）
            transient_errors = [
                'closing transport',
                'cannot write',
                'server disconnected',
                'connection reset',
                'broken pipe',
                'connection aborted'
            ]

            # 检查是否是暂时性网络错误
            is_transient = any(err in error_lower for err in transient_errors)

            if is_transient:
                logger.warning(
                    f"[{request_id}] ⚠ 检测到暂时性网络错误: {error_str}, "
                    f"URL: {target_url}, endpoint: {endpoint.id}"
                )
                # 强制重置 session，下次请求会重新创建
                if self.client_session:
                    try:
                        await self.client_session.close()
                    except:
                        pass
                    self.client_session = None

                # 暂时性错误不标记 endpoint 为失败，只增加请求计数
                await endpoint.update_health_status(
                    status=None,  # 不改变健康状态
                    increment_requests=True,
                    is_failure=False,  # 不计入失败
                    error_message=None
                )

                # 返回 None 让上层重试逻辑处理
                return None

            # 其他类型的错误才标记为失败
            error_msg = f"请求失败: {error_str}"
            logger.error(
                f"[{request_id}] ✗ {error_msg}, "
                f"URL: {target_url}, endpoint: {endpoint.id}",
                exc_info=True  # 记录完整堆栈信息
            )
            await endpoint.update_health_status(
                status='unhealthy',
                increment_requests=True,
                is_failure=True,
                error_message=error_msg
            )
            # 将失败请求加入队列
            if self.failure_queue:
                # 将失败的 endpoint 加入验证队列
                await self.failure_queue.add_failed_endpoint(
                    endpoint.id,
                    error_msg
                )
            return None

    async def start(self):
        """启动代理服务器"""
        if self.running:
            logger.warning("代理服务器已经在运行")
            return

        try:
            # 在事件循环内创建关闭事件
            self._shutdown_event = asyncio.Event()
            logger.debug("关闭事件已创建")

            logger.info(f"正在启动代理服务器 {self.host}:{self.port}...")

            # 保存 PID 到文件
            self._write_pid()

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()

            self.running = True
            self.stats['start_time'] = datetime.now().isoformat()

            logger.info(f"[OK] 代理服务器已启动: http://{self.host}:{self.port}")
            print(f"[OK] 代理服务器已启动: http://{self.host}:{self.port}")

            # 注释掉主动健康监控器（改为被动检测）
            # if self.health_monitor:
            #     endpoints = self._get_active_endpoints()
            #     if endpoints:
            #         self._health_monitor_task = asyncio.create_task(
            #             self.health_monitor.start(endpoints)
            #         )
            #         logger.info("[OK] 健康监控器已启动")
            #         print("[OK] 健康监控器已启动")

            # 启动故障转移管理器（后台任务）
            if self.failover_manager:
                policy = self.priority_manager.get_policy() if self.priority_manager else {}
                if policy.get('auto_failover'):
                    self._failover_manager_task = asyncio.create_task(
                        self.failover_manager.start()
                    )
                    logger.info("[OK] 故障转移监控已启动")
                    print("[OK] 故障转移监控已启动")

            # 启动失败队列处理器（后台任务）
            if self.failure_queue:
                # 清空历史失败记录（每次启动时重新开始）
                self.failure_queue.clear()
                # 获取所有 endpoints 用于验证
                all_endpoints = self._get_all_endpoints()
                self._failure_queue_task = asyncio.create_task(
                    self.failure_queue.process_queue(all_endpoints)
                )
                logger.info("[OK] 失败队列处理器已启动")
                print("[OK] 失败队列处理器已启动")

            # 保持运行，等待关闭信号
            try:
                if self._shutdown_event:
                    await self._shutdown_event.wait()
                    logger.info("收到关闭信号，开始停止服务器...")
                else:
                    logger.error("关闭事件未初始化，使用 asyncio.Event 等待")
                    await asyncio.Event().wait()
            except asyncio.CancelledError:
                logger.info("收到取消信号，开始停止服务器...")

        except Exception as e:
            logger.error(f"启动代理服务器失败: {e}", exc_info=True)
            self._remove_pid()
            raise
        finally:
            # 确保执行关闭流程
            if self.running:
                logger.info("finally 块：确保服务器停止...")
                await self.stop()

    async def stop(self):
        """停止代理服务器（带超时机制）"""
        if not self.running:
            logger.debug("stop() 被调用，但服务器已经停止")
            return

        logger.info("正在停止代理服务器...")
        print("\n正在停止代理服务器...")

        self.running = False

        # 立即停止接受新连接
        if self.site:
            logger.info("停止接受新连接...")
            await self.site.stop()

        # 使用超时机制强制停止所有后台任务
        shutdown_timeout = 10  # 10 秒超时

        try:
            await asyncio.wait_for(
                self._stop_background_tasks(),
                timeout=shutdown_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"后台任务停止超时（{shutdown_timeout}秒），强制终止...")
            # 强制取消所有任务
            await self._force_cancel_tasks()

        # 关闭客户端会话
        if self.client_session:
            try:
                if not self.client_session.closed:
                    await self.client_session.close()
                    logger.info("[OK] ClientSession 已关闭")
                # 等待连接完全关闭
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"关闭 client session 时出错: {e}")
            finally:
                self.client_session = None

        # 清理 runner（site 已经在开始时停止了）
        if self.runner:
            logger.info("清理 AppRunner...")
            try:
                await asyncio.wait_for(self.runner.cleanup(), timeout=5)
                logger.info("[OK] AppRunner 已清理")
            except asyncio.TimeoutError:
                logger.warning("AppRunner 清理超时")
            except Exception as e:
                logger.warning(f"清理 AppRunner 时出错: {e}")
            finally:
                self.runner = None
                self.site = None

        # 删除 PID 文件
        self._remove_pid()

        # 尝试还原 Claude Code 配置
        self._restore_claude_config()

        logger.info("[OK] 代理服务器已停止")
        print("[OK] 代理服务器已停止")

    async def _stop_background_tasks(self):
        """停止所有后台任务（内部方法）"""
        # 停止失败队列处理器
        if self.failure_queue and self._failure_queue_task:
            try:
                await self.failure_queue.stop()
                if not self._failure_queue_task.done():
                    self._failure_queue_task.cancel()
                    try:
                        await asyncio.wait_for(self._failure_queue_task, timeout=2)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                self._failure_queue_task = None
                logger.info("[OK] 失败队列处理器已停止")
            except Exception as e:
                logger.warning(f"停止失败队列处理器时出错: {e}")

        # 停止故障转移管理器
        if self.failover_manager and self._failover_manager_task:
            try:
                await self.failover_manager.stop()
                if not self._failover_manager_task.done():
                    self._failover_manager_task.cancel()
                    try:
                        await asyncio.wait_for(self._failover_manager_task, timeout=2)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                self._failover_manager_task = None
                logger.info("[OK] 故障转移管理器已停止")
            except Exception as e:
                logger.warning(f"停止故障转移管理器时出错: {e}")

        # 停止健康监控器
        if self.health_monitor and self._health_monitor_task:
            try:
                await self.health_monitor.stop()
                if not self._health_monitor_task.done():
                    self._health_monitor_task.cancel()
                    try:
                        await asyncio.wait_for(self._health_monitor_task, timeout=2)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                self._health_monitor_task = None
                logger.info("[OK] 健康监控器已停止")
            except Exception as e:
                logger.warning(f"停止健康监控器时出错: {e}")

    async def _force_cancel_tasks(self):
        """强制取消所有后台任务（超时时使用）"""
        tasks_to_cancel = []

        if self._failure_queue_task and not self._failure_queue_task.done():
            tasks_to_cancel.append(self._failure_queue_task)
            self._failure_queue_task = None

        if self._failover_manager_task and not self._failover_manager_task.done():
            tasks_to_cancel.append(self._failover_manager_task)
            self._failover_manager_task = None

        if self._health_monitor_task and not self._health_monitor_task.done():
            tasks_to_cancel.append(self._health_monitor_task)
            self._health_monitor_task = None

        if tasks_to_cancel:
            logger.warning(f"强制取消 {len(tasks_to_cancel)} 个后台任务")
            for task in tasks_to_cancel:
                task.cancel()

            # 等待所有任务取消完成（但不超过 1 秒）
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=1
                )
            except asyncio.TimeoutError:
                logger.error("部分后台任务无法在 1 秒内取消")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()

        if stats['start_time']:
            start = datetime.fromisoformat(stats['start_time'])
            stats['uptime'] = (datetime.now() - start).total_seconds()

        return stats

    async def handle_logs(self, request: web.Request) -> web.Response:
        """处理日志查看请求

        查询参数:
            - lines: 返回最后 N 行（默认 100）
            - level: 过滤日志级别（DEBUG, INFO, WARNING, ERROR, ALL）
            - grep: 搜索关键词
        """
        try:
            # 获取查询参数
            lines = int(request.query.get('lines', 100))
            level = request.query.get('level', 'ALL').upper()
            grep = request.query.get('grep', '')

            # 读取日志文件
            if not self.log_file.exists():
                return web.json_response({
                    'error': 'Log file not found',
                    'log_file': str(self.log_file)
                }, status=404)

            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            # 过滤日志
            filtered_lines = []
            for line in all_lines:
                if not line.strip():
                    continue

                # 级别过滤
                if level != 'ALL':
                    if f" - {level} - " not in line:
                        continue

                # 关键词过滤
                if grep and grep.lower() not in line.lower():
                    continue

                filtered_lines.append(line.rstrip())

            # 返回最后 N 行
            display_lines = filtered_lines[-lines:] if len(filtered_lines) > lines else filtered_lines

            return web.json_response({
                'logs': display_lines,
                'total_lines': len(filtered_lines),
                'displayed_lines': len(display_lines),
                'log_file': str(self.log_file),
                'filters': {
                    'lines': lines,
                    'level': level,
                    'grep': grep
                }
            })

        except Exception as e:
            logger.error(f"处理日志查看请求失败: {e}", exc_info=True)
            return web.json_response({
                'error': str(e)
            }, status=500)

    async def handle_count_tokens(self, request: web.Request) -> web.Response:
        """处理 token 计数请求（本地实现，不转发到后端）

        这个接口在代理层面本地实现，因为：
        1. 大多数第三方 API 服务不支持 count_tokens 接口
        2. 避免将 404 错误误判为 endpoint 故障
        3. 提供更好的用户体验
        """
        try:
            data = await request.json()

            # 提取消息内容
            messages = data.get('messages', [])
            system = data.get('system', '')

            # 简单的 token 估算算法
            # 根据 OpenAI 的经验规则：英文约 1 token = 4 字符，中文约 1 token = 1.5-2 字符
            # 这里使用保守估算：1 token ≈ 3 字符
            total_chars = 0

            # 计算系统提示的字符数
            if system:
                if isinstance(system, str):
                    total_chars += len(system)
                elif isinstance(system, list):
                    for item in system:
                        if isinstance(item, dict) and 'text' in item:
                            total_chars += len(item['text'])

            # 计算消息的字符数
            for msg in messages:
                content = msg.get('content', '')
                if isinstance(content, str):
                    total_chars += len(content)
                elif isinstance(content, list):
                    # 处理多模态内容（文本、图片等）
                    for block in content:
                        if isinstance(block, dict):
                            if block.get('type') == 'text':
                                total_chars += len(block.get('text', ''))
                            elif block.get('type') == 'image':
                                # 图片大约占用 85-170 tokens（根据分辨率）
                                total_chars += 500  # 保守估算

            # 估算 token 数量（保守估算，向上取整）
            # 使用系数 0.35 (1 token ≈ 2.85 字符)
            estimated_tokens = int(total_chars * 0.35) + 10  # 加 10 作为基础开销

            logger.info(f"Token 计数请求: {total_chars} 字符 ≈ {estimated_tokens} tokens")

            return web.json_response({
                'input_tokens': estimated_tokens
            })

        except Exception as e:
            logger.error(f"处理 token 计数请求失败: {e}", exc_info=True)
            # 返回一个默认值，避免客户端报错
            return web.json_response({
                'input_tokens': 100  # 默认估算值
            })

    async def handle_stats_api(self, request: web.Request) -> web.Response:
        """处理统计信息 API 请求"""
        try:
            stats = self.get_stats()

            # 添加 endpoint 信息
            if self.config_manager:
                endpoints_info = []
                all_endpoints = self._get_all_endpoints()

                for ep in all_endpoints:
                    endpoints_info.append({
                        'id': ep.id,
                        'base_url': ep.base_url,
                        'priority': ep.priority,
                        'enabled': ep.enabled,
                        'health_status': ep.health_status,
                        'is_healthy': ep.is_healthy()
                    })

                stats['endpoints'] = endpoints_info
                stats['total_endpoints'] = len(all_endpoints)
                stats['healthy_endpoints'] = len([ep for ep in all_endpoints if ep.is_healthy()])

            # 添加失败队列信息（从内存中获取）
            if self.failure_queue:
                stats['failed_endpoints'] = list(self.failure_queue.failed_endpoints)
                stats['failure_queue_size'] = len(self.failure_queue.failed_endpoints)
                stats['endpoint_verify_counts'] = dict(self.failure_queue.verify_counts)
            else:
                stats['failed_endpoints'] = []
                stats['failure_queue_size'] = 0
                stats['endpoint_verify_counts'] = {}

            return web.json_response(stats)

        except Exception as e:
            logger.error(f"处理统计信息请求失败: {e}", exc_info=True)
            return web.json_response({
                'error': str(e)
            }, status=500)

    def _write_pid(self):
        """写入 PID 文件"""
        try:
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.pid_file, 'w') as f:
                data = {
                    'pid': os.getpid(),
                    'host': self.host,
                    'port': self.port,
                    'start_time': datetime.now().isoformat()
                }
                # 添加 cluster_name（如果有）
                if self.cluster_name:
                    data['cluster_name'] = self.cluster_name
                json.dump(data, f)
            logger.debug(f"PID 文件已写入: {self.pid_file}")
        except Exception as e:
            logger.error(f"写入 PID 文件失败: {e}")

    def _remove_pid(self):
        """删除 PID 文件"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.debug(f"PID 文件已删除: {self.pid_file}")
        except Exception as e:
            logger.error(f"删除 PID 文件失败: {e}")

    def _restore_claude_config(self):
        """还原 Claude Code 配置（如果之前有应用过代理）"""
        try:
            import shutil
            claude_dir = Path.home() / ".claude"
            backup_file = claude_dir / "settings.json.qcc_backup"
            settings_file = claude_dir / "settings.json"
            proxy_info_file = claude_dir / "qcc_proxy_info.json"

            # 检查是否有备份
            if backup_file.exists() and proxy_info_file.exists():
                # 还原配置
                shutil.copy2(backup_file, settings_file)
                # 删除备份和代理信息
                backup_file.unlink(missing_ok=True)
                proxy_info_file.unlink(missing_ok=True)
                logger.info("[OK] 已自动还原 Claude Code 配置")
                print("[OK] 已自动还原 Claude Code 配置")
        except Exception as e:
            logger.warning(f"还原 Claude Code 配置失败: {e}")
            # 不抛出异常，因为这不是关键操作

    @staticmethod
    def get_running_server():
        """获取正在运行的服务器信息

        Returns:
            服务器信息字典，如果没有运行则返回 None
        """
        pid_file = Path.home() / '.fastcc' / 'proxy.pid'

        if not pid_file.exists():
            return None

        try:
            with open(pid_file, 'r') as f:
                data = json.load(f)

            pid = data.get('pid')
            if not pid:
                return None

            # 检查进程是否存在
            try:
                os.kill(pid, 0)  # 发送信号 0 只检查进程是否存在
                return data
            except OSError:
                # 进程不存在，清理 PID 文件
                pid_file.unlink()
                return None

        except Exception as e:
            logger.error(f"读取 PID 文件失败: {e}")
            return None

    @staticmethod
    def stop_running_server():
        """停止正在运行的服务器

        Returns:
            是否成功停止
        """
        server_info = ProxyServer.get_running_server()

        if not server_info:
            return False

        pid = server_info['pid']

        try:
            # 发送 SIGTERM 信号
            os.kill(pid, signal.SIGTERM)
            logger.info(f"已向进程 {pid} 发送停止信号")
            return True
        except OSError as e:
            logger.error(f"停止进程失败: {e}")
            return False

    async def __aenter__(self):
        """上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        await self.stop()

    def _maybe_override_model(self, body: bytes) -> bytes:
        """根据配置决定是否替换请求中的模型

        Args:
            body: 原始请求体

        Returns:
            处理后的请求体
        """
        try:
            # 获取模型配置
            proxy_model_mode = self.config_manager.settings.get('proxy_model_mode', 'passthrough')

            # 如果是 passthrough 模式，不做任何修改
            if proxy_model_mode == 'passthrough':
                return body

            # override 模式：替换模型
            if proxy_model_mode == 'override':
                proxy_model_override = self.config_manager.settings.get(
                    'proxy_model_override',
                    'claude-3-5-sonnet-20241022'
                )

                # 解析 JSON
                data = json.loads(body.decode('utf-8'))

                # 记录原始模型
                original_model = data.get('model', 'unknown')

                # 替换模型
                data['model'] = proxy_model_override

                logger.info(
                    f"模型替换: {original_model} -> {proxy_model_override}"
                )

                # 重新编码
                return json.dumps(data, ensure_ascii=False).encode('utf-8')

        except Exception as e:
            logger.warning(f"模型替换失败: {e}，使用原始请求")
            return body

        return body
