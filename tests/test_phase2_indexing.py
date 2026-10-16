"""
第二阶段知识库切块与离线索引 Pipeline 自动化测试套件
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

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings
from app.core.http_client import close_async_client
from app.services.chunking_service import ChunkingService
from app.services.knowledge_service import KnowledgeService
from app.repositories.vector_store_repository import VectorStoreRepository
from app.repositories.bm25_index_repository import BM25IndexRepository
from app.repositories.ollama_embedding_repository import OllamaEmbeddingRepository


class TestPhase2Indexing(unittest.IsolatedAsyncioTestCase):
    """
    第二阶段知识库切块、向量化与 BM25 索引单元与集成测试
    """

    async def asyncSetUp(self):
        self.settings = get_settings()
        self.client = TestClient(app)

    async def asyncTearDown(self):
        await close_async_client()

    def test_01_chunking_atomic_protection(self):
        """测试 1: 验证 AST 结构化切块质量与语义原子保护"""
        print("\n--- [测试 1] 验证切块质量与原子保护 ---")
        chunking_svc = ChunkingService()
        chunks = chunking_svc.split_specification()

        print(f"切块总数: {len(chunks)}")
        self.assertEqual(len(chunks), 6, "知识库应精确切分为 6 大核心语义块")

        chunk_dict = {c.chunk_id: c for c in chunks}

        # 1. 验证命名规范原子块是否包含反例
        naming_chunk = chunk_dict.get("chunk_naming_rules")
        self.assertIsNotNone(naming_chunk)
        self.assertIn("反例", naming_chunk.display_text)
        self.assertIn("db_order.order.order_id", naming_chunk.display_text)
        self.assertIn("【规范层级】", naming_chunk.embedding_text)
        print("[PASS] 命名规范原子块反例绑定验证通过！")

        # 2. 验证建表模板原子块是否完整保护代码
        template_chunk = chunk_dict.get("chunk_table_template")
        self.assertIsNotNone(template_chunk)
        self.assertIn("CREATE TABLE db_table", template_chunk.display_text)
        self.assertIn("modify_time DATETIME", template_chunk.display_text)
        self.assertIn("ENGINE=InnoDB", template_chunk.display_text)
        print("[PASS] 建表模板原子块 SQL 完整性验证通过！")

        # 3. 验证建库规范是否包含禁止外键
        db_rule_chunk = chunk_dict.get("chunk_database_rules")
        self.assertIsNotNone(db_rule_chunk)
        self.assertIn("表内禁止外键设计", db_rule_chunk.display_text)
        self.assertIn("double 类型不要用", db_rule_chunk.display_text)
        print("[PASS] 建库规范原子块核心禁令验证通过！")

    async def test_02_indexing_pipeline_build_and_persist(self):
        """测试 2: 执行全量索引构建 Pipeline，验证持久化文件生成"""
        print("\n--- [测试 2] 运行全量索引构建 Pipeline 并验证持久化 ---")
        knowledge_svc = KnowledgeService()

        # 强制全量重跑 (调用本地 Ollama 计算向量)
        status_info = await knowledge_svc.initialize_or_load(force=True)

        self.assertTrue(status_info.is_indexed)
        self.assertEqual(status_info.chunk_count, 6)
        self.assertEqual(status_info.dimension, 2560)
        self.assertTrue(bool(status_info.doc_hash))

        # 验证磁盘持久化文件是否存在
        storage_dir = Path(self.settings.storage_dir)
        dense_file = storage_dir / "dense_vectors.npy"
        bm25_file = storage_dir / "bm25_model.pkl"
        store_file = storage_dir / "chunks_store.json"
        meta_file = storage_dir / "index_meta.json"

        self.assertTrue(dense_file.exists(), f"稠密向量文件缺失: {dense_file}")
        self.assertTrue(bm25_file.exists(), f"BM25 索引文件缺失: {bm25_file}")
        self.assertTrue(store_file.exists(), f"切块正文文件缺失: {store_file}")
        self.assertTrue(meta_file.exists(), f"索引元信息文件缺失: {meta_file}")

        print(f"[PASS] 索引构建与持久化验证通过！存储路径: {storage_dir}")

    async def test_03_dense_vector_search(self):
        """测试 3: 验证稠密向量余弦相似度检索语义召回能力"""
        print("\n--- [测试 3] 验证稠密向量余弦相似度检索能力 ---")
        vector_repo = VectorStoreRepository()
        self.assertTrue(vector_repo.load(), "加载向量索引失败")

        ollama_repo = OllamaEmbeddingRepository()

        # 提问 1: 关于外键禁令 (自然语言提问)
        query_text = "数据库里能不能建外键约束？"
        query_vec = await ollama_repo.get_embedding(query_text)
        top_hits = vector_repo.search(query_vec, top_k=3)

        print(f"提问: '{query_text}' 召回结果:")
        for cid, sc in top_hits:
            print(f" - {cid}: 相似度={sc}")

        # Top-1 应该命中建库规范块 (chunk_database_rules)
        self.assertEqual(top_hits[0][0], "chunk_database_rules", "外键问题应精准召回建库规范块")
        self.assertGreater(top_hits[0][1], 0.5, "相似度得分应显著大于 0.5")
        print("[PASS] 稠密向量语义检索精准命中！")

    def test_04_bm25_sparse_search(self):
        """测试 4: 验证 BM25 稀疏索引对专有名词与数据类型的精确检索"""
        print("\n--- [测试 4] 验证 BM25 稀疏精确检索能力 ---")
        bm25_repo = BM25IndexRepository()
        self.assertTrue(bm25_repo.load(), "加载 BM25 索引失败")

        # 检索精确专有类型: decimal(20, 6)
        query = "decimal(20, 6)"
        hits = bm25_repo.search(query, top_k=3)
        print(f"精确检索: '{query}' 命中列表: {hits}")

        self.assertTrue(len(hits) > 0)
        # 应命中命名规范或建库规范块
        hit_ids = [h[0] for h in hits]
        self.assertIn("chunk_naming_rules", hit_ids)

        # 检索代码函数: IdWorker
        code_hits = bm25_repo.search("IdWorker.getId", top_k=2)
        print(f"代码函数检索: 'IdWorker.getId' 命中: {code_hits}")
        self.assertEqual(code_hits[0][0], "chunk_framework_mybatis")
        print("[PASS] BM25 专有名词与函数精准检索验证通过！")

    async def test_05_cache_instant_reload(self):
        """测试 5: 验证内容哈希一致时秒级直接从磁盘加载"""
        print("\n--- [测试 5] 验证文件哈希未变时的秒级本地缓存加载 ---")
        knowledge_svc = KnowledgeService()

        # force=False，此时源文件没变，应直接走磁盘 load()，耗时极短
        status_info = await knowledge_svc.initialize_or_load(force=False)
        self.assertTrue(status_info.is_indexed)
        self.assertEqual(status_info.chunk_count, 6)
        print("[PASS] 增量缓存秒级命中恢复通过！")

    def test_06_controller_endpoints(self):
        """测试 6: 验证知识库管理 RESTful 接口"""
        print("\n--- [测试 6] 验证知识库管理 HTTP 端点 ---")
        # 1. GET /api/v1/knowledge/indices/status
        status_resp = self.client.get("/api/v1/knowledge/indices/status")
        self.assertEqual(status_resp.status_code, 200)
        data = status_resp.json()
        self.assertEqual(data["code"], 20000)
        self.assertTrue(data["data"]["is_indexed"])
        self.assertEqual(data["data"]["chunk_count"], 6)
        print(f"状态接口响应成功: 切块数={data['data']['chunk_count']}")

        # 2. POST /api/v1/knowledge/indices (触发增量检查)
        reindex_resp = self.client.post("/api/v1/knowledge/indices", json={"force": False})
        self.assertEqual(reindex_resp.status_code, 200)
        reindex_data = reindex_resp.json()
        self.assertEqual(reindex_data["code"], 20000)
        print("[PASS] 知识库管理 RESTful 控制器接口测试通过！")


if __name__ == "__main__":
    unittest.main()
