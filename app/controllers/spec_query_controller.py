"""
规范知识问答控制器 (Controller Layer - Injected)

【企业级规范知识点说明】
- 采用 Depends 注入服务；
- 异步非阻塞响应，异常全量冒泡交由全局拦截器。
"""

from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_spec_query_service
from app.models.dto.common import ApiResponse
from app.models.dto.spec_query import SpecQueryRequest, SpecQueryResponseData
from app.services.spec_query_service import SpecQueryService

router = APIRouter(prefix="/spec", tags=["Specification Query"])


@router.post(
    "/queries",
    response_model=ApiResponse[SpecQueryResponseData],
    status_code=status.HTTP_200_OK,
    summary="数据库表设计规范智能问答接口",
    description="向规范知识库发起自然语言咨询提问，基于 RAG 返回严格依据规范生成的 Markdown 解答与条目引用"
)
async def query_specification_endpoint(
    request: SpecQueryRequest,
    service: SpecQueryService = Depends(get_spec_query_service)
) -> ApiResponse[SpecQueryResponseData]:
    """
    规范问答端点处理函数 (异步非阻塞 + 依赖注入)
    """
    result_data = await service.query_spec(request)
    return ApiResponse(
        code=20000,
        message="规范咨询查询成功",
        data=result_data
    )
