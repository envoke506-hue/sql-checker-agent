"""
向量存储仓储基础抽象契约 (Base Vector Store Repository Contract)

【企业级架构规范 - 六边形架构 / 端口与适配器模式 (Ports and Adapters)】
1. 定义中立的抽象端口 (Port)，严禁具体向量库厂商的原生 API (如 collection.query, add, upsert 等) 渗透至业务代码；
2. 统一出入参契约：输入使用 VectorRecord / VectorQuery，输出使用 VectorSearchResult；
3. 保留针对平滑过渡的便捷适配重载 (save, search)，保证向后兼容性。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from app.models.dto.vector_store import VectorQuery, VectorRecord, VectorSearchResult


class BaseVectorStoreRepository(ABC):
    """
    向量存储仓储统一抽象契约接口 (Vector Store Port)
    """

    @abstractmethod
    def upsert(self, records: List[VectorRecord]) -> None:
        """
        批量幂等存入或更新标准向量记录

        :param records: 中立的 VectorRecord 领域实体列表
        """
        pass

    @abstractmethod
    def search_records(self, query: VectorQuery) -> List[VectorSearchResult]:
        """
        根据标准查询条件检索相似记录

        :param query: 中立的 VectorQuery 查询对象
        :return: 中立的 VectorSearchResult 结果列表 (按得分降序排列)
        """
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        """检查底层向量库当前是否为空"""
        pass

    @abstractmethod
    def count(self) -> int:
        """获取底层向量库中的总记录数"""
        pass

    @abstractmethod
    def load(self) -> bool:
        """从持久化媒介连接或加载索引"""
        pass

    @abstractmethod
    def exists(self) -> bool:
        """检查底层持久化存储是否存在"""
        pass

    # ---------------- 向后兼容的平滑适配方法 ----------------

    def save(
        self,
        chunk_ids: List[str],
        vectors: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        向后兼容便捷适配器：将散列入参自动包装为强类型 VectorRecord 后调用 upsert
        """
        if len(chunk_ids) != len(vectors):
            raise ValueError("chunk_ids 数量必须与 vectors 数量严格一致")

        records: List[VectorRecord] = []
        for i, (cid, vec) in enumerate(zip(chunk_ids, vectors)):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            records.append(VectorRecord(id=cid, vector=vec, metadata=meta))

        self.upsert(records)

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float]]:
        """
        向后兼容便捷适配器：执行检索并返回传统 [(chunk_id, score), ...] 元组列表
        """
        query = VectorQuery(
            vector=query_vector,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        results = self.search_records(query)
        return [(r.id, r.score) for r in results]
