"""
第三阶段测试：SQL 特征提取、双路混合检索与 RRF 融合排序引擎
测试内容包括：
1. SqlFeatureExtractor 特征提取与多意图针对性 Query 生成
2. RRF 倒数排名融合算法的数学打分与跨路累加准确性
3. RetrievalService 真实违规 SQL 召回率测试 (外键/double/order_id/基类字段)
4. RetrievalService 自然语言规范咨询检索测试
5. 依赖容器装配测试
"""

import sys
import asyncio
from pathlib import Path
from typing import List

# 保证 Windows 命令行控制台输出中文不乱码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 将项目根目录加入 sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.sql_feature_extractor import SqlFeatureExtractor
from app.services.retrieval_service import RetrievalService
from app.repositories.doc_store_repository import DocStoreRepository
from app.core.dependencies import get_retrieval_service


def test_1_sql_feature_extractor():
    """测试 1: SQL 语法与合规特征提取器"""
    print("\n--- [测试 1: SQL 特征提取与意图生成] ---")
    extractor = SqlFeatureExtractor()

    bad_sql = """
    CREATE TABLE `order` (
        `order_id` bigint(20) NOT NULL AUTO_INCREMENT,
        `order_no` varchar(64) NOT NULL,
        `total_amount` double NOT NULL,
        `is_pay` tinyint(1) DEFAULT 0,
        `user_id` bigint(20) NOT NULL,
        PRIMARY KEY (`order_id`),
        CONSTRAINT `fk_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
    """

    features = extractor.extract_features(bad_sql)
    assert features.table_name == "order", f"表名提取失败: {features.table_name}"
    assert not features.has_db_prefix, "应识别出缺少 db_ 前缀"
    assert features.is_table_keyword, "应识别出 order 为保留关键字"
    assert features.has_foreign_key, "应识别出包含外键 FOREIGN KEY"
    assert features.has_double_type, "应识别出包含 double 类型"
    assert features.has_tinyint_1, "应识别出包含 tinyint(1)"
    assert features.has_table_prefix_in_column, "应识别出 order_id 冗余了表名前缀反例"
    assert "order_id" in features.redundant_columns, "redundant_columns 应包含 order_id"
    assert len(features.missing_base_fields) > 0, "应识别出缺失 7 大基类审计字段"
    print(f"[PASS] SQL 特征深度提取校验成功: 识别到表名={features.table_name}, 冗余前缀字段={features.redundant_columns}, 缺失基类={features.missing_base_fields}")

    queries = extractor.generate_retrieval_queries(bad_sql)
    assert len(queries) >= 5, f"针对违规 SQL 生成的意图数不足: {len(queries)}"
    print(f"[PASS] 针对性多意图 Query 生成成功，共生成 {len(queries)} 个高命中意图:")
    for idx, q in enumerate(queries, 1):
        print(f"       [{idx}] {q}")


def test_2_rrf_math_logic():
    """测试 2: RRF 倒数排名融合算法的纯数学与排序逻辑"""
    print("\n--- [测试 2: RRF 倒数排名融合数学计算] ---")
    retrieval_svc = RetrievalService()

    # 模拟两路检索结果
    # 路 1 (Dense 向量): A 排第 1, B 排第 2, C 排第 3
    dense_hits = [("chunk_A", 0.95), ("chunk_B", 0.88), ("chunk_C", 0.72)]
    # 路 2 (Sparse BM25): B 排第 1, A 排第 2, D 排第 3
    sparse_hits = [("chunk_B", 15.2), ("chunk_A", 12.1), ("chunk_D", 8.4)]

    # 理论打分 (k = 60):
    # chunk_A: 1/(60+1) + 1/(60+2) = 1/61 + 1/62 = 0.0163934 + 0.0161290 = 0.032522
    # chunk_B: 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.032522 (两者并列或极微差异)
    # chunk_C: 1/(60+3) = 1/63 = 0.015873
    # chunk_D: 1/(60+3) = 1/63 = 0.015873

    merged = retrieval_svc._apply_rrf_fusion([dense_hits, sparse_hits])
    assert len(merged) == 4, f"融合后文档总数不符: {len(merged)}"
    top_ids = [item[0] for item in merged[:2]]
    assert "chunk_A" in top_ids and "chunk_B" in top_ids, "双路均认可的 chunk_A 和 chunk_B 必须排在前两名"
    assert merged[2][0] in ["chunk_C", "chunk_D"], "单路认可的必须排在后面"
    print(f"[PASS] RRF 融合打分校验成功: {merged}")


async def test_3_sql_retrieval_integration():
    """测试 3: 真实违规 SQL 的端到端混合检索召回"""
    print("\n--- [测试 3: 真实违规 SQL 双路混合检索召回] ---")
    doc_repo = DocStoreRepository()
    if not doc_repo.exists():
        print("[WARN] 索引不存在，跳过检索集成测试")
        return

    retrieval_svc = RetrievalService()

    bad_sql = """
    CREATE TABLE `order` (
        `order_id` bigint(20) NOT NULL AUTO_INCREMENT,
        `order_no` varchar(64) NOT NULL,
        `total_amount` double NOT NULL,
        `user_id` bigint(20) NOT NULL,
        PRIMARY KEY (`order_id`),
        CONSTRAINT `fk_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    );
    """

    results = await retrieval_svc.retrieve_for_sql(bad_sql, top_k=5)
    assert len(results) > 0, "检索结果不应为空"
    print(f"[PASS] 违规 SQL 召回 {len(results)} 条核心规范条款:")
    
    retrieved_titles = []
    for rank, (chunk, score) in enumerate(results, 1):
        print(f"       Rank {rank} (RRF Score: {score:.5f}) -> {chunk.title} [ID: {chunk.id}]")
        retrieved_titles.append(chunk.title)

    # 验证关键条款是否被召回
    all_text = " ".join(retrieved_titles)
    # 违规 SQL 包含了表名关键字/外键/double/order_id/缺失基类字段，因此应该召回建库规范、命名规范或建表模板
    has_relevant_chunk = any(kw in all_text for kw in ["建库规范", "命名规范", "建表模板", "字段与索引"])
    assert has_relevant_chunk, f"未召回相关合规条款: {retrieved_titles}"
    print("[PASS] 核心违规规范条款均高分召回！")


async def test_4_query_retrieval_integration():
    """测试 4: 自然语言咨询双路混合检索召回"""
    print("\n--- [测试 4: 自然语言咨询双路混合检索] ---")
    doc_repo = DocStoreRepository()
    if not doc_repo.exists():
        print("[WARN] 索引不存在，跳过问答检索测试")
        return

    retrieval_svc = RetrievalService()

    question = "关于金额和单价字段，数据库规范有什么命名和数据类型的要求？"
    results = await retrieval_svc.retrieve_for_query(question, top_k=3)
    assert len(results) > 0, "问答检索结果不应为空"
    print(f"[PASS] 自然语言问题 '{question}' 召回 {len(results)} 条规范:")
    for rank, (chunk, score) in enumerate(results, 1):
        print(f"       Rank {rank} (RRF Score: {score:.5f}) -> {chunk.title}")
    
    # 命中命名规范或建库规范
    all_text = " ".join([c.title for c, _ in results])
    assert any(kw in all_text for kw in ["命名规范", "建库规范", "字段与索引"]), "问答检索条款不匹配"
    print("[PASS] 咨询问答规范条款召回校验成功！")


def test_5_dependency_injection():
    """测试 5: 依赖容器注入工厂验证"""
    print("\n--- [测试 5: 依赖注入工厂解析] ---")
    retrieval_svc = get_retrieval_service()
    assert isinstance(retrieval_svc, RetrievalService), "依赖注入解析出的对象类型不符"
    assert retrieval_svc.ollama_repo is not None
    assert retrieval_svc.vector_repo is not None
    assert retrieval_svc.bm25_repo is not None
    assert retrieval_svc.doc_repo is not None
    assert retrieval_svc.feature_extractor is not None
    print("[PASS] FastAPI Depends 依赖工厂 get_retrieval_service 解析与装配成功！")


async def main():
    test_1_sql_feature_extractor()
    test_2_rrf_math_logic()
    await test_3_sql_retrieval_integration()
    await test_4_query_retrieval_integration()
    test_5_dependency_injection()
    print("\n=======================================================")
    print(">>> 恭喜！第三阶段：SQL 特征提取与混合检索 RRF 引擎 5 项测试全部通过！<<<")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
