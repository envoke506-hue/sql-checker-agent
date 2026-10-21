"""
ALTER TABLE 增加字段标注 AFTER 规范规则
"""

from typing import List
from app.models.dto.sql_rule import SqlRuleViolation
from app.services.sql_rule.base_rule import BaseSqlRule
from app.services.sql_rule.parser import ParsedStatementContext


class AlterTableAfterRule(BaseSqlRule):
    """
    指定表增加字段校验:
    DDL 增加字段必须标注 AFTER 指定其所在位置
    """
    rule_id = "RULE_ALTER_TABLE_AFTER"
    rule_name = "新增字段必须标注 AFTER"
    severity = "ERROR"

    def validate(self, ctx: ParsedStatementContext) -> List[SqlRuleViolation]:
        if ctx.statement_type != "ALTER_TABLE":
            return []

        violations: List[SqlRuleViolation] = []

        for action in ctx.alter_actions:
            if action.action_type == "ADD_COLUMN":
                if not action.has_after:
                    target_col = action.column_name or "ADD COLUMN"
                    violations.append(
                        self.create_violation(
                            ctx=ctx,
                            target_object=target_col,
                            message=f"DDL 增加字段 '{target_col}' 未标注 AFTER 明确其相对位置",
                            suggested_fix=f"在字段定义后追加 AFTER <现有字段名>"
                        )
                    )

        return violations
