r"""
规范知识问答核心服务 (SpecQueryService)

【课程与企业级架构核心知识点 (落地第 18、19 篇)】
1. 规范问答 RAG 业务流:
   用户提问 -> 双路检索与 RRF 融合 (RetrievalService)
   -> 动态引用编号编排 (ContextOrchestrator)
   -> 严格依据依据回答与引用角标嵌入 (RelayLlmRepository)
   -> 结构化 Markdown 解答与溯源 Citations 输出。
2. 严格防幻觉提示词:
   - 明确要求“白纸黑字有依据才能答”，规范未说明的内容明确告知用户“规范未做强制约定”。
"""

from typing import List, Optional

from app.models.dto.sql_audit import CitationDetail
from app.models.dto.spec_query import (
    SpecQueryRequest,
    SpecQueryResponseData,
)
from app.repositories.ollama_embedding_repository import OllamaEmbeddingRepository
from app.repositories.relay_llm_repository import RelayLlmRepository
from app.services.context_orchestrator import ContextOrchestrator
from app.services.retrieval_service import RetrievalService


class SpecQueryService:
    """
    规范知识问答编排服务
    """

    SYSTEM_PROMPT = """你是一名严谨的数据库团队架构师，负责解答研发工程师关于《数据库规范》的技术咨询。

【作答规则】
1. 你的回答必须严格依据下方给出的【参考数据库设计规范依据】，白纸黑字有记载的才能回答。
2. 在回答正文中，提到具体规则条款时，必须在对应句子末尾标注引用编号（例如“金额字段必须使用 decimal(20, 6) 存储 [1]”）。
3. 如果参考规范依据中没有提及用户咨询的内容，请如实回答：“在当前的数据库规范中，未对该项作出明确规定或限制”，严禁依据通用经验凭空捏造。
4. 回答风格要求：条理清晰、专业精炼，使用标准 Markdown 格式排版（支持列表、加粗、代码块）。
"""

    def __init__(
        self,
        ollama_repo: Optional[OllamaEmbeddingRepository] = None,
        relay_repo: Optional[RelayLlmRepository] = None,
        retrieval_svc: Optional[RetrievalService] = None,
        orchestrator: Optional[ContextOrchestrator] = None,
    ):
        self.ollama_repo = ollama_repo or OllamaEmbeddingRepository()
        self.relay_repo = relay_repo or RelayLlmRepository()
        self.retrieval_svc = retrieval_svc or RetrievalService(ollama_repo=self.ollama_repo)
        self.orchestrator = orchestrator or ContextOrchestrator()

    async def query_spec(self, request: SpecQueryRequest) -> SpecQueryResponseData:
        """
        异步根据用户自然语言提问检索规范知识库并给出带依据的解答
        """
        # 步骤 1: 检索高相关规范条款 (Top 3)
        ranked_chunks = await self.retrieval_svc.retrieve_for_query(
            question=request.question,
            top_k=3
        )

        # 步骤 2: 上下文编排与编号
        orchestrated_ctx = self.orchestrator.orchestrate(
            ranked_chunks=ranked_chunks,
            enable_reorder=False  # 问答场景保持最佳相关度降序
        )

        # 步骤 3: 构造提示词并调用 LLM
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"### 用户咨询问题:\n{request.question}\n\n"
                    f"### 参考数据库设计规范依据:\n"
                    f"{orchestrated_ctx.formatted_context_text}\n\n"
                    f"请基于上述依据给出规范解答："
                ),
            },
        ]

        llm_answer = await self.relay_repo.generate(
            messages=messages,
            temperature=0.2,
            # deepseek 系列会把思考过程计入 completion_tokens，预算过小会导致正式回答还没
            # 输出就被截断，故与 SQL 审查保持同样的输出上限
            max_tokens=8192
        )

        # 步骤 4: 渲染完整 Markdown 内容
        markdown_blocks: List[str] = [
            "### 💡 数据库规范咨询解答",
            "",
            llm_answer.strip(),
            "",
            "#### 📚 规范条款引用依据:",
        ]
        for c in orchestrated_ctx.citations:
            markdown_blocks.append(f"- **[{c.index}] {c.title}**")
            markdown_blocks.append(f"  > {c.snippet}")

        full_markdown = "\n".join(markdown_blocks)

        return SpecQueryResponseData(
            answer=llm_answer.strip(),
            citations=orchestrated_ctx.citations,
            markdown_content=full_markdown
        )
