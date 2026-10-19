"""
Chroma 向量数据库仓储 (ChromaDB Vector Store Repository)

【企业级架构规范】
1. 继承 BaseVectorStoreRepository，严格遵循仓储模式 (Repository Pattern)；
2. 基于 chromadb.PersistentClient 实现本地磁盘持久化与基于 HNSW 图的高维近邻检索；
3. 将距离度量配置为余弦空间 (cosine)，并精准转化为 [0, 1] 范围的余弦相似度；
4. 深度支持标量元数据存储与 where 表达式下推过滤 (Push-down Filtering)。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.repositories.base_vector_store import BaseVectorStoreRepository


class ChromaVectorStoreRepository(BaseVectorStoreRepository):
    """
    负责基于 ChromaDB 的向量存储、磁盘持久化、HNSW 索引检索与元数据过滤
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
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        return self._client

    def _get_collection(self):
        """获取或创建指定名称的 Collection (空间度量设置为余弦距离 cosine)"""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def is_empty(self) -> bool:
        """检查集合中是否有数据"""
        try:
            return self._get_collection().count() == 0
        except Exception:
            return True

    def count(self) -> int:
        """获取集合中的向量总数"""
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    def save(
        self,
        chunk_ids: List[str],
        vectors: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        保存/更新切块向量至 ChromaDB Collection 中并持久化

        :param chunk_ids: 切块 ID 列表
        :param vectors: 对应的 2560 维浮点数组列表
        :param metadatas: 切块元数据字典列表 (用于标量前置过滤)
        """
        if len(chunk_ids) != len(vectors):
            raise ValueError("chunk_ids 数量必须与 vectors 数量严格一致")

        collection = self._get_collection()

        # Chroma 要求 metadata 字典的值必须是 str, int, float, bool
        clean_metadatas = []
        if metadatas:
            for m in metadatas:
                clean_m = {}
                for k, v in m.items():
                    if isinstance(v, (str, int, float, bool)):
                        clean_m[k] = v
                    elif isinstance(v, list):
                        clean_m[k] = ",".join(str(item) for item in v)
                    else:
                        clean_m[k] = str(v)
                clean_metadatas.append(clean_m)
        else:
            clean_metadatas = [{"chunk_id": cid} for cid in chunk_ids]

        # 使用 upsert 幂等添加或更新
        collection.upsert(
            ids=chunk_ids,
            embeddings=vectors,
            metadatas=clean_metadatas
        )

    def load(self) -> bool:
        """
        验证并连接 Chroma 本地持久化索引
        """
        try:
            col = self._get_collection()
            return col.count() > 0
        except Exception:
            return False

    def exists(self) -> bool:
        """检查 Chroma 持久化目录与集合数据是否存在"""
        return self.persist_dir.exists() and self.count() > 0

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        """
        在 ChromaDB 中基于 HNSW 执行向量余弦相似度检索

        :param query_vector: 用户问题计算后的 2560 维向量
        :param top_k: 期望召回的候选数量
        :param filter_metadata: 标量过滤条件 (如 {"category": "naming"})
        :return: [(chunk_id, cosine_similarity_score), ...] 按相似度降序排列
        """
        total = self.count()
        if total == 0:
            return []

        actual_k = min(top_k, total)
        col = self._get_collection()

        query_params = {
            "query_embeddings": [query_vector],
            "n_results": actual_k,
            "include": ["distances", "metadatas"]
        }
        if filter_metadata:
            query_params["where"] = filter_metadata

        results = col.query(**query_params)

        hits: List[Tuple[str, float]] = []
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for cid, dist in zip(ids, distances):
            # Chroma 在 hnsw:space 为 cosine 时，返回的是余弦距离 (cosine distance)
            # cosine distance = 1 - cosine similarity
            # 因此 cosine similarity = 1 - cosine distance
            sim = max(0.0, min(1.0, 1.0 - float(dist)))
            hits.append((cid, round(sim, 4)))

        # 按相似度降序排列
        hits.sort(key=lambda x: x[1], reverse=True)
        return hits
