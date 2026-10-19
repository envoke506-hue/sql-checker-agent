"""
向量存储通用数据传输对象 (Vector Store DTO)

【企业级架构规范】
定义厂商中立的向量记录实体、检索入参和返回契约，
坚决防止具体向量库（如 ChromaDB / Milvus / FAISS）的原生数据结构泄漏至 Service 业务层。
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VectorRecord(BaseModel):
    """
    通用向量存储记录项 (与底层向量数据库彻底解耦)
    """
    id: str = Field(..., description="切块或记录全局唯一标识符")
    vector: List[float] = Field(..., description="稠密浮点向量数组 (如 2560 维)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="关联的标量元数据 (如 category, heading_path, section 等)"
    )


class VectorQuery(BaseModel):
    """
    通用向量检索查询请求参数
    """
    vector: List[float] = Field(..., description="待检索的目标查询向量")
    top_k: int = Field(default=5, description="期望返回的最大相似记录数")
    filter_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="可选的标量元数据前置过滤条件 (例如 {'category': 'naming'})"
    )


class VectorSearchResult(BaseModel):
    """
    通用向量相似度检索命中实体
    """
    id: str = Field(..., description="命中的切块/记录全局唯一标识符")
    score: float = Field(..., description="规范化后的余弦相似度得分 [0.0, 1.0]")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="切块关联的标量元数据")

    def __iter__(self):
        """
        支持向后兼容的元组解包语法:
        chunk_id, score = result
        """
        return iter((self.id, self.score))

    def __getitem__(self, item: int):
        """
        支持向后兼容的下标访问语法:
        result[0] -> chunk_id, result[1] -> score
        """
        if item == 0:
            return self.id
        elif item == 1:
            return self.score
        raise IndexError("VectorSearchResult 仅支持索引 0 (id) 与 1 (score)")
