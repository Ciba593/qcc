"""
错误分类器

参考 fuergaosi233/claude-code-proxy 的错误分类机制，细化错误处理策略。
"""

from enum import Enum
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型枚举"""
    TRANSIENT = 'transient'      # 暂时性错误（快速重试）
    RATE_LIMIT = 'rate_limit'    # 限流（延迟重试或切换）
    AUTH = 'auth'                # 认证失败（禁用 endpoint）
    PERMANENT = 'permanent'      # 永久失败（立即切换）
    UNKNOWN = 'unknown'          # 未知错误（保守处理）


class ErrorClassifier:
    """错误分类器（Error Classifier）

    功能：
    - 将错误信息分类为不同类型
    - 为每种错误类型提供推荐的处理策略
    - 支持细粒度的错误处理决策

    参考：fuergaosi233/claude-code-proxy 的错误分类逻辑
    """

    # 暂时性错误模式（网络相关，可快速重试）
    TRANSIENT_ERRORS = [
        'closing transport',
        'connection reset',
        'broken pipe',
        'server disconnected',
        'connection aborted',
        'cannot write',
        'timeout',
        'timed out',
        'connection timeout',
        'read timeout',
        'temporarily unavailable',
        'service unavailable',
        '503',
    ]

    # 限流错误模式
    RATE_LIMIT_ERRORS = [
        'rate limit',
        '429',
        'too many requests',
        'quota exceeded',
        'rate_limit_exceeded',
        'requests per minute',
        'requests per day',
        'throttled',
    ]

    # 认证错误模式
    AUTH_ERRORS = [
        'unauthorized',
        '401',
        'invalid api key',
        'authentication failed',
        'invalid_api_key',
        'permission_denied',
        'forbidden',
        '403',
        'invalid_request_error',
        'api key',
    ]

    # 永久性错误模式
    PERMANENT_ERRORS = [
        'not found',
        '404',
        'invalid request',
        '400',
        'bad request',
        'model not found',
        'invalid_model',
        'invalid_type',
        'invalid_request_error',
        'validation_error',
        'malformed',
    ]

    @classmethod
    def classify(cls, error_str: str) -> Tuple[ErrorType, str]:
        """分类错误并返回推荐操作

        Args:
            error_str: 错误信息字符串

        Returns:
            (错误类型, 推荐操作描述)
        """
        if not error_str:
            return (ErrorType.UNKNOWN, "空错误信息")

        error_lower = error_str.lower()

        # 检查暂时性错误
        if any(err in error_lower for err in cls.TRANSIENT_ERRORS):
            return (
                ErrorType.TRANSIENT,
                "暂时性网络错误，快速重试同一节点"
            )

        # 检查限流错误
        elif any(err in error_lower for err in cls.RATE_LIMIT_ERRORS):
            return (
                ErrorType.RATE_LIMIT,
                "API 限流，延迟 30 秒重试或立即切换节点"
            )

        # 检查认证错误
        elif any(err in error_lower for err in cls.AUTH_ERRORS):
            return (
                ErrorType.AUTH,
                "认证失败，禁用此 endpoint"
            )

        # 检查永久性错误
        elif any(err in error_lower for err in cls.PERMANENT_ERRORS):
            return (
                ErrorType.PERMANENT,
                "永久性错误，立即切换节点"
            )

        # 未知错误
        else:
            return (
                ErrorType.UNKNOWN,
                "未知错误，保守处理（切换节点）"
            )

    @classmethod
    def is_retryable(cls, error_type: ErrorType) -> bool:
        """判断错误是否可重试

        Args:
            error_type: 错误类型

        Returns:
            True 如果可重试，False 否则
        """
        # 暂时性错误和未知错误可重试
        return error_type in (ErrorType.TRANSIENT, ErrorType.UNKNOWN)

    @classmethod
    def should_switch_endpoint(cls, error_type: ErrorType) -> bool:
        """判断是否应该切换 endpoint

        Args:
            error_type: 错误类型

        Returns:
            True 如果应该切换，False 否则
        """
        # 限流、认证失败、永久错误应该切换
        return error_type in (
            ErrorType.RATE_LIMIT,
            ErrorType.AUTH,
            ErrorType.PERMANENT
        )

    @classmethod
    def should_disable_endpoint(cls, error_type: ErrorType) -> bool:
        """判断是否应该禁用 endpoint

        Args:
            error_type: 错误类型

        Returns:
            True 如果应该禁用，False 否则
        """
        # 只有认证失败才禁用
        return error_type == ErrorType.AUTH

    @classmethod
    def get_retry_delay(cls, error_type: ErrorType) -> float:
        """获取建议的重试延迟时间（秒）

        Args:
            error_type: 错误类型

        Returns:
            延迟秒数
        """
        if error_type == ErrorType.TRANSIENT:
            return 0.5  # 暂时性错误快速重试
        elif error_type == ErrorType.RATE_LIMIT:
            return 30.0  # 限流延迟 30 秒
        elif error_type == ErrorType.UNKNOWN:
            return 1.0  # 未知错误延迟 1 秒
        else:
            return 0.0  # 其他不重试

    @classmethod
    def classify_and_log(cls, error_str: str, logger_instance=None) -> ErrorType:
        """分类错误并记录日志

        Args:
            error_str: 错误信息字符串
            logger_instance: 日志记录器实例（可选）

        Returns:
            错误类型
        """
        error_type, action = cls.classify(error_str)

        log_msg = (
            f"错误分类: {error_type.value} | "
            f"推荐操作: {action} | "
            f"错误: {error_str[:100]}"
        )

        if logger_instance:
            if error_type == ErrorType.AUTH:
                logger_instance.error(log_msg)
            elif error_type == ErrorType.PERMANENT:
                logger_instance.warning(log_msg)
            else:
                logger_instance.info(log_msg)
        else:
            logger.info(log_msg)

        return error_type


# 辅助函数，方便直接调用
def classify_error(error_str: str) -> Tuple[ErrorType, str]:
    """分类错误的便捷函数

    Args:
        error_str: 错误信息字符串

    Returns:
        (错误类型, 推荐操作描述)
    """
    return ErrorClassifier.classify(error_str)
