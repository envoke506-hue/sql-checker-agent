"""
系统健康检查控制器 (Controller Layer - Injected)

【框架核心知识点说明】
- 依赖注入: `service: HealthService = Depends(get_health_service)`。
- 由 FastAPI 在每个 HTTP 请求到达时自动调用 `get_health_service` 组装服务实例，消除类之间的硬编码耦合。
"""

from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_health_service
from app.models.dto.common import ApiResponse
from app.models.dto.health import HealthResponseData
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["Health & System"])


@router.get(
    "",
    response_model=ApiResponse[HealthResponseData],
    status_code=status.HTTP_200_OK,
    summary="系统运行与模型依赖健康体检接口",
    description="并发探测检查应用程序状态，以及本地 Ollama 向量模型和云端中转站大模型 API 的实时连通性与延迟"
)
async def get_health_status(
    service: HealthService = Depends(get_health_service)
) -> ApiResponse[HealthResponseData]:
    """
    健康检查端点处理函数 (通过 Depends 注入 HealthService)
    """
    health_data = await service.check_system_health()
    return ApiResponse(
        code=20000,
        message="系统与依赖服务体检完成",
        data=health_data
    )
