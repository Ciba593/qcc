"""QCC Health Monitor - 健康监控器"""

import asyncio
import logging
from typing import List
from aiohttp import ClientSession, ClientTimeout
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthMonitor:
    """健康监控器

    定时检查所有 endpoint 的健康状态
    """

    def __init__(self, check_interval: int = 60, timeout: int = 10):
        """初始化健康监控器

        Args:
            check_interval: 检查间隔（秒）
            timeout: 超时时间（秒）
        """
        self.check_interval = check_interval
        self.timeout = timeout
        self.running = False
        self.session: ClientSession = None

    async def start(self, endpoints: List = None):
        """启动健康监控

        Args:
            endpoints: 需要监控的 endpoint 列表
        """
        if self.running:
            logger.warning("健康监控器已经在运行")
            return

        self.running = True
        self.session = ClientSession(timeout=ClientTimeout(total=self.timeout))

        logger.info(f"✓ 健康监控器已启动 (检查间隔: {self.check_interval}秒)")

        try:
            while self.running:
                if endpoints:
                    await self.check_all_endpoints(endpoints)
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("健康监控器收到停止信号")
        finally:
            if self.session:
                await self.session.close()

    async def stop(self):
        """停止健康监控"""
        self.running = False
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("✓ 健康监控器已停止")

    async def check_all_endpoints(self, endpoints: List):
        """检查所有 endpoint"""
        tasks = [self.check_endpoint(ep) for ep in endpoints]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def check_endpoint(self, endpoint):
        """检查单个 endpoint

        Args:
            endpoint: 要检查的 endpoint
        """
        if not self.session:
            return

        try:
            start_time = datetime.now()

            # 发送简单的健康检查请求
            async with self.session.get(
                f"{endpoint.base_url}/health",
                headers={'Authorization': f'Bearer {endpoint.api_key}'},
                timeout=ClientTimeout(total=self.timeout)
            ) as response:
                response_time = (datetime.now() - start_time).total_seconds() * 1000

                # 更新健康状态
                if response.status < 500:
                    endpoint.update_health_status(
                        status='healthy',
                        response_time=response_time
                    )
                    logger.debug(
                        f"Endpoint {endpoint.id} 健康检查通过 "
                        f"({response_time:.2f}ms)"
                    )
                else:
                    endpoint.update_health_status(status='degraded')
                    logger.warning(f"Endpoint {endpoint.id} 健康检查降级")

        except asyncio.TimeoutError:
            endpoint.update_health_status(status='unhealthy')
            logger.error(f"Endpoint {endpoint.id} 健康检查超时")

        except Exception as e:
            endpoint.update_health_status(status='unhealthy')
            logger.error(f"Endpoint {endpoint.id} 健康检查失败: {e}")
