"""
优先级管理 API 路由
对应 CLI: priority set/list/switch/history/policy
"""

from fastapi import APIRouter, HTTPException
from ..models import ApiResponse

router = APIRouter()


@router.get("")
async def get_priority_config():
    """获取优先级配置 - 对应 CLI: qcc priority list"""
    # TODO: 实现优先级管理
    return ApiResponse(
        success=True,
        data={
            "primary": None,
            "secondary": None,
            "fallback": None
        },
        message="优先级功能开发中"
    )


@router.get("/history")
async def get_priority_history():
    """获取切换历史 - 对应 CLI: qcc priority history"""
    return ApiResponse(
        success=True,
        data=[],
        message="历史记录功能开发中"
    )
