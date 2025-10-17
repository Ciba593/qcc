"""动态权重调整模块"""

import logging
from typing import Dict
from .performance_metrics import PerformanceMetrics

logger = logging.getLogger(__name__)


class WeightAdjustmentStrategy:
    """权重调整策略配置

    定义如何根据性能指标调整 endpoint 权重的策略参数。
    """

    def __init__(self):
        """初始化策略参数"""
        # 权重范围
        self.base_weight = 100
        self.min_weight = 10
        self.max_weight = 200

        # 调整因子（权重分配，总和应为 1.0）
        self.response_time_factor = 0.3    # 响应时间影响因子
        self.success_rate_factor = 0.4     # 成功率影响因子
        self.stability_factor = 0.2        # 稳定性影响因子
        self.consecutive_failure_factor = 0.1  # 连续失败影响因子

        # 平滑调整参数
        self.smooth_factor = 0.7  # 新权重的平滑系数 (0-1)

        # 响应时间基准（毫秒）
        self.ideal_response_time = 200  # 理想响应时间
        self.response_time_step = 100   # 每增加 100ms 减少的评分


class DynamicWeightAdjuster:
    """动态权重调整器

    根据 endpoint 的实际性能表现自动调整其权重，
    实现智能的负载均衡。
    """

    def __init__(self, strategy: WeightAdjustmentStrategy = None):
        """初始化权重调整器

        Args:
            strategy: 调整策略，默认使用标准策略
        """
        self.strategy = strategy or WeightAdjustmentStrategy()
        self.metrics_store: Dict[str, PerformanceMetrics] = {}

    def calculate_response_score(self, avg_response_time: float) -> float:
        """计算响应时间评分 (0-100)

        响应时间越快，评分越高。

        Args:
            avg_response_time: 平均响应时间（毫秒）

        Returns:
            响应时间评分
        """
        if avg_response_time <= 0:
            return 0.0

        # 基于理想响应时间计算评分
        # 理想响应时间 = 100 分
        # 每增加 step ms 减少 10 分
        deviation = avg_response_time - self.strategy.ideal_response_time
        score = 100 - (deviation / self.strategy.response_time_step) * 10

        return max(0, min(100, score))

    def calculate_failure_penalty(self, consecutive_failures: int) -> float:
        """计算连续失败惩罚系数 (0-1)

        连续失败次数越多，惩罚越重。

        Args:
            consecutive_failures: 连续失败次数

        Returns:
            惩罚系数，1.0 表示无惩罚，0.2 表示最大惩罚
        """
        if consecutive_failures <= 0:
            return 1.0

        # 连续失败 1 次: 0.8
        # 连续失败 2 次: 0.6
        # 连续失败 3 次: 0.4
        # 连续失败 4+ 次: 0.2
        penalty = max(0.2, 1.0 - (consecutive_failures * 0.2))
        return penalty

    def calculate_new_weight(
        self,
        endpoint_id: str,
        current_weight: float,
        metrics: PerformanceMetrics
    ) -> float:
        """计算新的权重

        综合考虑响应时间、成功率、稳定性和连续失败等因素。

        Args:
            endpoint_id: Endpoint ID
            current_weight: 当前权重
            metrics: 性能指标

        Returns:
            新的权重值
        """
        # 1. 响应时间评分 (0-100)
        response_score = self.calculate_response_score(metrics.avg_response_time)

        # 2. 成功率评分 (0-100)
        success_score = metrics.recent_success_rate

        # 3. 稳定性评分 (0-100)
        stability_score = metrics.stability_score

        # 4. 连续失败惩罚系数 (0-1)
        failure_penalty = self.calculate_failure_penalty(
            metrics.consecutive_failures
        )

        # 综合计算新权重
        # 各因子加权求和，然后应用连续失败惩罚
        weighted_score = (
            response_score * self.strategy.response_time_factor +
            success_score * self.strategy.success_rate_factor +
            stability_score * self.strategy.stability_factor
        ) * failure_penalty

        # 将评分转换为权重（0-100 分 → min_weight-max_weight）
        weight_range = self.strategy.max_weight - self.strategy.min_weight
        new_weight = (
            self.strategy.min_weight +
            (weighted_score / 100) * weight_range
        )

        # 平滑调整：新权重 = 旧权重 * (1 - α) + 新计算权重 * α
        # 这样可以避免权重剧烈波动
        smoothed_weight = (
            current_weight * (1 - self.strategy.smooth_factor) +
            new_weight * self.strategy.smooth_factor
        )

        # 限制在范围内
        final_weight = max(
            self.strategy.min_weight,
            min(self.strategy.max_weight, smoothed_weight)
        )

        return round(final_weight, 2)

    def adjust_endpoint_weight(
        self,
        endpoint,
        metrics: PerformanceMetrics
    ) -> float:
        """调整 endpoint 的权重

        Args:
            endpoint: Endpoint 实例
            metrics: 性能指标

        Returns:
            调整后的新权重
        """
        current_weight = endpoint.weight
        new_weight = self.calculate_new_weight(
            endpoint.id,
            current_weight,
            metrics
        )

        # 记录权重变化（仅当变化超过 1 时才记录）
        if abs(new_weight - current_weight) > 1:
            change = new_weight - current_weight
            change_pct = (change / current_weight) * 100

            logger.info(
                f"📊 权重调整: {endpoint.id}\n"
                f"   当前权重: {current_weight:.2f}\n"
                f"   新权重: {new_weight:.2f} ({change:+.2f}, {change_pct:+.1f}%)\n"
                f"   原因:\n"
                f"     - 平均响应: {metrics.avg_response_time:.0f}ms\n"
                f"     - 成功率: {metrics.recent_success_rate:.1f}%\n"
                f"     - 稳定性: {metrics.stability_score:.1f}\n"
                f"     - 连续失败: {metrics.consecutive_failures}"
            )

        return new_weight

    def adjust_all_weights(
        self,
        endpoints: list,
        metrics_dict: Dict[str, PerformanceMetrics]
    ) -> Dict[str, float]:
        """批量调整所有 endpoint 的权重

        Args:
            endpoints: Endpoint 列表
            metrics_dict: Endpoint ID -> PerformanceMetrics 的映射

        Returns:
            Endpoint ID -> 新权重 的映射
        """
        new_weights = {}

        for endpoint in endpoints:
            metrics = metrics_dict.get(endpoint.id)

            # 检查次数太少时不调整权重
            if not metrics or metrics.total_checks < 3:
                logger.debug(
                    f"Endpoint {endpoint.id} 检查次数不足，跳过权重调整"
                )
                continue

            new_weight = self.adjust_endpoint_weight(endpoint, metrics)
            new_weights[endpoint.id] = new_weight

        return new_weights

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"DynamicWeightAdjuster("
            f"strategy={self.strategy.__class__.__name__})"
        )
