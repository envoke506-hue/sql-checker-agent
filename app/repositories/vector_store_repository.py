"""
稠密向量存储仓储门面 (Vector Store Repository Facade)

【企业级架构规范】
1. 采用门面模式 (Facade Pattern) 与策略模式 (Strategy Pattern)，统一向量库对外访问入口；
2. 彻底屏蔽底层向量库技术细节，无论是 ChromaDB、NumPy 还是将来的 Milvus，均通过中立的 BaseVectorStoreRepository 契约调用；
3. 支持通过应用配置项 `VECTOR_STORE_TYPE` 在 'chroma' 与 'numpy' 之间灵活无缝切换，实现解耦与多引擎兼容；
4. 保证 MVC 分层中 Service 层 (KnowledgeService / RetrievalService) 与 Controller 接口契约 100% 向后兼容。
"""

from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.models.dto.vector_store import VectorQuery, VectorRecord, VectorSearchResult
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

        # 根据配置实例化底层具体存储引擎适配器
        if self.engine_type == "numpy":
            self._engine: BaseVectorStoreRepository = NumpyVectorStoreRepository(
                storage_dir=storage_dir or self.settings.storage_dir
            )
        else:
            # 默认使用企业级 ChromaDB 适配器
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
        return self._engine.count()

    def upsert(self, records: List[VectorRecord]) -> None:
        """
        批量存入或更新中立的 VectorRecord 实体
        """
        self._engine.upsert(records)

    def search_records(self, query: VectorQuery) -> List[VectorSearchResult]:
        """
        执行标准向量查询并返回中立的 VectorSearchResult 列表
        """
        return self._engine.search_records(query)

    def load(self) -> bool:
        """
        从底层持久化文件中恢复/探测向量索引

        :return: True 表示可用，False 表示文件不存在或未构建
        """
        return self._engine.load()

    def exists(self) -> bool:
        """检查底层向量持久化存储是否存在"""
        return self._engine.exists()
