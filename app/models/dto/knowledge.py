"""
知识库索引与切块管理领域 DTO (Knowledge DTO)

【架构知识点说明】
- 负责知识库构建 (Indexing)、增量更新与状态查询的请求响应契约。
- 遵循 RESTful 规范，状态码与业务数据载荷明确。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ReindexRequest(BaseModel):
    """
    重建知识库索引请求入参
    """
    force: bool = Field(
        default=False,
        description="是否强制全量重建索引 (True: 忽略文件哈希缓存，重新调用 Ollama 计算向量；False: 哈希未变时直接复用缓存)"
    )


class ChunkSummary(BaseModel):
    """切块摘要简报"""
    chunk_id: str = Field(..., description="切块唯一标识")
    heading_path: str = Field(..., description="面包屑层级路径")
    category: str = Field(..., description="所属规范分类")
    char_count: int = Field(..., description="正文字符长度")


class IndexStatusResponseData(BaseModel):
    """
    知识库索引状态详情响应实体
    """
    is_indexed: bool = Field(..., description="是否已构建并加载索引")
    chunk_count: int = Field(..., description="当前知识库切块总量")
    doc_path: str = Field(..., description="源规范文件路径")
    doc_hash: str = Field(..., description="源文件 SHA-256 内容哈希值")
    dimension: int = Field(default=2560, description="向量维度 (Qwen3-Embedding:4b 为 2560)")
    categories: List[str] = Field(default_factory=list, description="包含的规范大类标签清单")
    chunks: List[ChunkSummary] = Field(default_factory=list, description="切块列表摘要")
    last_updated: Optional[str] = Field(default=None, description="最后一次索引构建时间戳")
