"""
SQL 规范违规聚合器 (Rule Violation Aggregator)
工业级降噪组件: 按规则维度自动聚合折叠同类多字段违规，杜绝单字段刷屏
"""

from collections import defaultdict
from typing import Dict, List
from app.models.dto.sql_rule import SqlRuleViolation


class RuleViolationAggregator:
    """违规项聚合器"""

    # 需要按规则聚合折叠的规则 ID 集合
    AGGREGATABLE_RULES = {
        "WARN_NOT_NULL_DEFAULT",
        "WARN_UNSIGNED_NUMBER",
        "RULE_NO_TABLE_PREFIX_IN_COLUMN",
        "RULE_TERMINOLOGY",
        "RULE_COL_SNAKE_CASE",
        "RULE_COL_KEYWORD",
        "RULE_NO_FLOAT_DOUBLE",
        "RULE_TINYINT_4",
        "RULE_DECIMAL_PRECISION",
        "RULE_NO_FIELD_CHARSET",
    }

    @classmethod
    def aggregate(cls, violations: List[SqlRuleViolation]) -> List[SqlRuleViolation]:
        """
        对单条 SQL 语句产出的违规项集合进行降噪聚合折叠
        """
        if not violations:
            return []

        grouped: Dict[str, List[SqlRuleViolation]] = defaultdict(list)
        result: List[SqlRuleViolation] = []

        for v in violations:
            if v.rule_id in cls.AGGREGATABLE_RULES:
                grouped[v.rule_id].append(v)
            else:
                result.append(v)

        # 对命中可聚合集合的规则进行结构化折叠
        for rule_id, items in grouped.items():
            if len(items) == 1:
                result.append(items[0])
                continue

            first = items[0]
            # 提取所有目标对象
            raw_targets = [it.target_object for it in items if it.target_object]
            unique_targets = []
            for t in raw_targets:
                if t not in unique_targets:
                    unique_targets.append(t)

            count = len(unique_targets)

            # 针对不同规则定制优雅的聚合文案
            if rule_id == "WARN_NOT_NULL_DEFAULT":
                # 显示前 8 个字段，超出的给出总计
                display_targets = ", ".join(unique_targets[:8])
                if count > 8:
                    target_summary = f"{display_targets} 等 (共 {count} 个字段)"
                else:
                    target_summary = f"{display_targets} (共 {count} 个字段)"

                aggregated = SqlRuleViolation(
                    rule_id=first.rule_id,
                    rule_name=first.rule_name,
                    severity=first.severity,
                    category=first.category,
                    target_object=target_summary,
                    message=f"表内共有 {count} 个字段未显式指定 NOT NULL 约束，建议尽量使用 NOT NULL 或 NOT NULL DEFAULT 避免存储与逻辑开销",
                    suggested_fix="建议在对应字段定义后追加 NOT NULL DEFAULT 默认值",
                    statement_index=first.statement_index
                )
                result.append(aggregated)

            elif rule_id == "WARN_UNSIGNED_NUMBER":
                target_summary = f"{', '.join(unique_targets)} (共 {count} 个字段)"
                aggregated = SqlRuleViolation(
                    rule_id=first.rule_id,
                    rule_name=first.rule_name,
                    severity=first.severity,
                    category=first.category,
                    target_object=target_summary,
                    message=f"表内共有 {count} 个数字字段在已知不存在负数的情况下建议添加 UNSIGNED",
                    suggested_fix="建议在对应字段类型后追加 UNSIGNED 修饰符",
                    statement_index=first.statement_index
                )
                result.append(aggregated)

            elif rule_id == "RULE_NO_TABLE_PREFIX_IN_COLUMN":
                # 聚合本表字段去前缀
                target_summary = ", ".join(unique_targets)
                # 收集所有修复建议
                fixes = []
                for it in items:
                    clean_fix = it.suggested_fix.replace("去掉表名前缀，直接命名为: ", "").strip()
                    fixes.append(clean_fix)
                fix_summary = f"分别改为: {', '.join(fixes)}"

                aggregated = SqlRuleViolation(
                    rule_id=first.rule_id,
                    rule_name=first.rule_name,
                    severity=first.severity,
                    category=first.category,
                    target_object=target_summary,
                    message=f"以下 {count} 个字段包含了本表表名前缀，违反'本表字段不加表名'规范",
                    suggested_fix=fix_summary,
                    statement_index=first.statement_index
                )
                result.append(aggregated)

            elif rule_id == "RULE_TERMINOLOGY":
                target_summary = ", ".join(unique_targets)
                fixes = []
                for it in items:
                    clean_fix = it.suggested_fix.replace("将字段改名为规范术语: ", "").strip()
                    fixes.append(clean_fix)

                aggregated = SqlRuleViolation(
                    rule_id=first.rule_id,
                    rule_name=first.rule_name,
                    severity=first.severity,
                    category=first.category,
                    target_object=target_summary,
                    message=f"以下 {count} 个字段中包含非标名词术语",
                    suggested_fix=f"分别改名为规范术语: {', '.join(fixes)}",
                    statement_index=first.statement_index
                )
                result.append(aggregated)

            else:
                # 通用聚合
                target_summary = f"{', '.join(unique_targets)} (共 {count} 项)"
                aggregated = SqlRuleViolation(
                    rule_id=first.rule_id,
                    rule_name=first.rule_name,
                    severity=first.severity,
                    category=first.category,
                    target_object=target_summary,
                    message=f"共有 {count} 处违反 '{first.rule_name}'",
                    suggested_fix=first.suggested_fix,
                    statement_index=first.statement_index
                )
                result.append(aggregated)

        return result
