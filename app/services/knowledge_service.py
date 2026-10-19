"""
知识库构建与索引生命周期编排服务 (Knowledge Service)

【课程与企业级知识点深度落地】
1. 增量更新与哈希校验机制 (对应第 16 篇第五节):
   - 计算 Embedding 又贵又慢，如果文档未发生改动，严禁每次重启或查询都重跑索引。
   - 采用 SHA-256 内容哈希校验：只要源文件未动，服务启动直接走毫秒级磁盘反序列化；
     一旦检测到文件被编辑改动，自动触发全量增量重建。
2. 双路多粒度索引协同构建 (Multi-Representation Indexing, 对应第 16.1 篇形态 C 与第 18 篇):
   - 同时产出【稠密向量索引】（专攻语义概念匹配）与【稀疏 BM25 索引】（专攻专有名词精准命中）。
3. 纯异步 Pipeline:
   - 充分利用异步 I/O 调用本地 Ollama 计算向量。
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings
from app.models.dto.knowledge import ChunkSummary, IndexStatusResponseData
from app.models.entity.chunk import Chunk
from app.repositories.bm25_index_repository import BM25IndexRepository
from app.repositories.doc_store_repository import DocStoreRepository
from app.repositories.ollama_embedding_repository import OllamaEmbeddingRepository
from app.repositories.vector_store_repository import VectorStoreRepository
from app.services.chunking_service import ChunkingService


class KnowledgeService:
    """
    负责规范文档解析、结构化切块、双路索引构建及状态管理的编排服务
    """

    def __init__(
        self,
        chunking_service: Optional[ChunkingService] = None,
        ollama_repo: Optional[OllamaEmbeddingRepository] = None,
        vector_repo: Optional[VectorStoreRepository] = None,
        bm25_repo: Optional[BM25IndexRepository] = None,
        doc_repo: Optional[DocStoreRepository] = None
    ):
        self.settings = get_settings()
        self.chunking_svc = chunking_service or ChunkingService()
        self.ollama_repo = ollama_repo or OllamaEmbeddingRepository()
        self.vector_repo = vector_repo or VectorStoreRepository()
        self.bm25_repo = bm25_repo or BM25IndexRepository()
        self.doc_repo = doc_repo or DocStoreRepository()

    async def initialize_or_load(self, force: bool = False) -> IndexStatusResponseData:
        """
        初始化知识库：检查缓存是否存在且哈希一致；若不一致或 force=True，则执行全量重建构建流水线

        :param force: 是否强制重新计算向量与索引
        :return: 索引构建状态详情
        """
        _, current_hash = self.chunking_svc.read_document_and_hash()

        # 1. 尝试从本地持久化文件恢复
        if not force:
            doc_loaded = self.doc_repo.load()
            vector_loaded = self.vector_repo.load()
            bm25_loaded = self.bm25_repo.load()

            if doc_loaded and vector_loaded and bm25_loaded:
                cached_meta = self.doc_repo.get_metadata()
                if cached_meta.get("doc_hash") == current_hash:
                    # 内容哈希一致，直接复用已有缓存
                    return self.get_index_status()

        # 2. 缓存失效或强制刷新，执行全量索引构建 Pipeline
        return await self._build_indices_pipeline(current_hash)

    async def _build_indices_pipeline(self, doc_hash: str) -> IndexStatusResponseData:
        """
        执行完整的知识库索引构建流水线
        步骤: 结构化切块 ➔ 计算 Embedding ➔ 训练 BM25 ➔ 磁盘持久化
        """
        print(f"🔄 开始执行知识库全量索引构建流水线...")

        # 步骤 1: AST 结构化切分
        chunks: List[Chunk] = self.chunking_svc.split_specification()
        chunk_ids = [c.chunk_id for c in chunks]
        embedding_texts = [c.embedding_text for c in chunks]

        # 步骤 2: 调用本地 Ollama 异步批量计算 2560 维向量
        print(f"🤖 正在调用 Ollama ({self.settings.ollama_embedding_model}) 计算 {len(chunks)} 个切块向量...")
        vectors = await self.ollama_repo.get_embeddings_batch(embedding_texts)

        # 步骤 3: 存入稠密向量仓储并持久化 (支持标量元数据存储与过滤)
        metadatas = [c.metadata.model_dump() for c in chunks]
        self.vector_repo.save(chunk_ids, vectors, metadatas=metadatas)

        # 步骤 4: 构造 BM25 关键词语料并训练持久化
        # 语料由 display_text 加上额外提取的 keywords 组成，强化专业词汇权重
        corpus_texts = [
            f"{c.display_text} {' '.join(c.keywords)}" for c in chunks
        ]
        self.bm25_repo.build_and_save(chunk_ids, corpus_texts)

        # 步骤 5: 将 Chunk 实体全量存入 DocStore 并保存元数据
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        categories = list(set(c.metadata.category for c in chunks))

        meta_info = {
            "doc_path": str(self.chunking_svc.spec_doc_path),
            "doc_hash": doc_hash,
            "chunk_count": len(chunks),
            "dimension": len(vectors[0]) if vectors else 2560,
            "categories": categories,
            "last_updated": now_str
        }
        self.doc_repo.save(chunks, meta_info)
        print(f"✅ 知识库索引构建完成！共生成 {len(chunks)} 个高质量切块，索引已持久化到磁盘。")

        return self.get_index_status()

    def _ensure_loaded(self) -> None:
        """
        若当前内存中索引为空，则尝试自动从本地磁盘持久化文件中快速加载恢复
        """
        if self.doc_repo.is_empty():
            self.doc_repo.load()
        if self.vector_repo.is_empty():
            self.vector_repo.load()
        if self.bm25_repo.is_empty():
            self.bm25_repo.load()

    def get_index_status(self) -> IndexStatusResponseData:
        """
        获取当前知识库的索引状态与元信息 (支持磁盘自动探测)
        """
        self._ensure_loaded()
        is_indexed = not self.vector_repo.is_empty() and not self.bm25_repo.is_empty() and not self.doc_repo.is_empty()
        chunks = self.doc_repo.get_all()
        meta = self.doc_repo.get_metadata()

        summaries = [
            ChunkSummary(
                chunk_id=c.chunk_id,
                heading_path=c.metadata.heading_path,
                category=c.metadata.category,
                char_count=len(c.display_text)
            )
            for c in chunks
        ]

        return IndexStatusResponseData(
            is_indexed=is_indexed,
            chunk_count=len(chunks),
            doc_path=meta.get("doc_path", str(self.chunking_svc.spec_doc_path)),
            doc_hash=meta.get("doc_hash", ""),
            dimension=meta.get("dimension", 2560),
            categories=meta.get("categories", []),
            chunks=summaries,
            last_updated=meta.get("last_updated")
        )
