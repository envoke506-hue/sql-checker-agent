r"""
双路混合检索与 RRF 融合排序引擎 (Retrieval Service)

【课程与算法知识点深度落地 (落地第 18 篇)】
1. 为什么必须采用混合检索 (Hybrid Search):
   - 稠密向量检索 (Dense Retrieval): 擅长理解长句、同义词与自然语言意图，但对精确关键字（如 `decimal(20, 6)`、`TINYINT(4)`、`db_`）不敏感。
   - 稀疏关键词检索 (Sparse BM25): 擅长精确统计罕见词频率，但不懂语义相近（如把“钱怎么存”与“金额”关联起来）。
   - 两路互补结合，是目前工业级 RAG 检索质量最高的主流打法。
2. RRF (Reciprocal Rank Fusion, 倒数排名融合算法):
   - BM25 分数是 0~20+ 的无界统计值，余弦相似度是 0~1 的夹角余弦，两者尺度完全不同，无法直接相加。
   - RRF 算法抛弃具体分数值，只看相对排名 (Rank)：
     $$RRF\_Score(d) = \sum_{m \in \{dense, sparse\}} \frac{1}{k + rank_m(d)}$$
   - 业内经验平滑常数通常取 $k = 60$。
   - 核心优势：不需要费心调两路权重，天然免疫尺度差异，多路同时认可的文档会自动累加高分排到第一！
3. 两阶段 K 与黄金条款收紧 (Two-stage K Retrieval):
   - 初筛阶段多意图并发召回，放宽候选集以保证召回率 (Recall)；
   - 精排阶段通过 RRF 累加打分排序，收紧至 Top-3 ~ Top-5 黄金规范送入后续大模型，防止无关噪声稀释模型注意力。
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from app.models.entity.chunk import Chunk
from app.repositories.bm25_index_repository import BM25IndexRepository
from app.repositories.doc_store_repository import DocStoreRepository
from app.repositories.ollama_embedding_repository import OllamaEmbeddingRepository
from app.repositories.vector_store_repository import VectorStoreRepository
from app.services.sql_feature_extractor import SqlFeatureExtractor


class RetrievalService:
    """
    负责执行 SQL 意图检索与自然语言咨询的双路混合检索与 RRF 融合排序
    """

    # RRF 标准平滑常数 (对应第 18 篇推荐配置)
    RRF_K_CONSTANT: int = 60

    def __init__(
        self,
        ollama_repo: Optional[OllamaEmbeddingRepository] = None,
        vector_repo: Optional[VectorStoreRepository] = None,
        bm25_repo: Optional[BM25IndexRepository] = None,
        doc_repo: Optional[DocStoreRepository] = None,
        feature_extractor: Optional[SqlFeatureExtractor] = None,
    ):
        self.ollama_repo = ollama_repo or OllamaEmbeddingRepository()
        self.vector_repo = vector_repo or VectorStoreRepository()
        self.bm25_repo = bm25_repo or BM25IndexRepository()
        self.doc_repo = doc_repo or DocStoreRepository()
        self.feature_extractor = feature_extractor or SqlFeatureExtractor()

    def _apply_rrf_fusion(
        self,
        ranked_lists: List[List[Tuple[str, float]]]
    ) -> List[Tuple[str, float]]:
        """
        核心算法：执行多路倒数排名融合 (RRF)
        :param ranked_lists: 多个已经按各自相关性从高到低排好序的 [(chunk_id, raw_score), ...] 列表
        :return: 跨路累加后全局重新降序排列的 [(chunk_id, rrf_score), ...]
        """
        rrf_scores: Dict[str, float] = defaultdict(float)

        for single_list in ranked_lists:
            # 遍历该路中的每个排名 (rank 从 1 开始计数)
            for rank, (chunk_id, _) in enumerate(single_list, start=1):
                # RRF 打分公式: 1 / (k + rank)
                contribution = 1.0 / (self.RRF_K_CONSTANT + rank)
                rrf_scores[chunk_id] += contribution

        # 按累加总分从大到小排序
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return [(cid, round(score, 6)) for cid, score in sorted_results]

    async def _search_single_query(
        self,
        query: str,
        dense_top_k: int = 5,
        sparse_top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        对单个意图 Query 执行双路检索并 RRF 融合
        """
        # 1. 稠密向量路 (Dense)
        dense_hits: List[Tuple[str, float]] = []
        try:
            query_vector = await self.ollama_repo.get_embedding(query)
            dense_hits = self.vector_repo.search(query_vector, top_k=dense_top_k)
        except Exception as e:
            print(f"[WARN] [混合检索] 稠密向量检索告警: {e}")

        # 2. 稀疏关键词路 (Sparse BM25)
        sparse_hits = self.bm25_repo.search(query, top_k=sparse_top_k)

        # 3. 双路 RRF 融合
        merged_rrf = self._apply_rrf_fusion([dense_hits, sparse_hits])
        return merged_rrf

    async def retrieve_for_sql(
        self,
        sql_text: str,
        top_k: int = 5
    ) -> List[Tuple[Chunk, float]]:
        """
        针对输入的 DDL SQL 语句执行高靶向性规范检索 (SQL 专用入口)

        工作流程:
        1. 由 SqlFeatureExtractor 提取违规与特征点，生成多意图 Queries
        2. 对每个意图 Query 执行双路混合检索
        3. 全局多意图 RRF 叠加汇总排序
        4. 收紧截断至 Top-K 并从 DocStore 回拉完整规范 Chunk 实体

        :param sql_text: 待审查的 SQL 语句
        :param top_k: 最终保留送入 LLM 审查的黄金条款数量
        :return: [(Chunk实体, RRF综合得分), ...] 按相关性降序排列
        """
        # 步骤 1: 提取特征并生成多意图 Queries
        queries = self.feature_extractor.generate_retrieval_queries(sql_text)
        print(f"[INFO] [SQL特征提取] 识别出 {len(queries)} 个合规审查意图 Queries:")
        for idx, q in enumerate(queries, 1):
            print(f"   [{idx}] {q}")

        # 步骤 2 & 3: 并行检索各 Query 并执行跨意图全局 RRF 累加
        all_query_rankings: List[List[Tuple[str, float]]] = []
        for q in queries:
            single_rrf_hits = await self._search_single_query(q, dense_top_k=5, sparse_top_k=5)
            all_query_rankings.append(single_rrf_hits)

        # 全局总排名融合
        global_ranked = self._apply_rrf_fusion(all_query_rankings)

        # 步骤 4: 截取 Top-K 并从 DocStore 回拉完整 Chunk 实体
        final_results: List[Tuple[Chunk, float]] = []
        for chunk_id, score in global_ranked[:top_k]:
            chunk_entity = self.doc_repo.get_by_id(chunk_id)
            if chunk_entity:
                final_results.append((chunk_entity, score))

        return final_results

    async def retrieve_for_query(
        self,
        question: str,
        top_k: int = 5
    ) -> List[Tuple[Chunk, float]]:
        """
        针对用户的自然语言提问执行双路混合检索 (规范问答入口)

        :param question: 用户咨询问题 (如 '金额字段必须使用什么类型？')
        :param top_k: 期望返回的规范条款数
        :return: [(Chunk实体, RRF综合得分), ...] 按相关性降序排列
        """
        clean_question = question.strip()
        merged_rrf = await self._search_single_query(clean_question, dense_top_k=top_k, sparse_top_k=top_k)

        final_results: List[Tuple[Chunk, float]] = []
        for chunk_id, score in merged_rrf[:top_k]:
            chunk_entity = self.doc_repo.get_by_id(chunk_id)
            if chunk_entity:
                final_results.append((chunk_entity, score))

        return final_results
