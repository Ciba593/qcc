"""
API 响应模型
使用 Pydantic 定义统一的响应格式
"""

from pydantic import BaseModel
from typing import Any, Optional, Dict, List
from datetime import datetime


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    timestamp: str = datetime.now().isoformat()


class ErrorResponse(BaseModel):
    """错误响应格式"""
    success: bool = False
    error: Dict[str, Any]
    timestamp: str = datetime.now().isoformat()


class ConfigProfileModel(BaseModel):
    """配置档案模型"""
    name: str
    description: Optional[str] = ""
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    endpoints: Optional[List[Dict[str, Any]]] = []
    is_default: bool = False
    priority_level: Optional[str] = None
    enabled: bool = True
    last_used: Optional[str] = None


class EndpointModel(BaseModel):
    """Endpoint 模型"""
    id: str
    base_url: str
    api_key: str
    weight: int = 100
    priority: int = 0
    enabled: bool = True
    health_status: Optional[str] = "unknown"
    consecutive_failures: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0


class ProxyStatusModel(BaseModel):
    """代理服务状态模型"""
    running: bool
    pid: Optional[int] = None
    host: str = "127.0.0.1"
    port: int = 7860
    uptime: Optional[int] = None
    cluster: Optional[str] = None


class HealthStatusModel(BaseModel):
    """健康状态模型"""
    endpoint_id: str
    status: str  # healthy, degraded, unhealthy, unknown
    last_check: Optional[str] = None
    consecutive_failures: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0


class QueueItemModel(BaseModel):
    """队列项模型"""
    request_id: str
    endpoint_id: str
    status: str  # pending, retrying, success, failed
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    created_at: str
    next_retry_at: Optional[str] = None
