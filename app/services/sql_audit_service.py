r"""
SQL 规范审查核心服务 (SqlAuditService)

【课程与企业级架构核心知识点 (落地第 18、19 篇)】
1. 完整 RAG 审计流水线编排:
   SQL 输入 -> SqlFeatureExtractor 特征感知 -> 双路检索与 RRF 融合 (RetrievalService)
   -> Lost-in-the-Middle 头尾重排与动态编号 (ContextOrchestrator)
   -> 深度系统提示词构建与 DeepSeek-Flash 推理 (RelayLlmRepository)
   -> 静态规则反向交叉断言与防幻觉二次核验 (DoubleCheckVerifier)
   -> 标准 Markdown 报告与结构化 DTO 渲染输出 (AuditReportRenderer)。
2. 防御性工程设计:
   - 全链路异步非阻塞；
   - 鲁棒的 JSON 解析器，自动剥离大模型思考过程与 Markdown 代码块包裹；
   - 模型异常情况下的安全降级兜底。
"""

import json
import re
from typing import Any, Dict, List, Optional

from app.models.dto.sql_audit import (
    CitationDetail,
    SqlAuditRequest,
    SqlAuditResponseData,
    ViolationDetail,
)
from app.repositories.ollama_embedding_repository import OllamaEmbeddingRepository
from app.repositories.relay_llm_repository import RelayLlmRepository
from app.services.audit_report_renderer import AuditReportRenderer
from app.services.context_orchestrator import ContextOrchestrator, OrchestratedContext
from app.services.double_check_verifier import DoubleCheckVerifier
from app.services.retrieval_service import RetrievalService


class SqlAuditService:
    """
    SQL 规范审查核心业务编排服务
    """

    SYSTEM_PROMPT_TEMPLATE = """你是一名资深的企业级数据库 DBA 与架构师，负责对研发人员提交的 MySQL DDL 语句进行严谨的数据库表设计规范合规审查。

【思考与输出纪律】
请用不超过 100 字快速完成简要思考，严禁长篇展开论述，立即输出合法的 JSON 对象！

【审查原则与铁律】
1. 你必须严格依据下方【参考数据库设计规范依据】进行审查与重构，严禁自行臆造或引入规范中未提及的外部规则。
2. 每一个检测到的违规项，必须在 `citation_index` 中精确标注其依据的规范编号（如 1, 2, 3 等，必须为整数）。
3. 如果输入 SQL 完全合规，`violations` 必须为空数组，`is_compliant` 为 true。
4. 你必须给出符合所有规范标准的完整重构 DDL SQL（`suggested_sql`）：
   - 必须包含规范建表模板所要求的 7 大通用基类审计字段：`version`, `deleted`, `disabled`, `create_id`, `create_time`, `modify_id`, `modify_time`；
   - 主键字段名统一为 `id`，类型为 `BIGINT UNSIGNED`；
   - 金额统一命名为 `_money` 或规范字段，类型必须为 `decimal(20, 6)`，严禁 `double`；
   - 严禁任何形式的外键约束 (`FOREIGN KEY`)；
   - 本表字段名前严禁拼接本表表名（例如在 order 表中写 order_id 是反例，必须直接为 id）；
   - 表名若无特殊要求，必须规范命名且不能使用保留关键字；
   - 包含 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4` 与字段/表中文注释。

【输出格式要求】
你必须直接返回一个合法的 JSON 字符串，严禁在外部包裹任何 ```json 围栏，严禁在 JSON 内部包含任何嵌套的 ``` 代码块：
{
  "is_compliant": false,
  "summary": "审查结果核心总结（100字以内）",
  "violations": [
    {
      "rule_id": "rule_no_double",
      "rule_name": "禁止使用浮点数 double",
      "severity": "ERROR",
      "target_object": "total_amount double",
      "description": "规范建库规范明确指出 double 类型存在精度丢失风险，金额必须使用 decimal(20, 6) 存储",
      "suggested_fix": "将 double 修改为 decimal(20, 6)",
      "citation_index": 2
    }
  ],
  "suggested_sql": "CREATE TABLE db_order ( id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT ... (必须为纯 SQL 文本，严禁嵌套 ``` 代码块)"
}
"""

    def __init__(
        self,
        ollama_repo: Optional[OllamaEmbeddingRepository] = None,
        relay_repo: Optional[RelayLlmRepository] = None,
        retrieval_svc: Optional[RetrievalService] = None,
        orchestrator: Optional[ContextOrchestrator] = None,
        double_checker: Optional[DoubleCheckVerifier] = None,
    ):
        self.ollama_repo = ollama_repo or OllamaEmbeddingRepository()
        self.relay_repo = relay_repo or RelayLlmRepository()
        self.retrieval_svc = retrieval_svc or RetrievalService(ollama_repo=self.ollama_repo)
        self.orchestrator = orchestrator or ContextOrchestrator()
        self.double_checker = double_checker or DoubleCheckVerifier()

    @staticmethod
    def _extract_json_from_llm(llm_output: str) -> Dict[str, Any]:
        """
        从大模型返回的文本中安全提取合法的根 JSON 数据
        自动兼容思维链前缀、多段代码块与嵌套代码围栏
        """
        cleaned = llm_output.strip()

        # 1. 过滤思维链 <think>...</think> 标签 (若存在)
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned).strip()

        # 2. 策略 A: 优先正则靶向匹配包含 "is_compliant" 的核心根 JSON 闭包
        root_json_match = re.search(r"(\{\s*\"is_compliant\"[\s\S]*\})", cleaned)
        if root_json_match:
            candidate = root_json_match.group(1).strip()
            # 从后向前扫描找到真正匹配闭合的最长合法 JSON
            for end_pos in range(len(candidate), 0, -1):
                if candidate[end_pos - 1] == '}':
                    sub = candidate[:end_pos]
                    try:
                        return json.loads(sub)
                    except Exception:
                        continue

        # 3. 策略 B: 从后往前寻找平衡的大括号 { ... }
        # 因为在含思考推导的输出中，真正的最终交付 JSON 总是位于文本末尾
        last_brace_end = cleaned.rfind("}")
        if last_brace_end != -1:
            for start_pos in range(last_brace_end - 1, -1, -1):
                if cleaned[start_pos] == '{':
                    sub = cleaned[start_pos : last_brace_end + 1]
                    try:
                        parsed = json.loads(sub)
                        if isinstance(parsed, dict) and "is_compliant" in parsed:
                            return parsed
                    except Exception:
                        continue

        # 4. 策略 C: 提取 Markdown 代码块 ```json { ... } ```
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except Exception:
                pass

        # 5. 兜底直接尝试解析整个文本
        try:
            return json.loads(cleaned)
        except Exception as e:
            print(f"[WARN] [JSON 解析异常] 原始文本截取 (长度={len(llm_output)}): {repr(llm_output[:300])}, 错误: {e}")
            raise ValueError(f"无法将大模型输出解析为有效 JSON: {e}")

    async def audit_sql(self, request: SqlAuditRequest) -> SqlAuditResponseData:
        """
        异步执行端到端的 SQL 规范合规审查全流程
        """
        # 步骤 1: 双路特征感知与混合检索 (Retrieval)
        ranked_chunks = await self.retrieval_svc.retrieve_for_sql(
            sql_text=request.sql_text,
            top_k=3
        )

        # 步骤 2: Lost-in-the-Middle 排序与动态引用编号编排 (Orchestration)
        orchestrated_ctx = self.orchestrator.orchestrate(
            ranked_chunks=ranked_chunks,
            enable_reorder=True
        )

        # 步骤 3: 构造 System Prompt 与 User Prompt
        system_content = self.SYSTEM_PROMPT_TEMPLATE
        user_content = (
            f"### 【待审查 DDL SQL】:\n"
            f"```sql\n{request.sql_text.strip()}\n```\n\n"
            f"### 【参考数据库设计规范依据】:\n"
            f"{orchestrated_ctx.formatted_context_text}\n\n"
            f"请根据上述规范依据对该 SQL 进行严格审查，输出符合上述约定的完整 JSON。"
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        # 步骤 4: 调用大模型进行推理审查 (强制 JSON 格式输出，低温度以确保严谨)
        raw_output = await self.relay_repo.generate(
            messages=messages,
            temperature=0.1,
            max_tokens=8192,
            response_format={"type": "json_object"}
        )

        # 步骤 5: 结构化解析 LLM 结果
        raw_violations: List[ViolationDetail] = []
        suggested_sql = request.sql_text
        summary = "审查完成。"
        try:
            parsed_json = self._extract_json_from_llm(raw_output)
            summary = parsed_json.get("summary", "审查完成。")
            suggested_sql = parsed_json.get("suggested_sql", request.sql_text)
            
            raw_violations_data = parsed_json.get("violations", [])
            for item in raw_violations_data:
                raw_violations.append(
                    ViolationDetail(
                        rule_id=str(item.get("rule_id", "rule_general")),
                        rule_name=str(item.get("rule_name", "设计规范违规")),
                        severity=str(item.get("severity", "ERROR")),
                        target_object=str(item.get("target_object", "")),
                        description=str(item.get("description", "")),
                        suggested_fix=str(item.get("suggested_fix", "")),
                        citation_index=int(item.get("citation_index", 1)),
                    )
                )
        except Exception as e:
            print(f"[WARN] [大模型审查解析降级] {e}，将生成基础审查报告")
            summary = f"大模型输出解析提示: {e}"

        # 步骤 6: Double Check 二次断言核验与防幻觉过滤
        check_result = self.double_checker.verify_and_filter(
            raw_violations=raw_violations,
            chunk_index_map=orchestrated_ctx.chunk_index_map
        )

        # 步骤 7: 渲染企业级标准 Markdown 审查报告
        markdown_report = AuditReportRenderer.render(
            is_compliant=check_result.is_compliant,
            score=check_result.score,
            summary=summary,
            violations=check_result.verified_violations,
            suggested_sql=suggested_sql,
            citations=orchestrated_ctx.citations,
            original_sql=request.sql_text
        )

        # 步骤 8: 组装输出标准响应 DTO
        return SqlAuditResponseData(
            is_compliant=check_result.is_compliant,
            score=check_result.score,
            summary=summary,
            violations=check_result.verified_violations,
            suggested_sql=suggested_sql,
            citations=orchestrated_ctx.citations,
            markdown_report=markdown_report
        )
