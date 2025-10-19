"""
断路器模式实现

参考 ccflare 的最佳实践，避免重复请求故障节点，自动恢复机制。
"""

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """断路器模式（Circuit Breaker Pattern）

    功能：
    - 记录 endpoint 失败次数
    - 达到阈值后打开断路器（停止使用该 endpoint）
    - 超时后自动进入半开状态，尝试恢复
    - 恢复成功后关闭断路器

    参数:
        failure_threshold: 连续失败多少次后打开断路器（默认 3）
        timeout: 断路器打开后多久尝试恢复（默认 60 秒）
    """

    def __init__(self, failure_threshold: int = 3, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout

        # 失败计数器
        self.failure_counts: Dict[str, int] = {}

        # 断路器打开时间记录
        self.circuit_opened_at: Dict[str, float] = {}

        logger.info(
            f"断路器初始化: failure_threshold={failure_threshold}, "
            f"timeout={timeout}s"
        )

    def is_open(self, endpoint_id: str) -> bool:
        """检查断路器是否打开

        Args:
            endpoint_id: Endpoint ID

        Returns:
            True 如果断路器打开（不应使用此 endpoint）
            False 如果断路器关闭或半开（可以尝试使用）
        """
        if endpoint_id not in self.circuit_opened_at:
            return False

        open_time = self.circuit_opened_at[endpoint_id]
        elapsed = time.time() - open_time

        # 超时后进入半开状态，允许一次尝试
        if elapsed > self.timeout:
            logger.info(
                f"断路器进入半开状态: {endpoint_id} "
                f"(已打开 {elapsed:.1f}s)"
            )
            # 删除打开记录，重置计数器
            del self.circuit_opened_at[endpoint_id]
            self.failure_counts[endpoint_id] = 0
            return False

        return True

    def record_failure(self, endpoint_id: str):
        """记录失败

        Args:
            endpoint_id: Endpoint ID
        """
        # 增加失败计数
        self.failure_counts[endpoint_id] = \
            self.failure_counts.get(endpoint_id, 0) + 1

        failure_count = self.failure_counts[endpoint_id]

        logger.debug(
            f"记录失败: {endpoint_id} "
            f"({failure_count}/{self.failure_threshold})"
        )

        # 达到阈值，打开断路器
        if failure_count >= self.failure_threshold:
            self.circuit_opened_at[endpoint_id] = time.time()
            logger.warning(
                f"⚠️ 断路器打开: {endpoint_id} "
                f"(连续失败 {failure_count} 次，将在 {self.timeout}s 后尝试恢复)"
            )

    def record_success(self, endpoint_id: str):
        """记录成功（重置计数器）

        Args:
            endpoint_id: Endpoint ID
        """
        # 重置失败计数
        if endpoint_id in self.failure_counts:
            old_count = self.failure_counts[endpoint_id]
            self.failure_counts[endpoint_id] = 0

            if old_count > 0:
                logger.debug(
                    f"重置失败计数: {endpoint_id} "
                    f"(之前 {old_count} 次失败)"
                )

        # 关闭断路器（如果之前打开了）
        if endpoint_id in self.circuit_opened_at:
            del self.circuit_opened_at[endpoint_id]
            logger.info(f"✅ 断路器关闭: {endpoint_id} (恢复成功)")

    def get_status(self, endpoint_id: str) -> dict:
        """获取断路器状态

        Args:
            endpoint_id: Endpoint ID

        Returns:
            状态信息字典
        """
        is_open = self.is_open(endpoint_id)
        failure_count = self.failure_counts.get(endpoint_id, 0)

        status = {
            'endpoint_id': endpoint_id,
            'is_open': is_open,
            'failure_count': failure_count,
            'failure_threshold': self.failure_threshold,
        }

        if endpoint_id in self.circuit_opened_at:
            open_time = self.circuit_opened_at[endpoint_id]
            elapsed = time.time() - open_time
            status['opened_at'] = open_time
            status['elapsed_seconds'] = elapsed
            status['remaining_seconds'] = max(0, self.timeout - elapsed)

        return status

    def get_all_status(self) -> dict:
        """获取所有断路器状态

        Returns:
            所有 endpoint 的状态信息
        """
        all_endpoints = set(self.failure_counts.keys()) | \
                       set(self.circuit_opened_at.keys())

        return {
            endpoint_id: self.get_status(endpoint_id)
            for endpoint_id in all_endpoints
        }

    def reset(self, endpoint_id: Optional[str] = None):
        """重置断路器状态

        Args:
            endpoint_id: 指定要重置的 endpoint ID，None 表示重置所有
        """
        if endpoint_id:
            # 重置指定 endpoint
            self.failure_counts.pop(endpoint_id, None)
            self.circuit_opened_at.pop(endpoint_id, None)
            logger.info(f"重置断路器: {endpoint_id}")
        else:
            # 重置所有
            self.failure_counts.clear()
            self.circuit_opened_at.clear()
            logger.info("重置所有断路器")
