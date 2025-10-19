"""QCC Load Balancer - 负载均衡器"""

import random
import logging
from typing import List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class LoadBalanceStrategy(Enum):
    """负载均衡策略"""
    WEIGHTED = "weighted"  # 加权轮询
    ROUND_ROBIN = "round_robin"  # 轮询
    RANDOM = "random"  # 随机
    LEAST_CONNECTIONS = "least_connections"  # 最少连接
    PRIORITY_FAILOVER = "priority_failover"  # 主备优先级（优先使用低priority值的节点）


class LoadBalancer:
    """负载均衡器

    支持多种负载均衡策略选择最佳 endpoint
    """

    def __init__(self, strategy: str = "weighted"):
        """初始化负载均衡器

        Args:
            strategy: 负载均衡策略
        """
        self.strategy = LoadBalanceStrategy(strategy)
        self.round_robin_index = 0

    async def select_endpoint(self, endpoints: List) -> Optional:
        """选择 endpoint（支持降级策略）

        降级策略：
        1. 优先选择 healthy 的 endpoint
        2. 如果没有 healthy，降级选择 degraded 的 endpoint
        3. 如果也没有 degraded，作为最后手段选择任何可用的 endpoint

        Args:
            endpoints: 可用的 endpoint 列表

        Returns:
            选中的 endpoint，如果没有可用的返回 None
        """
        logger.debug(f"LoadBalancer.select_endpoint 调用: 策略={self.strategy.value}, 输入 endpoints={len(endpoints)}")

        if not endpoints:
            logger.warning("没有可用的 endpoints")
            return None

        # 分类 endpoint
        healthy_endpoints = []
        degraded_endpoints = []

        for ep in endpoints:
            status = ep.health_status.get('status', 'unknown')
            if ep.is_healthy():
                healthy_endpoints.append(ep)
            elif status == 'degraded':
                degraded_endpoints.append(ep)

        logger.debug(f"健康 endpoints: {len(healthy_endpoints)}/{len(endpoints)}")
        logger.debug(f"降级 endpoints: {len(degraded_endpoints)}/{len(endpoints)}")

        for ep in endpoints:
            logger.debug(f"  - Endpoint {ep.id}: priority={ep.priority}, healthy={ep.is_healthy()}, status={ep.health_status}")

        # 降级策略：healthy > degraded > any
        selected_endpoints = None
        strategy_used = ""

        if healthy_endpoints:
            selected_endpoints = healthy_endpoints
            strategy_used = "healthy"
        elif degraded_endpoints:
            selected_endpoints = degraded_endpoints
            strategy_used = "degraded (降级)"
            logger.warning(f"没有健康 endpoints，降级使用 {len(degraded_endpoints)} 个 degraded endpoint")
        elif endpoints:
            # 极端情况：使用任何可用的 endpoint（包括 unhealthy）
            selected_endpoints = endpoints
            strategy_used = "any (极端降级)"
            logger.error(f"没有健康/降级 endpoints，极端降级使用所有 {len(endpoints)} 个 endpoint")
        else:
            logger.warning("没有可用的 endpoints")
            return None

        # 应用负载均衡策略
        selected = None
        if self.strategy == LoadBalanceStrategy.WEIGHTED:
            selected = self._weighted_select(selected_endpoints)
        elif self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            selected = self._round_robin_select(selected_endpoints)
        elif self.strategy == LoadBalanceStrategy.RANDOM:
            selected = self._random_select(selected_endpoints)
        elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            selected = self._least_connections_select(selected_endpoints)
        elif self.strategy == LoadBalanceStrategy.PRIORITY_FAILOVER:
            selected = self._priority_failover_select(selected_endpoints)
        else:
            selected = selected_endpoints[0]

        logger.info(f"负载均衡器选择: {selected.id if selected else 'None'} (策略: {self.strategy.value}, 类型: {strategy_used})")
        return selected

    def _weighted_select(self, endpoints: List):
        """加权随机选择"""
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return random.choice(endpoints)

        rand_weight = random.uniform(0, total_weight)
        cumulative_weight = 0

        for endpoint in endpoints:
            cumulative_weight += endpoint.weight
            if rand_weight <= cumulative_weight:
                return endpoint

        return endpoints[-1]

    def _round_robin_select(self, endpoints: List):
        """轮询选择"""
        endpoint = endpoints[self.round_robin_index % len(endpoints)]
        self.round_robin_index += 1
        return endpoint

    def _random_select(self, endpoints: List):
        """随机选择"""
        return random.choice(endpoints)

    def _least_connections_select(self, endpoints: List):
        """最少连接选择（基于总请求数）"""
        return min(endpoints, key=lambda ep: ep.health_status['total_requests'])

    def _priority_failover_select(self, endpoints: List):
        """主备优先级选择

        按照 priority 值从小到大排序，始终选择优先级最高（数字最小）的健康节点。
        只有当高优先级节点不健康时，才会自动切换到低优先级节点。
        一旦高优先级节点恢复健康，下次请求会立即切换回去。

        Args:
            endpoints: 健康的 endpoint 列表

        Returns:
            优先级最高的健康 endpoint
        """
        # 按 priority 值从小到大排序（数字越小优先级越高）
        sorted_endpoints = sorted(endpoints, key=lambda ep: ep.priority)

        logger.debug(f"优先级排序后的 endpoints:")
        for ep in sorted_endpoints:
            logger.debug(f"  - {ep.id}: priority={ep.priority}")

        # 返回优先级最高（priority 值最小）的节点
        selected = sorted_endpoints[0]
        logger.debug(f"选择优先级最高的 endpoint: {selected.id} (priority={selected.priority})")
        return selected
