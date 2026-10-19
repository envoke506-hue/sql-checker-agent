"""
ChromaDB 向量存储仓储专项测试 (Chroma Vector Store Tests)
"""

import sys
import unittest
from pathlib import Path

# 解决 Windows 控制台编码问题
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 将项目根目录加入 sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.repositories.chroma_vector_store_repository import ChromaVectorStoreRepository
from app.repositories.numpy_vector_store_repository import NumpyVectorStoreRepository
from app.repositories.vector_store_repository import VectorStoreRepository


class TestChromaVectorStore(unittest.TestCase):
    """
    ChromaDB 向量库功能、持久化与标量元数据过滤测试
    """

    def setUp(self):
        self.settings = get_settings()
        self.test_dir = Path("data/indices/test_chroma")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.repo = ChromaVectorStoreRepository(
            persist_dir=str(self.test_dir),
            collection_name="test_collection"
        )

    def test_01_save_and_retrieve(self):
        """测试 1: 向量存储、持久化与余弦相似度检索"""
        print("\n--- [测试 1] Chroma 向量存储与检索 ---")
        chunk_ids = ["chunk_rule_1", "chunk_rule_2", "chunk_rule_3"]
        # 构造三组正交及相似向量 (10 维作为测试)
        vectors = [
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ]
        metadatas = [
            {"category": "naming", "rule_type": "field"},
            {"category": "naming", "rule_type": "table"},
            {"category": "ddl_rule", "rule_type": "foreign_key"}
        ]

        self.repo.save(chunk_ids, vectors, metadatas=metadatas)
        self.assertEqual(self.repo.count(), 3)
        self.assertFalse(self.repo.is_empty())
        self.assertTrue(self.repo.exists())

        # 检索向量，与 chunk_rule_1 最接近
        query_vec = [0.99, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        results = self.repo.search(query_vec, top_k=2)

        print(f"Top 结果: {results}")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "chunk_rule_1")
        self.assertGreater(results[0][1], 0.95, "相似度得分应接近 1.0")
        print("[PASS] ChromaDB 基础向量存储与相似度检索验证通过！")

    def test_02_metadata_filtering(self):
        """测试 2: 标量元数据前置过滤 (Metadata Filtering)"""
        print("\n--- [测试 2] Chroma 标量元数据前置过滤 ---")
        query_vec = [0.99, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # 仅检索 category 为 ddl_rule 的切块
        filtered_results = self.repo.search(
            query_vec,
            top_k=5,
            filter_metadata={"category": "ddl_rule"}
        )

        print(f"带过滤条件的召回结果: {filtered_results}")
        self.assertEqual(len(filtered_results), 1)
        self.assertEqual(filtered_results[0][0], "chunk_rule_3")
        print("[PASS] ChromaDB 标量元数据过滤 (Push-down Filtering) 验证通过！")

    def test_03_facade_and_engine_switching(self):
        """测试 3: VectorStoreRepository 门面与双引擎兼容"""
        print("\n--- [测试 3] VectorStoreRepository 门面与引擎机制 ---")
        # 默认引擎应为 chroma
        default_repo = VectorStoreRepository()
        self.assertEqual(default_repo.active_engine, "chroma")
        print(f"当前默认激活向量引擎: {default_repo.active_engine}")

        # 指定 numpy 引擎
        numpy_repo = VectorStoreRepository(engine_type="numpy")
        self.assertEqual(numpy_repo.active_engine, "numpy")
        print(f"动态切换向量引擎为: {numpy_repo.active_engine}")
    def test_04_port_dto_upsert_and_search(self):
        """测试 4: 验证中立 DTO (VectorRecord / VectorQuery / VectorSearchResult) 隔离契约"""
        print("\n--- [测试 4] 中立 DTO 端口契约与解包兼容 ---")
        from app.models.dto.vector_store import VectorRecord, VectorQuery, VectorSearchResult

        records = [
            VectorRecord(
                id="doc_audit_1",
                vector=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                metadata={"category": "audit", "author": "dba"}
            ),
            VectorRecord(
                id="doc_audit_2",
                vector=[0.0, 0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                metadata={"category": "audit", "author": "sec"}
            )
        ]
        self.repo.upsert(records)

        # 强类型查询对象
        query = VectorQuery(
            vector=[0.0, 0.95, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            top_k=2,
            filter_metadata={"category": "audit"}
        )
        results = self.repo.search_records(query)

        self.assertEqual(len(results), 2)
        top_hit = results[0]
        self.assertIsInstance(top_hit, VectorSearchResult)
        self.assertEqual(top_hit.id, "doc_audit_1")
        self.assertGreater(top_hit.score, 0.95)
        self.assertEqual(top_hit.metadata.get("author"), "dba")

        # 验证支持像元组一样解包: cid, sc = top_hit
        cid, sc = top_hit
        self.assertEqual(cid, "doc_audit_1")
        self.assertAlmostEqual(sc, top_hit.score)

        print(f"中立命中实体: id={top_hit.id}, score={top_hit.score}, metadata={top_hit.metadata}")
        print("[PASS] 领域中立 DTO 端口契约与防腐隔离验证通过！")


if __name__ == "__main__":
    unittest.main()
