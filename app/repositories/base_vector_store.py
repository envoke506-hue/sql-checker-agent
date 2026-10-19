"""
向量存储仓储基础抽象接口 (Base Vector Store Repository)

【企业级架构规范】
遵循依赖倒置原则 (IoC) 与仓储模式 (Repository Pattern)，
定义向量数据库的标准接口契约，实现业务编排层 (Service) 与底层具体向量存储引擎 (NumPy / ChromaDB / Milvus) 的解耦。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple


class BaseVectorStoreRepository(ABC):
    """
    向量存储仓储抽象基类，规范向量的存入、持久化加载、存在性探测与余弦相似度检索契约
    """

    @abstractmethod
    def is_empty(self) -> bool:
        """检查当前索引是否为空或未加载"""
        pass

    @abstractmethod
    def save(
        self,
        chunk_ids: List[str],
        vectors: List[List[float]],
        metadatas: Optional[List[Dict]] = None
    ) -> None:
        """
        保存切块 ID、稠密向量列表及元数据至向量存储库并持久化

        :param chunk_ids: 切块全局唯一标识列表
        :param vectors: 对应的稠密向量浮点列表 (如 Ollama 2560 维)
        :param metadatas: 可选的标量元数据列表 (供元数据过滤使用)
        """
        pass

    @abstractmethod
    def load(self) -> bool:
        """
        从本地持久化介质或连接中加载/验证向量库索引状态

        :return: True 表示可用/加载成功，False 表示不存在或加载失败
        """
        pass

    @abstractmethod
    def exists(self) -> bool:
        """检查底层向量持久化数据是否存在且有效"""
        pass

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        """
        在多维空间中检索与查询向量最相似的候选切块 (按余弦相似度降序排列)

        :param query_vector: 查询文本计算后的稠密向量
        :param top_k: 期望返回的最大候选数量
        :param filter_metadata: 可选的标量过滤条件 (如 {"category": "naming"})
        :return: [(chunk_id, cosine_similarity_score), ...] 结果列表
        """
        pass
