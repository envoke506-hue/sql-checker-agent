"""
系统健康检查领域 DTO (Health DTO)
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ModelServiceStatus(BaseModel):
    """单个模型服务的连接状态"""
    name: str = Field(..., description="服务名称 (如 Ollama Embedding / Relay LLM)")
    model: str = Field(..., description="使用的具体模型标识")
    status: str = Field(..., description="运行状态 (healthy / unreachable / error)")
    latency_ms: Optional[float] = Field(default=None, description="测试调用耗时 (毫秒)")
    message: Optional[str] = Field(default=None, description="详细状态说明或错误原因")


class HealthResponseData(BaseModel):
    """系统健康检查汇总数据"""
    app_status: str = Field(default="running", description="应用程序运行状态")
    version: str = Field(..., description="系统版本号")
    services: List[ModelServiceStatus] = Field(default_factory=list, description="外部模型依赖服务状态清单")
