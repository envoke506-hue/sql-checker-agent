r"""
上下文编排与 Lost-in-the-Middle 头尾排序引擎 (Context Orchestrator)

【课程与算法知识点深度落地 (落地第 19 篇)】
1. Lost-in-the-Middle (迷失在中腹) 现象与成因:
   - 大模型在长上下文检索中具有显著的“首因效应 (Primacy Effect)”和“近因效应 (Recency Effect)”。
   - 处于上下文开头 (前 15%) 和结尾 (后 15%) 的信息召回率可达 90% 以上，而处于中间腹部的信息极易被大模型视而不见。
   - 如果直接按相关度降序排列 (1, 2, 3, 4, 5)，极其关键的第 2、3 条规范掉入中腹盲区，极易导致审查漏报。
2. 头尾交叉重排算法 (Lost-in-the-Middle Re-ordering):
   - 算法思想：将最相关的高分切块交替安放在两端，相关性稍低的切块沉淀到中央。
   - 变换过程 (假设输入相关度降序为 [A, B, C, D, E]):
     - A (Rank 1) -> 放在最开头
     - B (Rank 2) -> 放在最末尾
     - C (Rank 3) -> 放在开头第 2 位
     - D (Rank 4) -> 放在倒数第 2 位
     - E (Rank 5) -> 沉淀在最中央
     - 最终重排序列为: [A, C, E, D, B]
3. 动态引用编号与溯源映射 (Citation Mapping):
   - 为编排后的每个规范 Chunk 分配全局唯一的 `[1]`, `[2]` 编号标记。
   - 保留内存映射，供后续 Double Check 模块进行防幻觉断言核验。
"""

from typing import Dict, List, NamedTuple, Tuple
from pydantic import BaseModel, Field

from app.models.dto.sql_audit import CitationDetail
from app.models.entity.chunk import Chunk


class OrchestratedContext(BaseModel):
    """
    编排后的上下文数据载荷
    """
    formatted_context_text: str = Field(..., description="拼接好编号与元数据的规范提示词文本")
    citations: List[CitationDetail] = Field(default_factory=list, description="前端展示与机器溯源用的引用列表")
    chunk_index_map: Dict[int, Chunk] = Field(default_factory=dict, description="编号到原始 Chunk 实体的内存快速查找映射")


class ContextOrchestrator:
    """
    负责长上下文重排、抗注意力遗忘编排与动态引用标记
    """

    @staticmethod
    def reorder_lost_in_the_middle(items: List[Tuple[Chunk, float]]) -> List[Tuple[Chunk, float]]:
        """
        Lost-in-the-Middle 核心交替重排算法
        
        :param items: 已经按相关度 (如 RRF 得分) 从高到低排好序的 [(Chunk, score), ...]
        :return: 经过首尾交替重排后的列表
        """
        if len(items) <= 2:
            return items

        reordered: List[Tuple[Chunk, float]] = [None] * len(items)
        left = 0
        right = len(items) - 1

        for i, item in enumerate(items):
            # 偶数索引 (0, 2, 4...) 填入左侧头部，从前向后递进
            if i % 2 == 0:
                reordered[left] = item
                left += 1
            # 奇数索引 (1, 3, 5...) 填入右侧尾部，从后向前递进
            else:
                reordered[right] = item
                right -= 1

        return reordered

    def orchestrate(
        self,
        ranked_chunks: List[Tuple[Chunk, float]],
        enable_reorder: bool = True
    ) -> OrchestratedContext:
        """
        执行完整的上下文编排流水线：
        1. 执行 Lost-in-the-Middle 头尾重排
        2. 分配规范引用编号 [1], [2]...
        3. 拼接带有结构化元数据（小节、路径、分类）的上下文 Markdown 文本
        4. 生成 CitationDetail 清单和查找映射

        :param ranked_chunks: 检索召回的候选规范列表
        :param enable_reorder: 是否开启 Lost-in-the-Middle 重排
        :return: 编排好的 OrchestratedContext 对象
        """
        if not ranked_chunks:
            return OrchestratedContext(
                formatted_context_text="暂无匹配的相关数据库设计规范条款。",
                citations=[],
                chunk_index_map={}
            )

        # 1. 执行重排 (若启用)
        final_list = self.reorder_lost_in_the_middle(ranked_chunks) if enable_reorder else ranked_chunks

        context_blocks: List[str] = []
        citations: List[CitationDetail] = []
        chunk_index_map: Dict[int, Chunk] = {}

        # 2. 依次生成编号、上下文块与引用明细
        for idx, (chunk, score) in enumerate(final_list, start=1):
            chunk_index_map[idx] = chunk

            # 生成规范摘要 (截取前 120 字作为展示卡片)
            clean_display = chunk.display_text.strip()
            first_line = clean_display.split("\n")[0].strip("# ")
            snippet = clean_display[:150].replace("\n", " ") + "..."

            # 记录 Citation 实体
            citations.append(
                CitationDetail(
                    index=idx,
                    title=f"《{chunk.metadata.doc_title}》- {chunk.metadata.heading_path}",
                    snippet=snippet,
                    source_file=chunk.metadata.source_file,
                )
            )

            # 组装格式化上下文文本 (带有明确的引用编号与元数据，利于 LLM 引用)
            block = (
                f"### 【规范依据 [{idx}]】《{chunk.metadata.doc_title}》\n"
                f"- **层级路径**: {chunk.metadata.heading_path}\n"
                f"- **规范分类**: {chunk.metadata.category} | 细分类型: {chunk.metadata.rule_type}\n"
                f"- **规范正文与正反例条款**:\n"
                f"```markdown\n"
                f"{chunk.display_text}\n"
                f"```\n"
            )
            context_blocks.append(block)

        formatted_text = "\n".join(context_blocks)

        return OrchestratedContext(
            formatted_context_text=formatted_text,
            citations=citations,
            chunk_index_map=chunk_index_map
        )
