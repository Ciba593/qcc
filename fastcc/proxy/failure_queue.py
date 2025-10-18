"""QCC Failure Queue - 失败 Endpoint 验证队列

专门用于验证失败的 endpoint 是否已恢复，而不是重试失败的请求。
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FailureQueue:
    """失败 Endpoint 验证队列

    管理失败的 endpoint，定期验证是否已恢复健康。
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        config_manager=None,
        conversational_checker=None
    ):
        """初始化失败队列

        Args:
            storage_path: 队列持久化存储路径
            config_manager: 配置管理器（用于获取 endpoint）
            conversational_checker: 对话检查器（用于验证 endpoint）
        """
        self.storage_path = storage_path or Path.home() / '.qcc' / 'failure_endpoints.json'
        self.config_manager = config_manager
        self.conversational_checker = conversational_checker
        self.running = False

        # 失败的 endpoint ID 集合
        self.failed_endpoints: Set[str] = set()

        # 上次验证时间记录
        self.last_check_times: Dict[str, datetime] = {}

        # 每个 endpoint 的验证次数记录
        self.verify_counts: Dict[str, int] = {}

        # 统计信息
        self.stats = {
            'total_failed': 0,
            'total_verified': 0,
            'total_recovered': 0,
            'total_still_failed': 0
        }

        # 并发控制锁
        self._lock = asyncio.Lock()

        # 加载持久化数据
        self._load()

    async def add_failed_endpoint(self, endpoint_id: str, reason: str = ""):
        """将失败的 endpoint 加入队列（线程安全）

        Args:
            endpoint_id: Endpoint ID
            reason: 失败原因
        """
        async with self._lock:
            if endpoint_id not in self.failed_endpoints:
                self.failed_endpoints.add(endpoint_id)
                self.last_check_times[endpoint_id] = datetime.now()
                self.verify_counts[endpoint_id] = 0  # 初始化验证次数为 0
                self.stats['total_failed'] += 1

                logger.info(
                    f"Endpoint {endpoint_id} 加入失败队列, 原因: {reason}"
                )

                # 持久化
                self._save()
            else:
                # 已经在队列中，只更新时间和原因（不重复统计）
                logger.debug(
                    f"Endpoint {endpoint_id} 已在失败队列中（原因: {reason}），跳过重复添加"
                )

    async def remove_endpoint(self, endpoint_id: str):
        """从队列中移除 endpoint（线程安全）

        Args:
            endpoint_id: Endpoint ID
        """
        async with self._lock:
            if endpoint_id in self.failed_endpoints:
                self.failed_endpoints.remove(endpoint_id)
                self.last_check_times.pop(endpoint_id, None)
                self.verify_counts.pop(endpoint_id, None)  # 移除验证次数记录
                logger.info(f"Endpoint {endpoint_id} 已从失败队列移除")
                self._save()

    async def process_queue(self, all_endpoints: List = None):
        """处理队列中的 endpoint（后台任务）

        Args:
            all_endpoints: 所有 endpoint 列表
        """
        self.running = True
        logger.info("[OK] 失败队列处理器已启动")
        logger.info("  - 检查间隔: 60秒")
        logger.info("  - 功能: 验证失败的 endpoint 是否已恢复")

        try:
            while self.running:
                if self.failed_endpoints and all_endpoints:
                    await self._verify_failed_endpoints(all_endpoints)
                await asyncio.sleep(60)  # 每60秒检查一次（1分钟）
        except asyncio.CancelledError:
            logger.info("失败队列处理器收到停止信号")
        finally:
            logger.info("[OK] 失败队列处理器已停止")

    async def _verify_failed_endpoints(self, all_endpoints: List):
        """验证失败的 endpoint

        Args:
            all_endpoints: 所有 endpoint 列表
        """
        if not self.conversational_checker:
            logger.warning("没有配置对话检查器，无法验证 endpoint")
            return

        logger.info(f"\n🔍 开始验证失败的 endpoint ({len(self.failed_endpoints)} 个)")

        endpoints_to_verify = []
        for endpoint in all_endpoints:
            if endpoint.id in self.failed_endpoints:
                endpoints_to_verify.append(endpoint)

        if not endpoints_to_verify:
            logger.debug("没有需要验证的 endpoint")
            return

        # 逐个验证
        for endpoint in endpoints_to_verify:
            self.stats['total_verified'] += 1

            # 增加该 endpoint 的验证次数
            self.verify_counts[endpoint.id] = self.verify_counts.get(endpoint.id, 0) + 1

            logger.info(
                f"验证 endpoint {endpoint.id} ({endpoint.base_url}) "
                f"[第 {self.verify_counts[endpoint.id]} 次验证]"
            )

            # 使用对话检查器验证
            check = await self.conversational_checker.check_endpoint(endpoint)

            # 更新上次检查时间
            self.last_check_times[endpoint.id] = datetime.now()

            # 导入 HealthCheckResult
            from .health_check_models import HealthCheckResult

            # 判断是否真正恢复：需要同时满足 result=SUCCESS 和 response_valid=True
            if check.result == HealthCheckResult.SUCCESS and check.response_valid:
                # 恢复健康 - 注意：必须设置 increment_requests=True 才能重置 consecutive_failures
                await endpoint.update_health_status(
                    status='healthy',
                    increment_requests=True,
                    is_failure=False,
                    response_time=check.response_time_ms
                )
                await self.remove_endpoint(endpoint.id)
                self.stats['total_recovered'] += 1
                logger.info(
                    f"✅ Endpoint {endpoint.id} 已恢复健康 "
                    f"({check.response_time_ms:.0f}ms, 评分: {check.response_score:.0f})"
                )
            else:
                # 仍然失败
                self.stats['total_still_failed'] += 1
                reason = check.error_message or "响应无效（未包含验证码）"
                logger.warning(
                    f"❌ Endpoint {endpoint.id} 仍然不健康: {reason}"
                )

        # 持久化
        self._save()

    async def stop(self):
        """停止处理队列"""
        self.running = False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'failed_endpoints_count': len(self.failed_endpoints),
            'failed_endpoints': list(self.failed_endpoints)
        }

    def clear(self):
        """清空队列"""
        self.failed_endpoints.clear()
        self.last_check_times.clear()
        self.verify_counts.clear()
        self._save()
        logger.info("失败队列已清空")

    def _save(self):
        """
        注意：失败队列现在只保存在内存中，不持久化到文件。
        这样可以确保每次重启时都是全新的状态，避免过时数据的干扰。
        此方法保留为空，以兼容现有代码调用。
        """
        # 不再持久化到文件
        pass

    def _load(self):
        """
        注意：失败队列现在只保存在内存中，不从文件加载。
        此方法保留为空，以兼容现有代码调用。
        """
        # 不再从文件加载
        pass
