"""
Chroma 向量数据库适配器 (ChromaDB Vector Store Adapter)

【企业级架构规范】
1. 实现 BaseVectorStoreRepository 端口契约，作为具体技术驱动适配器；
2. 彻底封装 chromadb 的所有原生 API 调用（client, collection, query, upsert）；
3. 异常防腐层：捕获所有 Chroma 底层异常并包装转译为企业统一的 VectorStoreException，防止底层异常泄露；
4. 距离转译层：将底层余弦距离 (cosine distance) 转换为统一标准化的余弦相似度 (cosine similarity)。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.exceptions import VectorStoreException
from app.models.dto.vector_store import VectorQuery, VectorRecord, VectorSearchResult
from app.repositories.base_vector_store import BaseVectorStoreRepository


class ChromaVectorStoreRepository(BaseVectorStoreRepository):
    """
    负责基于 ChromaDB 的向量存储、持久化、HNSW 索引检索与元数据过滤的适配器实现
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        self.settings = get_settings()
        self.persist_dir = Path(persist_dir or self.settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name or self.settings.chroma_collection_name

        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    def _get_client(self) -> chromadb.PersistentClient:
        """获取或惰性初始化 Chroma 本地持久化客户端"""
        if self._client is None:
            try:
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir),
                    settings=ChromaSettings(anonymized_telemetry=False)
                )
            except Exception as e:
                raise VectorStoreException(
                    message="初始化 ChromaDB 客户端失败",
                    detail=f"路径: {self.persist_dir}, 异常: {str(e)}"
                ) from e
        return self._client

    def _get_collection(self):
        """获取或创建指定名称的 Collection (空间度量设置为余弦距离 cosine)"""
        if self._collection is None:
            client = self._get_client()
            try:
                self._collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                raise VectorStoreException(
                    message=f"获取或创建 ChromaDB 集合 '{self.collection_name}' 失败",
                    detail=str(e)
                ) from e
        return self._collection

    def is_empty(self) -> bool:
        """检查集合中是否有数据"""
        return self.count() == 0

    def count(self) -> int:
        """获取集合中的向量总数"""
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    def upsert(self, records: List[VectorRecord]) -> None:
        """
        批量存入或更新中立的 VectorRecord 记录项
        """
        if not records:
            return

        collection = self._get_collection()

        chunk_ids = [r.id for r in records]
        embeddings = [r.vector for r in records]

        # Chroma 标量元数据值清洗 (仅支持 str, int, float, bool)
        clean_metadatas: List[Dict[str, Any]] = []
        for r in records:
            clean_m: Dict[str, Any] = {}
            for k, v in r.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_m[k] = v
                elif isinstance(v, list):
                    clean_m[k] = ",".join(str(item) for item in v)
                else:
                    clean_m[k] = str(v)
            clean_metadatas.append(clean_m)

        try:
            collection.upsert(
                ids=chunk_ids,
                embeddings=embeddings,
                metadatas=clean_metadatas
            )
        except Exception as e:
            raise VectorStoreException(
                message="ChromaDB 批量写入/更新向量记录失败",
                detail=str(e)
            ) from e

    def search_records(self, query: VectorQuery) -> List[VectorSearchResult]:
        """
        在 ChromaDB 中执行近邻检索，并将底层原生数据结构转译为中立的 VectorSearchResult
        """
        total = self.count()
        if total == 0:
            return []

        actual_k = min(query.top_k, total)
        col = self._get_collection()

        query_params = {
            "query_embeddings": [query.vector],
            "n_results": actual_k,
            "include": ["distances", "metadatas"]
        }
        if query.filter_metadata:
            query_params["where"] = query.filter_metadata

        try:
            raw_results = col.query(**query_params)
        except Exception as e:
            raise VectorStoreException(
                message="ChromaDB 执行向量相似度检索失败",
                detail=str(e)
            ) from e

        search_results: List[VectorSearchResult] = []
        ids = raw_results.get("ids", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0] if raw_results.get("metadatas") else [{}] * len(ids)

        for cid, dist, meta in zip(ids, distances, metadatas):
            # Chroma 在 hnsw:space=cosine 时返回余弦距离 d
            # 余弦相似度 = 1.0 - d
            sim = max(0.0, min(1.0, 1.0 - float(dist)))
            search_results.append(
                VectorSearchResult(
                    id=cid,
                    score=round(sim, 4),
                    metadata=meta or {}
                )
            )

        # 按相似度降序排列
        search_results.sort(key=lambda x: x.score, reverse=True)
        return search_results

    def load(self) -> bool:
        """
        验证并探测 Chroma 本地持久化索引
        """
        try:
            return self.count() > 0
        except Exception:
            return False

    def exists(self) -> bool:
        """检查 Chroma 持久化目录与集合数据是否存在"""
        return self.persist_dir.exists() and self.count() > 0
