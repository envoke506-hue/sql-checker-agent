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
        "tinyint": ["tinyint", "语义分歧", "tinyint(4)"],
        "redundant_prefix": ["本表", "反例", "加表名", "order_id", "前缀"],
        "base_fields": ["基类", "基础", "create_time", "modify_time", "version", "deleted", "disabled", "模板"],
        "db_prefix": ["db_", "前缀", "数据库"],
        "reserved_keyword": ["关键字", "保留字", "命名"],
        "naming_suffix": ["price", "money", "amount", "time", "后缀", "命名规范"],
    }

    def verify_and_filter(
        self,
        raw_violations: List[ViolationDetail],
        chunk_index_map: Dict[int, Chunk]
    ) -> DoubleCheckResult:
        """
        对大模型输出的违规项列表执行二次确定性断言核验

        :param raw_violations: 大模型原始解析出的违规列表
        :param chunk_index_map: 检索到的引用序号到 Chunk 实体的映射表
        :return: 核验与校准后的 DoubleCheckResult
        """
        verified: List[ViolationDetail] = []
        hallucinations: List[ViolationDetail] = []

        for v in raw_violations:
            idx = v.citation_index

            # 校验 1: 序号边界有效性
            if idx not in chunk_index_map:
                print(f"[WARN] [DoubleCheck 拦截] 虚假引用序号: [{idx}] 不在检索上下文有效编号范围内 (有效范围: 1~{len(chunk_index_map)})")
                hallucinations.append(v)
                continue

            target_chunk = chunk_index_map[idx]
            chunk_content = (target_chunk.display_text + " " + target_chunk.metadata.heading_path).lower()

            # 校验 2: 违规对象或规则关键词是否在引用正文中得到佐证
            v_text = (v.rule_name + " " + v.description + " " + v.target_object).lower()

            # 检查是否有至少一个特征词命中被引用的规范原文
            is_verified = False

            # (1) 检查是否直接包含违规对象 (如 'double', 'order_id', 'db_')
            if v.target_object and v.target_object.lower() in chunk_content:
                is_verified = True

            # (2) 若未直接包含对象名，根据规则语义白名单检查关键词
            if not is_verified:
                for rule_key, keywords in self.RULE_KEYWORD_REQUIREMENTS.items():
                    # 如果违规描述中提到了该类违规
                    if any(kw.lower() in v_text for kw in keywords):
                        # 那么对应的 Chunk 原文也必须包含该类关键词
                        if any(kw.lower() in chunk_content for kw in keywords):
                            is_verified = True
                            break

            # (3) 兜底：如果规则名称在 Chunk 标题或正文中有明确提及
            if not is_verified:
                clean_rule_name = re.sub(r"[^\w\u4e00-\u9fa5]", "", v.rule_name.lower())
                if clean_rule_name and any(kw in chunk_content for kw in [clean_rule_name, v.rule_id.lower()]):
                    is_verified = True

            if is_verified:
                verified.append(v)
            else:
                print(f"[WARN] [DoubleCheck 拦截] 幻觉误报过滤: 规则 '{v.rule_name}' 在依据 [{idx}] 原文中无实质支持，判定为模型幻觉并剔除。")
                hallucinations.append(v)

        # 3. 动态评分重算
        if not verified:
            is_compliant = True
            score = 100
        else:
            is_compliant = False
            # 计算扣分：ERROR 每项扣 20 分，WARN 每项扣 10 分
            penalty = 0
            for v in verified:
                penalty += 20 if v.severity.upper() == "ERROR" else 10
            score = max(0, 100 - penalty)

        return DoubleCheckResult(
            verified_violations=verified,
            hallucinations=hallucinations,
            is_compliant=is_compliant,
            score=score
        )
