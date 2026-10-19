"""
NumPy 纯内存稠密向量存储仓储 (NumPy Vector Store Repository)

【算法与框架知识点说明】
1. 向量相似度计算 (对应第 17 篇):
   - 文本检索优先使用余弦相似度 (Cosine Similarity)，只看多维空间的方向夹角，不受长短影响。
   - 使用 NumPy 进行矩阵批量向量化点积计算：
     $$\text{similarity} = \frac{Q \cdot M^T}{\|Q\|_2 \times \|M\|_2}$$
     利用 NumPy 底层 BLAS C 语言加速，毫秒内完成多维向量比对。
2. 索引持久化与零成本恢复 (对应第 16 篇):
   - 本仓储将向量矩阵保存为 `.npy` 二进制文件，元数据保存为 `.json`，重启时实现 0 毫秒冷启动加载！
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from app.core.config import get_settings
from app.models.dto.vector_store import VectorQuery, VectorRecord, VectorSearchResult
from app.repositories.base_vector_store import BaseVectorStoreRepository


class NumpyVectorStoreRepository(BaseVectorStoreRepository):
    """
    负责基于 NumPy 矩阵的稠密向量检索、磁盘持久化与元数据映射
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.settings = get_settings()
        self.storage_dir = Path(storage_dir or self.settings.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.vector_file = self.storage_dir / "dense_vectors.npy"
        self.id_map_file = self.storage_dir / "vector_ids.json"

        # 内存数据结构
        self.chunk_ids: List[str] = []
        self.vector_matrix: Optional[np.ndarray] = None  # 形状为 (N, Dimension)

    def is_empty(self) -> bool:
        """检查当前内存中是否已加载向量索引"""
        return self.vector_matrix is None or len(self.chunk_ids) == 0

    def count(self) -> int:
        """获取当前加载的切块总数"""
        return len(self.chunk_ids)

    def upsert(self, records: List[VectorRecord]) -> None:
        """
        批量存入中立的 VectorRecord 记录项
        """
        if not records:
            return

        self.chunk_ids = [r.id for r in records]
        self.vector_matrix = np.array([r.vector for r in records], dtype=np.float32)

        # 1. 保存向量矩阵 (NumPy 高效二进制格式)
        np.save(self.vector_file, self.vector_matrix)

        # 2. 保存 ID 映射
        with open(self.id_map_file, "w", encoding="utf-8") as f:
            json.dump(self.chunk_ids, f, ensure_ascii=False, indent=2)

    def load(self) -> bool:
        """
        从磁盘文件加载向量索引与 ID 映射至内存

        :return: True 表示加载成功，False 表示文件不存在
        """
        if not self.vector_file.exists() or not self.id_map_file.exists():
            return False

        try:
            self.vector_matrix = np.load(self.vector_file)
            with open(self.id_map_file, "r", encoding="utf-8") as f:
                self.chunk_ids = json.load(f)
            return True
        except Exception:
            return False

    def exists(self) -> bool:
        """检查磁盘持久化文件是否存在"""
        return self.vector_file.exists() and self.id_map_file.exists()

    def search_records(self, query: VectorQuery) -> List[VectorSearchResult]:
        """
        计算输入向量与库内所有向量的余弦相似度，并返回中立的 VectorSearchResult 列表
        """
        if self.is_empty() and self.exists():
            self.load()

        if self.is_empty():
            return []

        q = np.array(query.vector, dtype=np.float32)

        # 计算模长 (L2 Norm)
        q_norm = np.linalg.norm(q)
        m_norm = np.linalg.norm(self.vector_matrix, axis=1)

        # 避免分母除以 0
        denominator = (m_norm * q_norm)
        denominator[denominator == 0] = 1e-10

        # 点积与余弦相似度计算 (利用 NumPy 矩阵乘法快速得出所有候选分数)
        similarities = np.dot(self.vector_matrix, q) / denominator

        # 获取得分最高的 Top-K 索引
        actual_k = min(query.top_k, len(self.chunk_ids))
        top_indices = np.argsort(similarities)[::-1][:actual_k]

        results: List[VectorSearchResult] = []
        for idx in top_indices:
            score = float(similarities[idx])
            chunk_id = self.chunk_ids[idx]
            results.append(
                VectorSearchResult(
                    id=chunk_id,
                    score=round(score, 4),
                    metadata={}
                )
            )

        return results
