"""
稀疏 BM25 关键词检索仓储 (BM25 Index Repository)

【算法与框架知识点说明】
1. BM25 算法 (对应第 18 篇混合检索):
   - 稠密向量检索（Embedding）虽然懂近义词，但对“精确字符串、特定字段名、错误码、特定类型（如 decimal(20, 6)）”非常迟钝。
   - BM25 依据 TF-IDF 原理统计词频与反文档频率，对罕见的专业缩写与专有名词给予极大权重。
2. 领域分词器 (Tokenizer):
   - 中文和代码混排如果只按空格切词，中文会被当成整句；如果盲目按字切，`decimal` 会被拆成碎字符。
   - 本分词器使用复合正则：英文单词、SQL 关键字、带下划线的前后缀（如 `db_`, `order_id`）保持完整，中文按 1~2 字滑动分词，兼顾中英双语检索精度。
"""

import pickle
import re
from pathlib import Path
from typing import List, Optional, Tuple
from rank_bm25 import BM25Okapi

from app.core.config import get_settings


class BM25IndexRepository:
    """
    负责基于 BM25 算法的关键词倒排索引构建、持久化与稀疏检索
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.settings = get_settings()
        self.storage_dir = Path(storage_dir or self.settings.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.model_file = self.storage_dir / "bm25_model.pkl"
        self.meta_file = self.storage_dir / "bm25_meta.json"

        # 内存模型与映射
        self.bm25: Optional[BM25Okapi] = None
        self.chunk_ids: List[str] = []

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """
        专为数据库规范定制的中英双语与 SQL 混合分词器
        - 保留带下划线标识符：lower_snake_case, order_price, db_
        - 保留括号数据类型：decimal(20, 6), tinyint(4)
        - 中文文本按单字与双字切分
        """
        clean_text = text.lower()
        tokens: List[str] = []

        # 1. 正则匹配英文术语、数据类型及带下划线标识符
        pattern = re.compile(r"[a-z0-9_]+(?:\([0-9,\s]+\))?|[\u4e00-\u9fa5]")
        matches = pattern.findall(clean_text)

        for match in matches:
            tokens.append(match)

        # 2. 为中文文本补充 2-gram 双字词 (提升如“单价”、“外键”、“雪花”匹配率)
        chinese_chars = [ch for ch in clean_text if '\u4e00' <= ch <= '\u9fa5']
        for i in range(len(chinese_chars) - 1):
            tokens.append(chinese_chars[i] + chinese_chars[i + 1])

        return tokens

    def is_empty(self) -> bool:
        """检查索引是否未构建"""
        return self.bm25 is None or len(self.chunk_ids) == 0

    def build_and_save(self, chunk_ids: List[str], corpus_texts: List[str]) -> None:
        """
        根据切块语料训练 BM25 模型并持久化到磁盘

        :param chunk_ids: 切块 ID 列表
        :param corpus_texts: 各切块包含的文本与关键词集合
        """
        if len(chunk_ids) != len(corpus_texts):
            raise ValueError("chunk_ids 数量必须与语料文本数量严格一致")

        self.chunk_ids = chunk_ids
        tokenized_corpus = [self.tokenize(doc) for doc in corpus_texts]

        # 训练 BM25Okapi 模型
        self.bm25 = BM25Okapi(tokenized_corpus)

        # 序列化持久化到磁盘
        with open(self.model_file, "wb") as f:
            pickle.dump({
                "bm25": self.bm25,
                "chunk_ids": self.chunk_ids
            }, f)

    def load(self) -> bool:
        """
        从磁盘文件加载 BM25 索引模型

        :return: True 表示加载成功，False 表示文件不存在
        """
        if not self.model_file.exists():
            return False

        try:
            with open(self.model_file, "rb") as f:
                data = pickle.load(f)
                self.bm25 = data["bm25"]
                self.chunk_ids = data["chunk_ids"]
            return True
        except Exception:
            return False

    def exists(self) -> bool:
        """检查磁盘模型文件是否存在"""
        return self.model_file.exists()

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        基于 BM25 词频统计计算相关性打分并返回 Top-K 结果

        :param query: 用户输入的问题或关键词
        :param top_k: 期望召回的数量
        :return: [(chunk_id, bm25_score), ...] 按得分降序排列
        """
        if self.is_empty() and self.exists():
            self.load()

        if self.is_empty():
            return []

        tokenized_query = self.tokenize(query)
        if not tokenized_query:
            return []

        # 计算所有文档的得分
        scores = self.bm25.get_scores(tokenized_query)

        # 按得分从大到小排序
        scored_items = list(zip(self.chunk_ids, scores))
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # 过滤掉得分为 0 的无关块
        valid_items = [(cid, round(float(sc), 4)) for cid, sc in scored_items if sc > 0]
        return valid_items[:top_k]
