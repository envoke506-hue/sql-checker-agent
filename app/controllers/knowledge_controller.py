"""
知识库索引与切块管理控制器 (Controller Layer - Knowledge)

【RESTful 规范说明】
- 路径: `/knowledge/indices` (名词复数，代表知识库索引资源集合)
- `GET /knowledge/indices/status`: 安全读取当前知识库索引状态、切块数量与元信息
- `POST /knowledge/indices`: 发起构建或增量刷新索引操作
"""

from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_knowledge_service
from app.models.dto.common import ApiResponse
from app.models.dto.knowledge import IndexStatusResponseData, ReindexRequest
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base Management"])


@router.get(
    "/indices/status",
    response_model=ApiResponse[IndexStatusResponseData],
    status_code=status.HTTP_200_OK,
    summary="获取规范知识库索引状态",
    description="查询当前知识库是否已索引、包含的切块列表摘要、源文件 SHA-256 哈希值与更新时间"
)
async def get_index_status_endpoint(
    service: KnowledgeService = Depends(get_knowledge_service)
) -> ApiResponse[IndexStatusResponseData]:
    """
    查询知识库索引状态端点
    """
    status_data = service.get_index_status()
    return ApiResponse(
        code=20000,
        message="查询知识库索引状态成功",
        data=status_data
    )


@router.post(
    "/indices",
    response_model=ApiResponse[IndexStatusResponseData],
    status_code=status.HTTP_200_OK,
    summary="触发构建或重建知识库索引",
    description="执行文档解析、AST 结构化切块、Ollama 2560 维向量计算与 BM25 稀疏模型训练持久化流水线"
)
async def reindex_knowledge_endpoint(
    request: ReindexRequest = ReindexRequest(),
    service: KnowledgeService = Depends(get_knowledge_service)
) -> ApiResponse[IndexStatusResponseData]:
    """
    触发索引构建端点 (支持 force=True 强制全量重跑)
    """
    status_data = await service.initialize_or_load(force=request.force)
    return ApiResponse(
        code=20000,
        message="知识库索引流水线执行完成",
        data=status_data
    )
