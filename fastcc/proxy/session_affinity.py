"""
会话亲和性管理器

参考 ccflare 的会话绑定机制，确保同一对话始终使用同一节点（5 小时内）。
"""

import time
import asyncio
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SessionAffinityManager:
    """会话亲和性管理器（Session Affinity Manager）

    功能：
    - 将对话 ID 绑定到特定 endpoint
    - 同一对话的请求始终转发到同一节点
    - 自动过期清理（默认 5 小时）
    - 提升用户体验和节点切换丝滑度

    参数:
        ttl: 会话过期时间（秒），默认 18000 秒（5 小时）
    """

    def __init__(self, ttl: int = 18000):
        self.ttl = ttl
        # 会话绑定: {conversation_id: (endpoint_id, expire_time)}
        self.sessions: Dict[str, Tuple[str, float]] = {}
        # 异步锁，确保并发安全
        self.lock = asyncio.Lock()

        logger.info(f"会话亲和性管理器初始化: TTL={ttl}s ({ttl/3600:.1f}h)")

    async def get_endpoint(self, conversation_id: str) -> Optional[str]:
        """获取会话绑定的 endpoint

        Args:
            conversation_id: 对话 ID

        Returns:
            绑定的 endpoint ID，如果没有绑定或已过期则返回 None
        """
        if not conversation_id:
            return None

        async with self.lock:
            if conversation_id in self.sessions:
                endpoint_id, expire_time = self.sessions[conversation_id]

                # 检查是否过期
                if time.time() < expire_time:
                    remaining = expire_time - time.time()
                    logger.debug(
                        f"会话绑定命中: {conversation_id[:8]}... -> {endpoint_id} "
                        f"(剩余 {remaining/60:.1f}min)"
                    )
                    return endpoint_id
                else:
                    # 过期，删除绑定
                    del self.sessions[conversation_id]
                    logger.debug(
                        f"会话绑定已过期: {conversation_id[:8]}... -> {endpoint_id}"
                    )

            return None

    async def bind_session(self, conversation_id: str, endpoint_id: str):
        """绑定会话到 endpoint

        Args:
            conversation_id: 对话 ID
            endpoint_id: Endpoint ID
        """
        if not conversation_id:
            return

        async with self.lock:
            expire_time = time.time() + self.ttl

            # 检查是否已有绑定
            if conversation_id in self.sessions:
                old_endpoint_id, _ = self.sessions[conversation_id]
                if old_endpoint_id != endpoint_id:
                    logger.info(
                        f"会话重新绑定: {conversation_id[:8]}... "
                        f"{old_endpoint_id} -> {endpoint_id}"
                    )
            else:
                logger.debug(
                    f"会话新绑定: {conversation_id[:8]}... -> {endpoint_id}"
                )

            # 更新或创建绑定
            self.sessions[conversation_id] = (endpoint_id, expire_time)

    async def unbind_session(self, conversation_id: str) -> bool:
        """解除会话绑定

        Args:
            conversation_id: 对话 ID

        Returns:
            True 如果成功解绑，False 如果没有绑定
        """
        if not conversation_id:
            return False

        async with self.lock:
            if conversation_id in self.sessions:
                endpoint_id, _ = self.sessions[conversation_id]
                del self.sessions[conversation_id]
                logger.info(
                    f"会话解绑: {conversation_id[:8]}... -> {endpoint_id}"
                )
                return True

            return False

    async def cleanup_expired(self) -> int:
        """清理过期会话（后台任务）

        Returns:
            清理的会话数量
        """
        async with self.lock:
            now = time.time()
            expired = [
                conv_id for conv_id, (_, expire_time) in self.sessions.items()
                if now > expire_time
            ]

            for conv_id in expired:
                endpoint_id, _ = self.sessions[conv_id]
                del self.sessions[conv_id]
                logger.debug(
                    f"清理过期会话: {conv_id[:8]}... -> {endpoint_id}"
                )

            if expired:
                logger.info(f"清理了 {len(expired)} 个过期会话")

            return len(expired)

    async def get_session_info(self, conversation_id: str) -> Optional[dict]:
        """获取会话信息

        Args:
            conversation_id: 对话 ID

        Returns:
            会话信息字典，如果没有绑定则返回 None
        """
        if not conversation_id:
            return None

        async with self.lock:
            if conversation_id in self.sessions:
                endpoint_id, expire_time = self.sessions[conversation_id]
                remaining = max(0, expire_time - time.time())

                return {
                    'conversation_id': conversation_id,
                    'endpoint_id': endpoint_id,
                    'expire_time': expire_time,
                    'remaining_seconds': remaining,
                    'remaining_minutes': remaining / 60,
                }

            return None

    async def get_all_sessions(self) -> dict:
        """获取所有会话信息

        Returns:
            所有会话的信息字典
        """
        async with self.lock:
            now = time.time()
            return {
                conv_id: {
                    'endpoint_id': endpoint_id,
                    'expire_time': expire_time,
                    'remaining_seconds': max(0, expire_time - now),
                }
                for conv_id, (endpoint_id, expire_time) in self.sessions.items()
            }

    async def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        async with self.lock:
            now = time.time()

            # 统计每个 endpoint 的会话数
            endpoint_counts: Dict[str, int] = {}
            active_sessions = 0
            expired_sessions = 0

            for endpoint_id, expire_time in self.sessions.values():
                if now < expire_time:
                    active_sessions += 1
                    endpoint_counts[endpoint_id] = \
                        endpoint_counts.get(endpoint_id, 0) + 1
                else:
                    expired_sessions += 1

            return {
                'total_sessions': len(self.sessions),
                'active_sessions': active_sessions,
                'expired_sessions': expired_sessions,
                'endpoint_distribution': endpoint_counts,
                'ttl_seconds': self.ttl,
            }

    async def start_cleanup_task(self, interval: int = 300):
        """启动后台清理任务

        Args:
            interval: 清理间隔（秒），默认 300 秒（5 分钟）
        """
        logger.info(f"启动会话清理任务: interval={interval}s")

        while True:
            try:
                await asyncio.sleep(interval)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                logger.info("会话清理任务已取消")
                break
            except Exception as e:
                logger.error(f"会话清理任务错误: {e}")
                # 继续运行，不中断清理任务
