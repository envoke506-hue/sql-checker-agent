r"""
SQL 规范审查核心服务 (SqlAuditService)

【课程与企业级架构核心知识点 (落地第 18、19 篇)】
1. 完整 RAG 审计流水线编排:
   SQL 输入 -> SqlFeatureExtractor 特征感知 -> 双路检索与 RRF 融合 (RetrievalService)
   -> Lost-in-the-Middle 头尾重排与动态编号 (ContextOrchestrator)
   -> 深度系统提示词构建与 DeepSeek-Flash 推理 (RelayLlmRepository)
   -> 静态规则反向交叉断言与防幻觉二次核验 (DoubleCheckVerifier)
   -> 精简 Markdown 整改回复与结构化 DTO 渲染输出 (AuditReportRenderer)。
2. 防御性工程设计:
   - 全链路异步非阻塞；
   - 鲁棒的 JSON 解析器，自动剥离大模型思考过程与 Markdown 代码块包裹；
   - 模型未返回合法 JSON 时追加强约束重试一次，仍失败则显式报错，严禁伪判「完全合规」。
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
from app.core.exceptions import ModelServiceException
from app.repositories.ollama_embedding_repository import OllamaEmbeddingRepository
from app.repositories.relay_llm_repository import RelayLlmRepository
from app.services.audit_report_renderer import AuditReportRenderer
from app.services.context_orchestrator import ContextOrchestrator, OrchestratedContext
from app.services.double_check_verifier import DoubleCheckVerifier
from app.services.retrieval_service import RetrievalService
from app.services.sql_rule.engine import SqlRuleEngine


# 单次审查的大模型输出上限：deepseek 系列会把思考过程计入 completion_tokens，
# 提升到 32768，为超大业务表留足生成预算，防止思考耗尽 token 截断。
AUDIT_MAX_TOKENS = 32768


class SqlAuditService:
    """
    SQL 规范审查核心业务编排服务
    """

    SYSTEM_PROMPT_TEMPLATE = """你是一名资深的企业级数据库 DBA 与架构师，负责对研发人员提交的 MySQL DDL 语句进行严谨的数据库表设计规范合规审查。

【思考与输出纪律（重要铁律）】
1. 【极简快速思考，严禁长篇论述】：在内部只进行极简速记思考（严格控制在 200 字以内），直接快速定位违规项，严禁逐字段展开推导论述；面对多字段大表时，思考中严禁推导合规字段，思考完毕后必须立即开始输出最终 JSON 正文；
2. 你的整段回答必须是一个合法的 JSON 对象：第一个字符必须是 `{`，最后一个字符必须是 `}`。

【审查原则与铁律】
1. 你必须严格依据下方【参考数据库设计规范依据】进行审查与重构，严禁自行臆造或引入规范中未提及的外部规则。
2. 每一个检测到的违规项，必须在 `citation_index` 中精确标注其依据的规范编号（如 1, 2, 3 等，必须为整数）。
3. 如果输入 SQL 完全合规，`violations` 必须为空数组，`is_compliant` 为 true。
4. 【推荐性条款与模板字段豁免】：
   - 规范中带有「可以」、「尽量」等字样的推荐性条款（如「数字类型已知不存在负数的情况下可以加 UNSIGNED」），仅供建议，严禁作为强制 ERROR 扣分；
   - 严禁对规范建表模板原文中已明确定义的标准基类字段（如 `version INT NOT NULL DEFAULT 0`）报未加 UNSIGNED 违规。
5. 【字符与字符串类型规范】：
   - 只有真正表示 1 个字符（如 `is_split`、单字符状态标记）时，统一使用 `TINYINT(4)`，不得使用 `char(1)`；
   - 大于 1 个字符的字符串（如车牌号、各种业务 ID/流水号），统一使用 `varchar(N)`，严禁使用定长 `char(N)`；严禁将 `char(22)` 等多字符字段误判为单字符甚至错误建议为 `TINYINT(4)`！
   - 布尔类型字段统一使用 `TINYINT(4)` 且列名尽量用名词。
6. 【严禁合规反咬与假阳性误报（重中之重）】：
   - 必须严格核实字段在待审查 SQL 中的真实定义！如果字段在待审查 SQL 中已经使用了 `decimal(20, 6)`，严禁报其未用 decimal；
   - 如果单价字段已是 `_price`、金额字段已是 `_money`、数量已是 `_amount`，严禁将其列入违规列表；
   - 严禁出现「字段基本符合规范，需保留」却打上 ERROR 违规的情况。只有真正违反规范的字段才可输出到 `violations` 数组中！
7. 【同规则多字段必须合并】：
   - 如果同一条规范规则在多个字段违规（例如多个字段未使用标准名词术语，或多个字段手写字符集），**必须合并为一条违规项**输出；
   - 在 `target_object` 中用逗号列出所有违规字段（如 "dept, organ, goods"），在 `description` 中汇总说明，严禁对同一规则拆分为多条同名重复记录。
8. 【本表字段不加表名规则与主客体边界约束】：
   - 规范第 16 条「若是本表自己的字段，字段前不需要加表名」仅适用于本表自身属性（如 order 表的 order_code 改为 code，主键命名为 id 而非 order_id）；
   - 【严禁过度去除前缀导致重名或关键字】：
     ① 从属维度/商品物料实体属性（如 oil_order 表中的加油油品属性 oil_no、oil_name、oil_type，或第三方属性 third_user_id、gas_id）严禁粗暴去除前缀，否则会丢失业务主客体语义；
     ② 严禁将时间字段（如 order_time）去前缀改为保留关键字 'time'（MySQL 保留字与数据类型）；
     ③ 严禁因去除前缀导致同表出现重复字段名（例如若同时存在 order_no 与 oil_no，严禁均剥离为 'no' 造成语法冲突）！重构后的 DDL 必须保证字段名唯一、无语法冲突。
9. 你必须给出符合所有规范标准的完整重构 DDL SQL（`suggested_sql`）：
   - 必须包含规范建表模板所要求的 7 大通用基类审计字段：`version`, `deleted`, `disabled`, `create_id`, `create_time`, `modify_id`, `modify_time`；
   - 主键字段名统一为 `id`，类型为 `BIGINT UNSIGNED`，遵循雪花算法无自增规范，严禁 `AUTO_INCREMENT`；
   - 金额统一命名为 `_money` 或规范字段，类型必须为 `decimal(20, 6)`，严禁 `double`；
   - 数量统一命名后缀为 `_amount`（如 oil_amount，原字段如 num 属于未遵循数量命名规范，而非保留关键字）；
   - 严禁任何形式的外键约束 (`FOREIGN KEY`)；
   - 严禁触发器、存储过程、自定义函数；
   - 表名若无特殊要求，必须规范命名且不能使用保留关键字；库前缀在无特殊情况统一使用 db_，表名不需要强制以 db_ 开头；关联表必须以 `r_` 开头；
   - 包含 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4` 与字段/表中文注释。
10. 违规条目必须精炼可读（最终会直接呈现给研发人员作为整改清单）：
   - `description` 只说明「违反了什么」，40 字以内，严禁长篇论证；
   - `suggested_fix` 只给出可直接落地的字段级整改动作，30 字以内；
   - `description` 与 `suggested_fix` 中严禁出现 Markdown 语法（如 `**`、`#`、表格、换行）。

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
      "description": "double 存在精度丢失风险，金额必须用 decimal(20, 6)",
      "suggested_fix": "改为 decimal(20, 6)，命名后缀为 _money",
      "citation_index": 2
    }
  ],
  "suggested_sql": "CREATE TABLE db_order ( id BIGINT UNSIGNED NOT NULL COMMENT '主键' ... (必须为纯 SQL 文本，严禁嵌套 ``` 代码块)"
}
"""

    def __init__(
        self,
        ollama_repo: Optional[OllamaEmbeddingRepository] = None,
        relay_repo: Optional[RelayLlmRepository] = None,
        retrieval_svc: Optional[RetrievalService] = None,
        orchestrator: Optional[ContextOrchestrator] = None,
        double_checker: Optional[DoubleCheckVerifier] = None,
        rule_engine: Optional[SqlRuleEngine] = None,
    ):
        self.ollama_repo = ollama_repo or OllamaEmbeddingRepository()
        self.relay_repo = relay_repo or RelayLlmRepository()
        self.retrieval_svc = retrieval_svc or RetrievalService(ollama_repo=self.ollama_repo)
        self.orchestrator = orchestrator or ContextOrchestrator()
        self.double_checker = double_checker or DoubleCheckVerifier()
        self.rule_engine = rule_engine or SqlRuleEngine()

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
            preview = (cleaned[:150] + " ... " + cleaned[-150:]) if len(cleaned) > 300 else cleaned
            print(f"[WARN] [JSON 解析异常] 文本长度={len(cleaned)}, 摘要截取: {repr(preview)}, 错误: {e}")
            raise ValueError(f"无法将大模型输出解析为有效 JSON: {e}")

    def _build_audit_payload(self, llm_output: str) -> Dict[str, Any]:
        """
        将大模型输出解析并映射为结构化审查结果 (总结 / 重构 SQL / 违规明细)

        :raises ValueError: 输出中不存在可解析的合法 JSON
        """
        parsed_json = self._extract_json_from_llm(llm_output)

        violations: List[ViolationDetail] = []
        for item in parsed_json.get("violations", []):
            violations.append(
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

        return {
            "summary": str(parsed_json.get("summary", "审查完成。")),
            "suggested_sql": str(parsed_json.get("suggested_sql", "")),
            "violations": violations,
        }

    @staticmethod
    def _clean_suggested_sql(sql: str) -> str:
        r"""
        清洗重构 SQL：
        1. 移除雪花算法主键后遗留的 AUTO_INCREMENT；
        2. 移除表选项中多余的 AUTO_INCREMENT=\d+；
        3. 保护时间字段避免成为裸保留关键字 `time` DATETIME。
        """
        if not sql:
            return sql
        cleaned = sql
        # 移除 id 行的 AUTO_INCREMENT（兼容有无反引号）
        cleaned = re.sub(
            r"([`]?id[`]?\s+BIGINT\s+UNSIGNED\s+NOT\s+NULL)\s+AUTO_INCREMENT\b",
            r"\1",
            cleaned,
            flags=re.IGNORECASE,
        )
        # 移除末尾 AUTO_INCREMENT=\d+
        cleaned = re.sub(r"\s+AUTO_INCREMENT=\d+", "", cleaned, flags=re.IGNORECASE)
        # 避免 `time` DATETIME 保留关键字，自动修复为 `order_time`
        cleaned = re.sub(
            r"([`\s])time([`\s]+(?:DATETIME|TIMESTAMP))",
            r"\1order_time\2",
            cleaned,
            flags=re.IGNORECASE,
        )
        return cleaned

    @staticmethod
    def _resolve_citation_index(category: str, chunk_index_map: Dict[int, Any]) -> int:
        """根据规则分类在动态切块映射中寻址最匹配的规范章节引用编号"""
        if not chunk_index_map:
            return 1
        for idx, chunk in chunk_index_map.items():
            heading = (chunk.metadata.heading_path or "").lower()
            sec = (chunk.metadata.section or "").lower()
            cid = (chunk.chunk_id or "").lower()

            if category == "database_rule":
                if any(kw in heading or kw in sec or kw in cid for kw in ["建库规范", "database_rule", "建库"]):
                    return idx
            elif category == "sql_template":
                if any(kw in heading or kw in sec or kw in cid for kw in ["建表模板", "table_template", "基类"]):
                    return idx
            elif category == "naming_rule":
                if any(kw in heading or kw in sec or kw in cid for kw in ["命名规范", "naming_rule", "命名"]):
                    return idx
            elif category == "glossary":
                if any(kw in heading or kw in sec or kw in cid for kw in ["名词术语", "terminology", "单词"]):
                    return idx

        # 若未精准匹配，默认返回首个有效引用序号
        return min(chunk_index_map.keys()) if chunk_index_map else 1

    async def audit_sql(self, request: SqlAuditRequest) -> SqlAuditResponseData:
        """
        异步执行端到端的 SQL 规范合规审查全流程 (企业级双环模型):
        1. 阶段一: 代码静态规则引擎 (AST驱动) 先行执行 100% 确定性硬规则与降噪聚合
        2. 阶段二: 大模型 (AI Copilot) 结合确定性违规事实进行深层语义拼写识别与完整 DDL 重构
        3. 阶段三: 精简输出终态报告，杜绝双重曝光与刷屏
        """
        # =========================================================================
        # 步骤 0: 阶段一 - 代码静态规则引擎先行执行 (聚合降噪 + 闭环安全建议)
        # =========================================================================
        static_result = self.rule_engine.validate(request.sql_text)

        # 步骤 1: 双路特征感知与混合检索 (Retrieval)
        ranked_chunks = await self.retrieval_svc.retrieve_for_sql(
            sql_text=request.sql_text,
            top_k=5
        )

        # 步骤 2: Lost-in-the-Middle 排序与动态引用编号编排 (Orchestration)
        orchestrated_ctx = self.orchestrator.orchestrate(
            ranked_chunks=ranked_chunks,
            enable_reorder=True
        )

        # 为代码静态规则违规项精准绑定动态切块引用序号 (消除写死 [1] 的依据失真)
        static_violations: List[ViolationDetail] = []
        for stmt_res in static_result.results:
            for v in stmt_res.violations:
                cit_idx = self._resolve_citation_index(v.category, orchestrated_ctx.chunk_index_map)
                static_violations.append(
                    ViolationDetail(
                        rule_id=v.rule_id,
                        rule_name=v.rule_name,
                        severity=v.severity,
                        target_object=v.target_object,
                        description=v.message,
                        suggested_fix=v.suggested_fix,
                        citation_index=cit_idx,
                    )
                )

        # 步骤 3: 构造 System Prompt 与 User Prompt (告知大模型已确定的硬伤，让其专注语义与重构)
        static_hints = ""
        if static_violations:
            hints_list = [f"- [{v.severity}] {v.rule_name} (对象: {v.target_object}): {v.description} -> 终态建议: {v.suggested_fix}" for v in static_violations]
            static_hints = (
                f"\n\n### 【代码静态规则引擎已确定的违规事实（已完成聚合与建议防冲突，不可推翻）】:\n"
                f"{chr(10).join(hints_list)}\n\n"
                f"【大模型任务纪律要求】:\n"
                f"1. 上述清单属于客观确凿事实，你【严禁】在返回的 violations 中对上述同类硬性规则拆分字段重复输出；\n"
                f"2. 你主要负责两件事：\n"
                f"   ① 语义与拼写检查：如在字段名或注释中发现代码无法识别的深层业务语义笔误（如拼写错误 busine_hours 应为 business_hours），可在 violations 中补充；若无补充则保持 violations 为空；\n"
                f"   ② 完整重构 SQL (suggested_sql)：必须综合上述所有违规项，输出一份修复纠正后的、符合全部规范的完整建表 DDL SQL！"
            )

        system_content = self.SYSTEM_PROMPT_TEMPLATE
        user_content = (
            f"### 【待审查 DDL SQL】:\n"
            f"```sql\n{request.sql_text.strip()}\n```\n"
            f"{static_hints}\n\n"
            f"### 【参考数据库设计规范依据】:\n"
            f"{orchestrated_ctx.formatted_context_text}\n\n"
            f"请根据上述规范依据与已知违规事实输出符合约定的完整 JSON。"
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        # 步骤 4: 调用大模型进行推理审查与重构 SQL 生成
        raw_output = await self.relay_repo.generate(
            messages=messages,
            temperature=0.1,
            max_tokens=AUDIT_MAX_TOKENS,
            response_format={"type": "json_object"}
        )

        # 步骤 5: 结构化解析 LLM 结果 (带失败重试机制)
        try:
            payload = self._build_audit_payload(raw_output)
        except Exception as first_error:
            print(f"[WARN] [大模型审查解析失败] {first_error}，追加极简 JSON 约束后重试一次")
            retry_messages = messages + [{
                "role": "user",
                "content": (
                    "上一次输出因推理思考过长或截断未能返回完整合法 JSON。请本次【完全跳过中间思考与推导】，"
                    "立即只输出审查结果的合法根 JSON 对象（以 { 开头、以 } 结尾），严禁思维链、解释文字与代码围栏。"
                )
            }]
            try:
                retry_output = await self.relay_repo.generate(
                    messages=retry_messages,
                    temperature=0.0,
                    max_tokens=AUDIT_MAX_TOKENS,
                    response_format={"type": "json_object"}
                )
                payload = self._build_audit_payload(retry_output)
            except Exception as retry_error:
                print(f"[WARN] [大模型审查解析失败] 重试仍未返回合法 JSON: {retry_error}")
                raise ModelServiceException(
                    message="大模型本次未返回可解析的审查结果，请重试",
                    detail=str(retry_error)
                ) from retry_error

        summary = payload["summary"]
        suggested_sql = self._clean_suggested_sql(payload["suggested_sql"] or request.sql_text)
        raw_violations: List[ViolationDetail] = payload["violations"]

        # 步骤 6: Double Check 二次断言核验与防幻觉过滤
        check_result = self.double_checker.verify_and_filter(
            raw_violations=raw_violations,
            chunk_index_map=orchestrated_ctx.chunk_index_map,
            summary=summary,
            sql_text=request.sql_text
        )

        # 步骤 7: 企业级违规项融合 (代码硬性违规为主体，彻底抑制大模型在同类硬规则上的重复报错，仅吸收独特的纯语义增量)
        # 代码规则引擎管辖的所有硬规则语义特征词 (中英文、小写)
        static_managed_keywords = {
            # 库名前缀与显式声明
            "库名", "建库", "db_", "schema", "database",
            # 字符集与存储引擎
            "字符集", "utf8", "utf8mb4", "charset", "collate", "排序规则", "编码",
            "存储引擎", "innodb", "engine", "引擎",
            # 基类审计字段与主键规范
            "基类", "审计字段", "建表模板", "base_entity", "template", "模板",
            "deleted", "disabled", "version", "create_time", "modify_time", "create_id", "modify_id",
            "主键", "primary key", "自增",
            # 保留关键字与命名规则
            "保留字", "关键字", "keyword", "reserved",
            "本表字段", "表名前缀", "加表名", "去掉表名", "prefix",
            # 规范名词术语字典
            "名词术语", "规范名词", "术语", "标准命名单词", "单词字典", "glossary", "term", "phone", "tel",
            # 字段约束与数据类型
            "not null", "not_null", "非空",
            "double", "float", "tinyint", "decimal", "浮点数", "unsigned", "数据类型",
            # 字段级字符集与高级数据库对象
            "字段字符集", "column charset",
            "外键", "foreign key", "触发器", "trigger", "存储过程", "procedure", "视图", "view",
            "after", "first", "列顺序",
        }

        combined_violations: List[ViolationDetail] = list(static_violations)
        
        # 收集代码静态违规项中涉及的所有目标对象 token（转为小写集合，按逗号/空格切分）
        existing_target_tokens = set()
        for v in static_violations:
            for token in v.target_object.replace(",", " ").replace("，", " ").split():
                cleaned = token.strip("`'\"()（） ").lower()
                if cleaned and cleaned not in {"等", "共", "个字段", "字段"}:
                    existing_target_tokens.add(cleaned)

        for v in check_result.verified_violations:
            v_text = f"{v.rule_id} {v.rule_name} {v.description}".lower()

            # 判定 1: 若大模型违规项命中了代码规则引擎管辖的硬规则范畴，无条件抑制过滤 (绝不重复报送)
            if any(kw in v_text for kw in static_managed_keywords):
                continue

            # 判定 2: 若为大模型语义违规，但涉及的字段对象已在静态规则中被完全覆盖，且规则同名，予以防重过滤
            v_target_tokens = {
                t.strip("`'\"()（） ").lower()
                for t in v.target_object.replace(",", " ").replace("，", " ").split()
                if t.strip("`'\"()（） ") and t.strip("`'\"()（） ") not in {"等", "共", "个字段", "字段"}
            }
            if v_target_tokens and v_target_tokens.issubset(existing_target_tokens) and v.rule_name in {ev.rule_name for ev in combined_violations}:
                continue

            # 保留大模型独特的纯语义增量 (如纯业务拼写错误 busine_hours -> business_hours)
            combined_violations.append(v)

        # 步骤 8: 动态计算合规状态与最终评分
        has_error = any(v.severity == "ERROR" for v in combined_violations)
        final_is_compliant = not has_error
        error_count = sum(1 for v in combined_violations if v.severity == "ERROR")
        warn_count = sum(1 for v in combined_violations if v.severity == "WARN")
        final_score = max(0, 100 - (error_count * 15 + warn_count * 5))

        # 步骤 9: 渲染精简 Markdown 整改回复
        markdown_report = AuditReportRenderer.render(
            is_compliant=final_is_compliant,
            score=final_score,
            violations=combined_violations,
            suggested_sql=suggested_sql,
            citations=orchestrated_ctx.citations,
        )

        # 步骤 10: 组装输出标准响应 DTO
        return SqlAuditResponseData(
            is_compliant=final_is_compliant,
            score=final_score,
            summary=summary,
            violations=combined_violations,
            suggested_sql=suggested_sql,
            citations=orchestrated_ctx.citations,
            markdown_report=markdown_report
        )
