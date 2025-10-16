"""QCC Failure Queue - 失败队列管理器"""

import asyncio
import logging
from collections import deque
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 指数退避
    FIXED_INTERVAL = "fixed_interval"  # 固定间隔
    IMMEDIATE = "immediate"  # 立即重试


class FailureQueue:
    """失败队列管理器

    管理失败的请求并根据策略进行重试
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_retries: int = 5,
        strategy: str = "exponential_backoff"
    ):
        """初始化失败队列

        Args:
            max_size: 队列最大长度
            max_retries: 最大重试次数
            strategy: 重试策略
        """
        self.max_size = max_size
        self.max_retries = max_retries
        self.strategy = RetryStrategy(strategy)
        self.queue = deque(maxlen=max_size)
        self.running = False

        # 统计信息
        self.stats = {
            'total_enqueued': 0,
            'total_retried': 0,
            'total_success': 0,
            'total_failed': 0,
            'queue_size': 0
        }

    async def enqueue(self, request_data: Dict[str, Any], reason: str = ""):
        """将失败的请求加入队列

        Args:
            request_data: 请求数据
            reason: 失败原因
        """
        if len(self.queue) >= self.max_size:
            logger.warning("失败队列已满，丢弃最旧的请求")
            self.queue.popleft()

        retry_item = {
            'request_id': f"retry-{self.stats['total_enqueued']}",
            'request_data': request_data,
            'reason': reason,
            'enqueued_at': datetime.now(),
            'retry_count': 0,
            'next_retry_at': self._calculate_next_retry(0),
            'status': 'pending'
        }

        self.queue.append(retry_item)
        self.stats['total_enqueued'] += 1
        self.stats['queue_size'] = len(self.queue)

        logger.info(
            f"请求加入失败队列: {retry_item['request_id']}, "
            f"原因: {reason}"
        )

    def _calculate_next_retry(self, retry_count: int) -> datetime:
        """计算下次重试时间

        Args:
            retry_count: 当前重试次数

        Returns:
            下次重试时间
        """
        if self.strategy == RetryStrategy.IMMEDIATE:
            return datetime.now()
        elif self.strategy == RetryStrategy.FIXED_INTERVAL:
            return datetime.now() + timedelta(seconds=30)
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            # 指数退避: 5s, 10s, 20s, 40s, 80s (最大 300s)
            delay = min(5 * (2 ** retry_count), 300)
            return datetime.now() + timedelta(seconds=delay)

        return datetime.now() + timedelta(seconds=60)

    async def process_queue(self):
        """处理队列中的请求（后台任务）"""
        self.running = True
        logger.info("✓ 失败队列处理器已启动")

        try:
            while self.running:
                if self.queue:
                    await self._process_pending_requests()
                await asyncio.sleep(5)  # 每5秒检查一次
        except asyncio.CancelledError:
            logger.info("失败队列处理器收到停止信号")
        finally:
            logger.info("✓ 失败队列处理器已停止")

    async def _process_pending_requests(self):
        """处理待重试的请求"""
        now = datetime.now()
        processed_items = []

        # 找出需要重试的请求
        for item in list(self.queue):
            if item['status'] == 'pending' and item['next_retry_at'] <= now:
                processed_items.append(item)

        # 处理需要重试的请求
        for item in processed_items:
            await self._retry_request(item)

        self.stats['queue_size'] = len(self.queue)

    async def _retry_request(self, item: Dict[str, Any]):
        """重试单个请求

        Args:
            item: 重试项
        """
        item['retry_count'] += 1
        self.stats['total_retried'] += 1

        logger.info(
            f"重试请求 {item['request_id']} "
            f"(第 {item['retry_count']}/{self.max_retries} 次)"
        )

        # TODO: 实际的重试逻辑（需要与 ProxyServer 集成）
        # 这里暂时模拟重试结果
        success = False  # 模拟失败

        if success:
            item['status'] = 'success'
            self.stats['total_success'] += 1
            self.queue.remove(item)
            logger.info(f"请求 {item['request_id']} 重试成功")
        else:
            if item['retry_count'] >= self.max_retries:
                item['status'] = 'failed'
                self.stats['total_failed'] += 1
                self.queue.remove(item)
                logger.error(
                    f"请求 {item['request_id']} 达到最大重试次数，放弃重试"
                )
            else:
                item['next_retry_at'] = self._calculate_next_retry(
                    item['retry_count']
                )
                logger.warning(
                    f"请求 {item['request_id']} 重试失败，"
                    f"下次重试时间: {item['next_retry_at']}"
                )

    async def stop(self):
        """停止处理队列"""
        self.running = False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()

    def clear(self):
        """清空队列"""
        self.queue.clear()
        self.stats['queue_size'] = 0
        logger.info("失败队列已清空")
