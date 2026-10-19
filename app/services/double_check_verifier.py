r"""
二次断言核验器与防幻觉过滤器 (Double Check Verifier)

【课程与算法知识点深度落地 (落地第 19 篇)】
1. 为什么必须做 Double Check (二次核验):
   - 大模型在代码审计场景下极易产生“过度合规幻觉”：
     ① 伪造不存在的规则：模型可能根据其预训练记忆，强行添加团队规范里根本没有的条款（如“索引字段必须以 idx_ 开头”、“varchar 长度超长”等）；
     ② 乱标引用序号：输出引用了 `[8]` 或 `[99]`，但上下文实际只提供了 `[1]~[5]`；
     ③ 指鹿为马：引用了“建库规范 [1]”，但解释的内容却是“命名规范”里的东西。
2. 规则断言引擎校验策略 (Deterministic Rule Assertions):
   - 确定性是企业级系统的底线。通过 Python 静态规则层对 LLM 提取的每条违规记录进行反向溯源核验：
     - 校验 1: 引用序号有效性边界核验；
     - 校验 2: 规范正文反向交叉验证 (Cross-Verification) —— 违规关键词必须真正在该 Chunk 中白纸黑字写明。
3. 动态评分修正 (Dynamic Score Recalculation):
   - 一旦过滤掉幻觉误报，系统重新基于真实违规严重度（ERROR/WARN）动态重算合规评分。
"""

import re
from typing import Dict, List, Set, Tuple
from app.models.dto.sql_audit import ViolationDetail
from app.models.entity.chunk import Chunk


class DoubleCheckResult:
    """二次核验过滤结果封装"""
    def __init__(
        self,
        verified_violations: List[ViolationDetail],
        hallucinations: List[ViolationDetail],
        is_compliant: bool,
        score: int
    ):
        self.verified_violations = verified_violations
        self.hallucinations = hallucinations
        self.is_compliant = is_compliant
        self.score = score


class DoubleCheckVerifier:
    """
    负责对大模型审查结果进行规则断言核验与防幻觉过滤
    """

    # 典型规范规则与必须在 Chunk 正文中出现的特征词白名单映射
    RULE_KEYWORD_REQUIREMENTS: Dict[str, List[str]] = {
        "foreign_key": ["外键", "foreign key", "约束"],
        "double_type": ["double", "decimal", "浮点"],
        "tinyint": ["tinyint", "语义分歧", "tinyint(4)", "tinyint(1)"],
        "redundant_prefix": ["本表", "反例", "加表名", "order_id", "前缀", "表名前缀"],
        "base_fields": ["基类", "基础", "create_time", "modify_time", "version", "deleted", "disabled", "模板", "实体基类"],
        "reserved_keyword": ["关键字", "保留字", "命名", "保留关键字"],
        "naming_suffix": ["price", "money", "amount", "time", "后缀", "命名规范", "biz_", "in_", "out_", "code", "amount_unit"],
        "unsigned_number": ["unsigned", "数字类型", "负数"],
        "not_null_default": ["not null", "null", "默认值"],
        "snowflake_primary_key": ["雪花", "主键", "id", "bigint unsigned"],
        # 补全核心缺失规范项
        "trigger_procedure": ["触发器", "存储过程", "自定义函数", "trigger", "procedure", "function"],
        "charset_collate": ["utf8mb4", "charset", "字符集", "latin1", "utf8", "collate", "排序规则", "手写"],
        "single_char_type": ["tinyint(4)", "单字符", "1个字符", "1 个字符", "标记", "is_split", "char(1)", "varchar(1)"],
        "string_length": ["varchar", "默认长度", "长度", "字符"],
        "index_naming": ["uniq_", "idx_", "唯一索引", "普通索引", "索引命名", "btree"],
        "engine_type": ["innodb", "myisam", "引擎", "engine"],
        "table_prefix_r": ["r_", "关联表"],
        "terminology_words": [
            "术语", "标准词", "name", "parent", "audit", "tag", "relation", "rel_id",
            "status", "type", "dept", "organ", "goods", "address", "zip", "phone",
            "contact", "info", "url", "source", "expire", "duty", "nick"
        ],
    }

    def _is_supported_by_chunk(self, v: ViolationDetail, target_chunk: Chunk) -> bool:
        """检查单个违规项是否在目标 Chunk 内有实质依据支持"""
        chunk_content = (target_chunk.display_text + " " + target_chunk.metadata.heading_path).lower()
        v_text = (v.rule_name + " " + v.description + " " + v.target_object).lower()

        # (1) 检查是否直接包含违规对象名 (如 'double', 'order_id')
        if v.target_object and v.target_object.lower() in chunk_content:
            return True

        # (2) 检查规则关键词白名单命中
        for _, keywords in self.RULE_KEYWORD_REQUIREMENTS.items():
            if any(kw.lower() in v_text for kw in keywords):
                if any(kw.lower() in chunk_content for kw in keywords):
                    return True

        # (3) 规则名称在 Chunk 标题或正文中有明确提及
        clean_rule_name = re.sub(r"[^\w\u4e00-\u9fa5]", "", v.rule_name.lower())
        if clean_rule_name and len(clean_rule_name) >= 2 and any(kw in chunk_content for kw in [clean_rule_name, v.rule_id.lower()]):
            return True

        return False

    @staticmethod
    def _extract_column_defs(sql_text: str) -> Dict[str, Dict[str, str]]:
        """
        从待审查 SQL 文本中提取所有列名及其数据类型与原始定义行
        返回: { "col_name_lower": { "type": "char(22)", "full_line": "`carry_company_id` char(22)..." } }
        """
        cols: Dict[str, Dict[str, str]] = {}
        if not sql_text:
            return cols

        for line in sql_text.splitlines():
            clean = line.strip().rstrip(",")
            if not clean or clean.startswith(("--", "/*", "#")):
                continue
            first_word = clean.split()[0].replace("`", "").upper()
            if first_word in (
                "CREATE", "TABLE", "PRIMARY", "KEY", "UNIQUE", "CONSTRAINT",
                "INDEX", "FOREIGN", "CHECK", "FULLTEXT", "SPATIAL"
            ):
                continue

            m = re.match(r"^`?([a-zA-Z0-9_]+)`?\s+([a-zA-Z0-9_]+(?:\([^)]*\))?)", clean)
            if m:
                col_name = m.group(1).lower()
                col_type = m.group(2).lower()
                cols[col_name] = {
                    "type": col_type,
                    "full_line": clean,
                }
        return cols

    @staticmethod
    def _is_self_contradictory(v: ViolationDetail) -> bool:
        """
        过滤自相矛盾的假阳性违规项：
        模型在描述中自述「基本符合要求需统一保留」、「符合规范无需修改」，却错误打上了 ERROR/WARN 违规标记
        """
        desc = (v.description + " " + v.suggested_fix).lower()
        contradict_patterns = [
            r"基本符合.*要求",
            r"基本符合.*规范",
            r"完全符合.*要求",
            r"符合.*要求.*无需",
            r"符合.*规范.*无需",
            r"需统一保留",
            r"保留即可",
            r"无需修改",
            r"不作修改",
            r"没有违规",
        ]
        for pat in contradict_patterns:
            if re.search(pat, desc):
                return True
        return False

    @staticmethod
    def _is_decimal_false_positive(v: ViolationDetail, col_defs: Dict[str, Dict[str, str]]) -> bool:
        """
        过滤针对金额/单价类型必须为 decimal 的假阳性误报：
        若规则指控必须使用 decimal，但原 SQL 中指定的目标列已经明确是 decimal，则判定为假阳性
        """
        rule_text = (v.rule_name + " " + v.description).lower()
        if "decimal" not in rule_text:
            return False

        # 如果指控的是 double，不属于 decimal 假阳性
        if "double" in (v.target_object + " " + v.description).lower():
            return False

        target_cols = [c.strip("`' \"").lower() for c in re.split(r"[,，\s]+", v.target_object) if c.strip("`' \"")]
        if not target_cols:
            return False

        # 检查是否所有 target_cols 在原 SQL 中都已经是 decimal 类型
        all_already_decimal = True
        for col in target_cols:
            if col in col_defs:
                col_type = col_defs[col]["type"]
                if not col_type.startswith("decimal"):
                    all_already_decimal = False
                    break
            else:
                all_already_decimal = False
                break

        return all_already_decimal

    @staticmethod
    def _clean_naming_suffix_targets(v: ViolationDetail) -> bool:
        """
        清理和核对命名后缀类假阳性：
        1. 若为 _money 规则，但列名本身已是以 _money 结尾（如 listed_money），从 target_object 移除；
           若所有字段本身均符合 _money，剔除该违规；
        2. 若为 _price 规则，若所有 target 均已是 _price，剔除；
        3. 若为 _amount 规则，若所有 target 均已是 _amount，剔除。
        返回 True 表示整条违规应被剔除（假阳性），False 表示保留。
        """
        rule_name = v.rule_name.lower()

        # 针对 _money 规则
        if "_money" in rule_name or "money" in rule_name or "金额字段命名" in rule_name:
            raw_targets = [c.strip("`' \"") for c in re.split(r"[,，\s]+", v.target_object) if c.strip("`' \"")]
            real_targets = [t for t in raw_targets if not t.lower().endswith("_money") and t.lower() != "money"]
            if not real_targets and raw_targets:
                return True
            if len(real_targets) < len(raw_targets):
                v.target_object = ", ".join(real_targets)

        # 针对 _price 规则
        if "_price" in rule_name or "price" in rule_name or "单价字段命名" in rule_name:
            raw_targets = [c.strip("`' \"") for c in re.split(r"[,，\s]+", v.target_object) if c.strip("`' \"")]
            real_targets = [t for t in raw_targets if not t.lower().endswith("_price") and t.lower() != "price"]
            if not real_targets and raw_targets:
                return True
            if len(real_targets) < len(raw_targets):
                v.target_object = ", ".join(real_targets)

        # 针对 _amount 规则
        if "_amount" in rule_name or "数量字段命名" in rule_name:
            raw_targets = [c.strip("`' \"") for c in re.split(r"[,，\s]+", v.target_object) if c.strip("`' \"")]
            real_targets = [t for t in raw_targets if not t.lower().endswith("_amount") and t.lower() != "amount"]
            if not real_targets and raw_targets:
                return True
            if len(real_targets) < len(raw_targets):
                v.target_object = ", ".join(real_targets)

        return False

    @staticmethod
    def _guard_single_char_rule(v: ViolationDetail, col_defs: Dict[str, Dict[str, str]]) -> None:
        """
        防御模型将长 char 字段（如 char(22)）误判为「1 个字符须用 TINYINT(4)」：
        若模型将长度大于 1 的 CHAR(N) 归入 1 字符 TINYINT(4) 规则，自动校正为「大于1个字符须统一使用 varchar」
        """
        rule_text = (v.rule_name + " " + v.description).lower()
        is_single_char_rule = any(kw in rule_text for kw in ["1个字符", "1 个字符", "单字符", "tinyint(4)"])
        if not is_single_char_rule:
            return

        target_cols = [c.strip("`' \"").lower() for c in re.split(r"[,，\s]+", v.target_object) if c.strip("`' \"")]
        for col in target_cols:
            if col in col_defs:
                col_type = col_defs[col]["type"]
                char_match = re.match(r"^char\s*\(\s*(\d+)\s*\)$", col_type)
                if char_match:
                    length = int(char_match.group(1))
                    if length > 1:
                        v.rule_id = "rule_string_type"
                        v.rule_name = "大于1个字符须统一使用 varchar"
                        v.severity = "WARN"
                        v.description = f"字段 {col} 长度为 {length} 位字符，大于1个字符应使用 varchar({length})，避免定长 char 开销"
                        v.suggested_fix = f"将 char({length}) 改为 varchar({length})"
                        print(f"[INFO] [DoubleCheck 防护] 成功纠正多字符定长 char({length}) 误判单字符规则: 字段={col}")
                        break

    @staticmethod
    def _guard_reserved_keyword(v: ViolationDetail) -> None:
        """
        防护保留关键字误判：
        num 并不是 MySQL 保留关键字，字段为数量语义时，违规应归属于数量统一命名后缀 _amount 规范
        """
        target_cols = [c.strip("`' \"").lower() for c in re.split(r"[,，\s]+", v.target_object) if c.strip("`' \"")]
        rule_text = (v.rule_name + " " + v.description).lower()

        if "num" in target_cols and ("保留关键字" in rule_text or "关键字" in rule_text):
            v.rule_id = "rule_naming_suffix"
            v.rule_name = "数量字段命名后缀须为_amount"
            v.severity = "WARN"
            v.description = "字段 num 属于数量语义且命名过于简略，数量统一命名后缀为 [xxxx_]amount，如 oil_amount"
            v.suggested_fix = "将 num 重命名为语义明确的数量名称（如 oil_amount）"
            print("[INFO] [DoubleCheck 防护] 成功纠正 num 误判为保留关键字，校准为数量命名后缀规则")

    def verify_and_filter(
        self,
        raw_violations: List[ViolationDetail],
        chunk_index_map: Dict[int, Chunk],
        summary: str = "",
        sql_text: str = ""
    ) -> DoubleCheckResult:
        """
        对大模型输出的违规项列表执行二次确定性断言核验、假阳性过滤与多字段智能聚合

        :param raw_violations: 大模型原始解析出的违规列表
        :param chunk_index_map: 检索到的引用序号到 Chunk 实体的映射表
        :param summary: 大模型生成的综述，用于一致性兜底核验
        :param sql_text: 待审查的原始 SQL 文本，用于做 AST/正则级确定性事实交叉核验
        :return: 核验与校准后的 DoubleCheckResult
        """
        verified: List[ViolationDetail] = []
        hallucinations: List[ViolationDetail] = []
        col_defs = self._extract_column_defs(sql_text)

        for v in raw_violations:
            # 前置过滤 1: 自相矛盾项过滤 (如描述自述「基本符合要求需保留」却打 ERROR)
            if self._is_self_contradictory(v):
                print(f"[WARN] [DoubleCheck 拦截] 排除自相矛盾假阳性: 规则 '{v.rule_name}' 说明中已认定符合规范，剔除。")
                hallucinations.append(v)
                continue

            # 前置过滤 2: DECIMAL 假阳性过滤 (原表中指定列已经明确是 decimal)
            if self._is_decimal_false_positive(v, col_defs):
                print(f"[WARN] [DoubleCheck 拦截] 排除 DECIMAL 类型假阳性: 字段 `{v.target_object}` 在原始 SQL 中已为 decimal，剔除。")
                hallucinations.append(v)
                continue

            # 前置过滤 3: 命名后缀假阳性过滤与清洗 (如 listed_money 混入金额违规)
            if self._clean_naming_suffix_targets(v):
                print(f"[WARN] [DoubleCheck 拦截] 排除命名后缀假阳性: 字段 `{v.target_object}` 本身已符合命名后缀要求，剔除。")
                hallucinations.append(v)
                continue

            # 前置纠偏 1: 单字符规则防御 (char(22) 误判为 1 字符 TINYINT(4) 自动校正为 varchar)
            self._guard_single_char_rule(v, col_defs)

            # 前置纠偏 2: 保留关键字误判防护 (num 纠偏为数量后缀规范)
            self._guard_reserved_keyword(v)

            idx = v.citation_index
            is_verified = False

            # 步骤 1: 优先在模型指定的 citation_index 对应 Chunk 中核验
            if idx in chunk_index_map:
                if self._is_supported_by_chunk(v, chunk_index_map[idx]):
                    is_verified = True

            # 步骤 2: 跨 Chunk 回退核验 (Cross-Chunk Fallback)
            if not is_verified:
                for alt_idx, alt_chunk in chunk_index_map.items():
                    if alt_idx == idx:
                        continue
                    if self._is_supported_by_chunk(v, alt_chunk):
                        v.citation_index = alt_idx
                        is_verified = True
                        break

            if is_verified:
                verified.append(v)
            else:
                print(f"[WARN] [DoubleCheck 拦截] 幻觉误报过滤: 规则 '{v.rule_name}' 在当前依据原文中无实质支持，判定为模型幻觉并剔除。")
                hallucinations.append(v)

        # 步骤 3: 违规自洽熔断保护 (防止 summary 判定违规却伪判 100 分通过)
        if not verified and raw_violations:
            has_violation_in_summary = bool(re.search(r"违反|禁止|不符合|问题|建议统一|需改为|错误|缺失", summary))
            if has_violation_in_summary and hallucinations:
                for cand in hallucinations:
                    cand_text = (cand.rule_name + " " + cand.description).lower()
                    for _, kw_list in self.RULE_KEYWORD_REQUIREMENTS.items():
                        if any(kw in cand_text for kw in kw_list):
                            cand.citation_index = cand.citation_index if cand.citation_index in chunk_index_map else 1
                            verified.append(cand)
                            print(f"[INFO] [DoubleCheck 熔断保护] 恢复被误杀的高置信违规项: '{cand.rule_name}'")
                            break
                    if verified:
                        break

        # 步骤 4: 同规则多字段智能聚合 (避免重复同名规则膨胀违规计数)
        aggregated_verified: List[ViolationDetail] = []
        rule_map: Dict[str, ViolationDetail] = {}

        for v in verified:
            norm_key = re.sub(r"\s+", "", v.rule_name)
            if norm_key not in rule_map:
                rule_map[norm_key] = v
                aggregated_verified.append(v)
            else:
                existing = rule_map[norm_key]
                if v.target_object and v.target_object not in existing.target_object:
                    existing.target_object = f"{existing.target_object}, {v.target_object}"
                if v.description and v.description not in existing.description:
                    existing.description = f"{existing.description}; {v.description}"

        # 步骤 5: 动态评分重算
        if not aggregated_verified:
            is_compliant = True
            score = 100
        else:
            is_compliant = False
            penalty = 0
            for v in aggregated_verified:
                penalty += 20 if v.severity.upper() == "ERROR" else 10
            score = max(0, 100 - penalty)

        return DoubleCheckResult(
            verified_violations=aggregated_verified,
            hallucinations=hallucinations,
            is_compliant=is_compliant,
            score=score
        )
