"""
FastAPI 依赖注入与服务装配工厂 (Dependency Injection / IoC Container)
"""

from functools import lru_cache
from fastapi import Depends

from app.repositories.ollama_embedding_repository import OllamaEmbeddingRepository
from app.repositories.relay_llm_repository import RelayLlmRepository
from app.repositories.vector_store_repository import VectorStoreRepository
from app.repositories.bm25_index_repository import BM25IndexRepository
from app.repositories.doc_store_repository import DocStoreRepository
from app.services.chunking_service import ChunkingService
from app.services.health_service import HealthService
from app.services.knowledge_service import KnowledgeService
from app.services.sql_feature_extractor import SqlFeatureExtractor
from app.services.retrieval_service import RetrievalService
from app.services.context_orchestrator import ContextOrchestrator
from app.services.double_check_verifier import DoubleCheckVerifier
from app.services.sql_audit_service import SqlAuditService
from app.services.spec_query_service import SpecQueryService
from app.services.sql_rule.engine import SqlRuleEngine


# ---------------- 1. 仓储层 Repository 与工具组件依赖提供者 (单例) ----------------

@lru_cache
def get_ollama_repository() -> OllamaEmbeddingRepository:
    """提供本地 Ollama 向量仓储单例"""
    return OllamaEmbeddingRepository()


@lru_cache
def get_relay_llm_repository() -> RelayLlmRepository:
    """提供云端中转站大模型仓储单例"""
    return RelayLlmRepository()


@lru_cache
def get_vector_store_repository() -> VectorStoreRepository:
    """提供稠密向量仓储单例"""
    return VectorStoreRepository()


@lru_cache
def get_bm25_index_repository() -> BM25IndexRepository:
    """提供 BM25 稀疏检索仓储单例"""
    return BM25IndexRepository()


@lru_cache
def get_doc_store_repository() -> DocStoreRepository:
    """提供切块正文与元数据仓储单例"""
    return DocStoreRepository()


@lru_cache
def get_chunking_service() -> ChunkingService:
    """提供切块服务单例"""
    return ChunkingService()


@lru_cache
def get_sql_feature_extractor() -> SqlFeatureExtractor:
    """提供 SQL 特征提取与意图分解器单例"""
    return SqlFeatureExtractor()


@lru_cache
def get_context_orchestrator() -> ContextOrchestrator:
    """提供 Lost-in-the-Middle 上下文编排器单例"""
    return ContextOrchestrator()


@lru_cache
def get_double_check_verifier() -> DoubleCheckVerifier:
    """提供防幻觉规则二次断言核验器单例"""
    return DoubleCheckVerifier()


# ---------------- 2. 业务层 Service 依赖提供者 ----------------

def _resolve(dep, default_factory):
    """
    辅助解析器：兼容 FastAPI 容器路由注入与非容器直接调用 (如离线任务、单元测试)
    若传入的是 FastAPI 的 Depends 描述符，则自动回退调用单例工厂获取实例
    """
    from fastapi.params import Depends as DependsClass
    return default_factory() if isinstance(dep, DependsClass) else dep


def get_health_service(
    ollama_repo: OllamaEmbeddingRepository = Depends(get_ollama_repository),
    relay_repo: RelayLlmRepository = Depends(get_relay_llm_repository),
) -> HealthService:
    """组装系统健康体检服务"""
    return HealthService(
        ollama_repo=_resolve(ollama_repo, get_ollama_repository),
        relay_repo=_resolve(relay_repo, get_relay_llm_repository),
    )


def get_knowledge_service(
    chunking_svc: ChunkingService = Depends(get_chunking_service),
    ollama_repo: OllamaEmbeddingRepository = Depends(get_ollama_repository),
    vector_repo: VectorStoreRepository = Depends(get_vector_store_repository),
    bm25_repo: BM25IndexRepository = Depends(get_bm25_index_repository),
    doc_repo: DocStoreRepository = Depends(get_doc_store_repository),
) -> KnowledgeService:
    """组装知识库索引构建与管理服务"""
    return KnowledgeService(
        chunking_service=_resolve(chunking_svc, get_chunking_service),
        ollama_repo=_resolve(ollama_repo, get_ollama_repository),
        vector_repo=_resolve(vector_repo, get_vector_store_repository),
        bm25_repo=_resolve(bm25_repo, get_bm25_index_repository),
        doc_repo=_resolve(doc_repo, get_doc_store_repository),
    )


def get_retrieval_service(
    ollama_repo: OllamaEmbeddingRepository = Depends(get_ollama_repository),
    vector_repo: VectorStoreRepository = Depends(get_vector_store_repository),
    bm25_repo: BM25IndexRepository = Depends(get_bm25_index_repository),
    doc_repo: DocStoreRepository = Depends(get_doc_store_repository),
    feature_extractor: SqlFeatureExtractor = Depends(get_sql_feature_extractor),
) -> RetrievalService:
    """组装双路混合检索与 RRF 融合排序引擎服务"""
    return RetrievalService(
        ollama_repo=_resolve(ollama_repo, get_ollama_repository),
        vector_repo=_resolve(vector_repo, get_vector_store_repository),
        bm25_repo=_resolve(bm25_repo, get_bm25_index_repository),
        doc_repo=_resolve(doc_repo, get_doc_store_repository),
        feature_extractor=_resolve(feature_extractor, get_sql_feature_extractor),
    )


@lru_cache
def get_sql_rule_engine() -> SqlRuleEngine:
    """提供 SQL 静态规则校验引擎单例"""
    return SqlRuleEngine()


def get_sql_audit_service(
    ollama_repo: OllamaEmbeddingRepository = Depends(get_ollama_repository),
    relay_repo: RelayLlmRepository = Depends(get_relay_llm_repository),
    retrieval_svc: RetrievalService = Depends(get_retrieval_service),
    orchestrator: ContextOrchestrator = Depends(get_context_orchestrator),
    double_checker: DoubleCheckVerifier = Depends(get_double_check_verifier),
    rule_engine: SqlRuleEngine = Depends(get_sql_rule_engine),
) -> SqlAuditService:
    """组装 SQL 规范审查核心服务"""
    return SqlAuditService(
        ollama_repo=_resolve(ollama_repo, get_ollama_repository),
        relay_repo=_resolve(relay_repo, get_relay_llm_repository),
        retrieval_svc=_resolve(retrieval_svc, get_retrieval_service),
        orchestrator=_resolve(orchestrator, get_context_orchestrator),
        double_checker=_resolve(double_checker, get_double_check_verifier),
        rule_engine=_resolve(rule_engine, get_sql_rule_engine),
    )


def get_spec_query_service(
    ollama_repo: OllamaEmbeddingRepository = Depends(get_ollama_repository),
    relay_repo: RelayLlmRepository = Depends(get_relay_llm_repository),
    retrieval_svc: RetrievalService = Depends(get_retrieval_service),
    orchestrator: ContextOrchestrator = Depends(get_context_orchestrator),
) -> SpecQueryService:
    """组装规范知识问答编排服务"""
    return SpecQueryService(
        ollama_repo=_resolve(ollama_repo, get_ollama_repository),
        relay_repo=_resolve(relay_repo, get_relay_llm_repository),
        retrieval_svc=_resolve(retrieval_svc, get_retrieval_service),
        orchestrator=_resolve(orchestrator, get_context_orchestrator),
    )

