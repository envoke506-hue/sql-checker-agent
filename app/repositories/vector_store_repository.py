"""
稠密向量存储仓储门面 (Vector Store Repository Facade)

【企业级架构规范】
1. 采用门面模式 (Facade Pattern) 与策略模式 (Strategy Pattern)，统一向量库对外访问入口；
2. 默认装配并驱动企业级 ChromaDB 向量数据库 (ChromaVectorStoreRepository)，支持 HNSW 索引与标量元数据过滤；
3. 支持通过应用配置项 `VECTOR_STORE_TYPE` 在 'chroma' 与 'numpy' 之间灵活无缝切换，实现解耦与多引擎兼容；
4. 保证 MVC 分层中 Service 层 (KnowledgeService / RetrievalService) 与 Controller 接口契约 100% 向后兼容。
"""

from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.repositories.base_vector_store import BaseVectorStoreRepository
from app.repositories.chroma_vector_store_repository import ChromaVectorStoreRepository
from app.repositories.numpy_vector_store_repository import NumpyVectorStoreRepository


class VectorStoreRepository(BaseVectorStoreRepository):
    """
    向量存储仓储门面类，实现统一存储契约与动态引擎调度
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        engine_type: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        self.settings = get_settings()
        self.engine_type = (engine_type or self.settings.vector_store_type).lower()

        # 根据配置实例化底层具体存储引擎
        if self.engine_type == "numpy":
            self._engine: BaseVectorStoreRepository = NumpyVectorStoreRepository(
                storage_dir=storage_dir or self.settings.storage_dir
            )
        else:
            # 默认使用企业级 ChromaDB 引擎
            self._engine = ChromaVectorStoreRepository(
                persist_dir=storage_dir or self.settings.chroma_persist_dir,
                collection_name=collection_name or self.settings.chroma_collection_name
            )

    @property
    def active_engine(self) -> str:
        """获取当前激活的存储引擎名称"""
        return self.engine_type

    def is_empty(self) -> bool:
        """检查底层存储中向量索引是否为空"""
        return self._engine.is_empty()

    def count(self) -> int:
        """获取向量总数"""
        if hasattr(self._engine, "count"):
            return self._engine.count()
        return 0 if self.is_empty() else len(getattr(self._engine, "chunk_ids", []))

    def save(
        self,
        chunk_ids: List[str],
        vectors: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        保存切块 ID、稠密向量列表及可选元数据至底层向量库

        :param chunk_ids: 切块 ID 列表
        :param vectors: 对应的 2560 维浮点数组列表
        :param metadatas: 标量元数据字典列表 (ChromaDB 原生支持过滤)
        """
        self._engine.save(chunk_ids=chunk_ids, vectors=vectors, metadatas=metadatas)

    def load(self) -> bool:
        """
        从底层持久化文件中恢复/探测向量索引

        :return: True 表示可用，False 表示文件不存在或未构建
        """
        return self._engine.load()

    def exists(self) -> bool:
        """检查底层向量持久化存储是否存在"""
        return self._engine.exists()

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        """
        在底层向量库中执行基于余弦相似度的近邻检索并返回 Top-K 结果

        :param query_vector: 用户问题计算后的 2560 维向量
        :param top_k: 期望召回的候选数量
        :param filter_metadata: 可选的标量元数据过滤条件
        :return: [(chunk_id, cosine_similarity_score), ...] 按相似度降序排列
        """
        return self._engine.search(
            query_vector=query_vector,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
