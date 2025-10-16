"""QCC Proxy Server - 代理服务器主逻辑"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from aiohttp import web, ClientSession, ClientTimeout
from datetime import datetime
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
        load_balancer=None
    ):
        """初始化代理服务器

        Args:
            host: 监听地址 (默认 127.0.0.1)
            port: 监听端口 (默认 7860)
            config_manager: 配置管理器实例
            load_balancer: 负载均衡器实例
        """
        self.host = host
        self.port = port
        self.config_manager = config_manager
        self.load_balancer = load_balancer

        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.client_session: Optional[ClientSession] = None
        self.running = False

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': None,
            'uptime': 0
        }

        self._setup_routes()
        self._setup_signal_handlers()

    def _setup_routes(self):
        """设置路由"""
        # 捕获所有路径的所有 HTTP 方法
        self.app.router.add_route('*', '/{path:.*}', self.handle_request)

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备关闭服务器...")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def handle_request(self, request: web.Request) -> web.Response:
        """处理代理请求

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

            # 2. 选择 endpoint（通过负载均衡器）
            endpoint = await self._select_endpoint()
            if not endpoint:
                logger.error(f"[{request_id}] 没有可用的 endpoint")
                self.stats['failed_requests'] += 1
                return web.Response(
                    status=503,
                    text=json.dumps({'error': 'No available endpoints'}),
                    content_type='application/json'
                )

            logger.info(f"[{request_id}] 选中 endpoint: {endpoint.id} ({endpoint.base_url})")

            # 3. 转发请求
            response = await self._forward_request(
                endpoint=endpoint,
                method=request.method,
                path=request.path,
                headers=dict(request.headers),
                body=body,
                request_id=request_id
            )

            if response:
                self.stats['successful_requests'] += 1
                logger.info(f"[{request_id}] 请求成功: {response.status}")
            else:
                self.stats['failed_requests'] += 1
                logger.error(f"[{request_id}] 请求失败")

            return response if response else web.Response(
                status=502,
                text=json.dumps({'error': 'Bad Gateway'}),
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

    async def _select_endpoint(self):
        """选择 endpoint（通过负载均衡器）"""
        if self.load_balancer and self.config_manager:
            # 获取当前活跃配置的所有 endpoint
            endpoints = self._get_active_endpoints()
            if endpoints:
                return await self.load_balancer.select_endpoint(endpoints)

        # 如果没有负载均衡器，使用简单的单配置模式
        if self.config_manager:
            default_profile = self.config_manager.get_default_profile()
            if default_profile:
                # 如果配置有 endpoints，使用第一个
                if hasattr(default_profile, 'endpoints') and default_profile.endpoints:
                    return default_profile.endpoints[0]
                # 否则从传统字段创建临时 endpoint
                from fastcc.core.endpoint import Endpoint
                return Endpoint(
                    base_url=default_profile.base_url,
                    api_key=default_profile.api_key
                )

        return None

    def _get_active_endpoints(self):
        """获取当前活跃配置的所有健康 endpoint"""
        endpoints = []
        if not self.config_manager:
            return endpoints

        # 获取默认配置或主配置
        profile = self.config_manager.get_default_profile()
        if not profile:
            return endpoints

        # 获取配置的 endpoints
        if hasattr(profile, 'endpoints') and profile.endpoints:
            # 只返回启用且健康的 endpoint
            endpoints = [
                ep for ep in profile.endpoints
                if ep.enabled and ep.is_healthy()
            ]

        return endpoints

    async def _forward_request(
        self,
        endpoint,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: bytes,
        request_id: str
    ) -> Optional[web.Response]:
        """转发请求到目标 endpoint

        Args:
            endpoint: 目标 endpoint
            method: HTTP 方法
            path: 请求路径
            headers: 请求头
            body: 请求体
            request_id: 请求 ID

        Returns:
            代理响应，失败返回 None
        """
        if not self.client_session:
            self.client_session = ClientSession(
                timeout=ClientTimeout(total=endpoint.timeout)
            )

        try:
            # 构建目标 URL
            target_url = f"{endpoint.base_url}{path}"

            # 修改请求头
            forward_headers = headers.copy()
            # 使用 endpoint 的 API Key
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
                timeout=ClientTimeout(total=endpoint.timeout)
            ) as response:
                # 读取响应
                response_body = await response.read()

                # 计算响应时间
                response_time = (datetime.now() - start_time).total_seconds() * 1000

                # 更新 endpoint 健康状态
                endpoint.update_health_status(
                    status='healthy',
                    increment_requests=True,
                    is_failure=False,
                    response_time=response_time
                )

                logger.debug(
                    f"[{request_id}] 响应: {response.status}, "
                    f"耗时: {response_time:.2f}ms"
                )

                # 构建代理响应
                proxy_response = web.Response(
                    status=response.status,
                    body=response_body,
                    headers=dict(response.headers)
                )

                return proxy_response

        except asyncio.TimeoutError:
            logger.error(f"[{request_id}] 请求超时")
            endpoint.update_health_status(
                status='unhealthy',
                increment_requests=True,
                is_failure=True
            )
            return None

        except Exception as e:
            logger.error(f"[{request_id}] 转发请求失败: {e}")
            endpoint.update_health_status(
                status='unhealthy',
                increment_requests=True,
                is_failure=True
            )
            return None

    async def start(self):
        """启动代理服务器"""
        if self.running:
            logger.warning("代理服务器已经在运行")
            return

        try:
            logger.info(f"正在启动代理服务器 {self.host}:{self.port}...")

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()

            self.running = True
            self.stats['start_time'] = datetime.now().isoformat()

            logger.info(f"✓ 代理服务器已启动: http://{self.host}:{self.port}")
            print(f"✓ 代理服务器已启动: http://{self.host}:{self.port}")

            # 保持运行
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                logger.info("收到停止信号")

        except Exception as e:
            logger.error(f"启动代理服务器失败: {e}", exc_info=True)
            raise

    async def stop(self):
        """停止代理服务器"""
        if not self.running:
            return

        logger.info("正在停止代理服务器...")
        print("\n正在停止代理服务器...")

        self.running = False

        # 关闭客户端会话
        if self.client_session:
            await self.client_session.close()
            self.client_session = None

        # 停止服务器
        if self.site:
            await self.site.stop()
            self.site = None

        if self.runner:
            await self.runner.cleanup()
            self.runner = None

        logger.info("✓ 代理服务器已停止")
        print("✓ 代理服务器已停止")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()

        if stats['start_time']:
            start = datetime.fromisoformat(stats['start_time'])
            stats['uptime'] = (datetime.now() - start).total_seconds()

        return stats

    async def __aenter__(self):
        """上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        await self.stop()
