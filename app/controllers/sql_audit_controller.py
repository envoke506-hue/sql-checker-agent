"""
SQL 规范合规审查控制器 (Controller Layer - Injected)

【企业级规范知识点说明】
1. 依赖注入解耦:
   - 通过 `service: SqlAuditService = Depends(get_sql_audit_service)` 注入业务服务。
2. 异常交由全局拦截:
   - 移除了每个接口手写的 `try ... except Exception: raise HTTPException(500)` 样板代码。
   - 业务异常由底层抛出，FastAPI 全局异常处理器会自动将其截获并包装成标准的统一 JSON 结构。
"""

from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_sql_audit_service
from app.models.dto.common import ApiResponse
from app.models.dto.sql_audit import SqlAuditRequest, SqlAuditResponseData
from app.services.sql_audit_service import SqlAuditService

router = APIRouter(prefix="/sql", tags=["SQL Audit"])


@router.post(
    "/audits",
    response_model=ApiResponse[SqlAuditResponseData],
    status_code=status.HTTP_200_OK,
    summary="SQL 语句规范合规性审查接口",
    description="提交一段 SQL (如 CREATE TABLE)，基于数据库规范知识库进行逐项合规诊断，并返回 Markdown 报告与重构建议"
)
async def audit_sql_endpoint(
    request: SqlAuditRequest,
    service: SqlAuditService = Depends(get_sql_audit_service)
) -> ApiResponse[SqlAuditResponseData]:
    """
    SQL 审查端点处理函数 (异步非阻塞 + 依赖注入)
    """
    result_data = await service.audit_sql(request)
    return ApiResponse(
        code=20000,
        message="SQL 审查完成",
        data=result_data
    )
