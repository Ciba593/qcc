"""Claude 模型定义和常量

包含所有支持的 Claude 模型列表及其元数据
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ClaudeModel:
    """Claude 模型信息"""
    id: str  # API 使用的模型 ID
    name: str  # 显示名称
    description: str  # 描述
    context_window: int  # 上下文窗口大小（tokens）
    max_output: int  # 最大输出 tokens
    supports_vision: bool  # 是否支持图片
    price_input: float  # 输入价格（$/MTok）
    price_output: float  # 输出价格（$/MTok）
    recommended_for: str  # 推荐用途


# Claude 4.5 系列（最新，2025年9-10月发布）
CLAUDE_SONNET_4_5 = ClaudeModel(
    id="claude-sonnet-4-5-20250929",
    name="Claude Sonnet 4.5",
    description="最智能的模型，适合复杂代理和编码任务",
    context_window=200_000,
    max_output=64_000,
    supports_vision=True,
    price_input=3.0,
    price_output=15.0,
    recommended_for="复杂推理、编码、代理任务"
)

CLAUDE_HAIKU_4_5 = ClaudeModel(
    id="claude-haiku-4-5-20251001",
    name="Claude Haiku 4.5",
    description="最快的模型，接近前沿智能",
    context_window=200_000,
    max_output=64_000,
    supports_vision=True,
    price_input=1.0,
    price_output=5.0,
    recommended_for="高吞吐量、低成本、快速响应"
)

CLAUDE_OPUS_4_1 = ClaudeModel(
    id="claude-opus-4-1-20250805",
    name="Claude Opus 4.1",
    description="专业推理任务的顶级模型",
    context_window=200_000,
    max_output=32_000,
    supports_vision=True,
    price_input=15.0,
    price_output=75.0,
    recommended_for="专业推理、高难度任务"
)

# Claude 3.7 系列（2025年2月发布）
CLAUDE_SONNET_3_7 = ClaudeModel(
    id="claude-3-7-sonnet-20250219",
    name="Claude Sonnet 3.7",
    description="混合推理模型，支持快速响应和深度思考",
    context_window=200_000,
    max_output=64_000,  # 使用 beta header 可达 128K
    supports_vision=True,
    price_input=3.0,
    price_output=15.0,
    recommended_for="混合推理、灵活响应"
)

# Claude 3.5 系列（2024年发布，仍然广泛使用）
CLAUDE_SONNET_3_5 = ClaudeModel(
    id="claude-3-5-sonnet-20241022",
    name="Claude Sonnet 3.5",
    description="平衡性能和成本的经典选择",
    context_window=200_000,
    max_output=64_000,
    supports_vision=True,
    price_input=3.0,
    price_output=15.0,
    recommended_for="通用任务、编码"
)

CLAUDE_HAIKU_3_5 = ClaudeModel(
    id="claude-3-5-haiku-20241022",
    name="Claude Haiku 3.5",
    description="快速且经济的模型",
    context_window=200_000,
    max_output=64_000,
    supports_vision=True,
    price_input=1.0,
    price_output=5.0,
    recommended_for="健康检查、快速测试"
)

# 所有可用模型列表（按推荐程度排序）
ALL_MODELS: List[ClaudeModel] = [
    CLAUDE_SONNET_4_5,      # 最新最强
    CLAUDE_HAIKU_4_5,       # 最新最快
    CLAUDE_OPUS_4_1,        # 最强推理
    CLAUDE_SONNET_3_7,      # 混合推理
    CLAUDE_SONNET_3_5,      # 经典平衡
    CLAUDE_HAIKU_3_5,       # 经济实惠
]

# 模型分类
FAST_MODELS = [CLAUDE_HAIKU_4_5, CLAUDE_HAIKU_3_5]
BALANCED_MODELS = [CLAUDE_SONNET_4_5, CLAUDE_SONNET_3_7, CLAUDE_SONNET_3_5]
POWERFUL_MODELS = [CLAUDE_OPUS_4_1, CLAUDE_SONNET_4_5]

# 默认模型
DEFAULT_TEST_MODEL = CLAUDE_HAIKU_3_5.id  # 健康检查默认使用最便宜最快的
DEFAULT_PROXY_MODEL = None  # 代理默认使用客户端请求的模型


def get_model_by_id(model_id: str) -> ClaudeModel:
    """根据 ID 获取模型信息

    Args:
        model_id: 模型 ID

    Returns:
        ClaudeModel 对象，如果未找到则返回 None
    """
    for model in ALL_MODELS:
        if model.id == model_id:
            return model
    return None


def get_all_models_dict() -> List[Dict[str, Any]]:
    """获取所有模型的字典表示

    Returns:
        模型列表（字典格式）
    """
    return [
        {
            'id': model.id,
            'name': model.name,
            'description': model.description,
            'context_window': model.context_window,
            'max_output': model.max_output,
            'supports_vision': model.supports_vision,
            'price_input': model.price_input,
            'price_output': model.price_output,
            'recommended_for': model.recommended_for
        }
        for model in ALL_MODELS
    ]


def get_model_display_name(model_id: str) -> str:
    """获取模型的显示名称

    Args:
        model_id: 模型 ID

    Returns:
        显示名称，如果未找到则返回原 ID
    """
    model = get_model_by_id(model_id)
    return model.name if model else model_id
