"""
字段命名规范规则 (lower_snake_case 与禁止保留关键字)
"""

import re
from typing import List
from app.models.dto.sql_rule import SqlRuleViolation
from app.services.sql_rule.base_rule import BaseSqlRule
from app.services.sql_rule.constants import MYSQL_RESERVED_WORDS
from app.services.sql_rule.parser import ParsedStatementContext

# lower_snake_case: 小写字母开头，由小写字母、数字和下划线组成，不以下划线结尾
SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


class ColumnNamingRule(BaseSqlRule):
    """
    字段校验:
    1. 检查字段是否都采用 lower_snake_case 命名法
    2. 字段名不允许用关键字
    """
    rule_id = "RULE_COLUMN_NAMING"
    rule_name = "字段命名规范"
    severity = "ERROR"
    category = "naming_rule"

    def validate(self, ctx: ParsedStatementContext) -> List[SqlRuleViolation]:
        if ctx.statement_type not in ("CREATE_TABLE", "ALTER_TABLE"):
            return []

        violations: List[SqlRuleViolation] = []

        # 收集需校验的列
        cols_to_check = list(ctx.columns)
        for action in ctx.alter_actions:
            if action.column_info:
                cols_to_check.append(action.column_info)

        for col in cols_to_check:
            col_name = col.name
            col_name_lower = col_name.lower()

            # 1. 检查 lower_snake_case 命名法
            if not SNAKE_CASE_PATTERN.match(col_name):
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=col_name,
                        message=f"字段 '{col_name}' 未遵循 lower_snake_case 命名规范 (仅允许小写字母、数字和下划线)",
                        suggested_fix=f"将字段改名为规范的下划线小写格式，如: {self._to_snake_case(col_name)}",
                        rule_id_override="RULE_COL_SNAKE_CASE",
                        rule_name_override="字段必须采用 lower_snake_case 命名法"
                    )
                )

            # 2. 字段名不允许用关键字
            if col_name_lower in MYSQL_RESERVED_WORDS:
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=col_name,
                        message=f"字段名 '{col_name}' 命中了 MySQL 保留关键字",
                        suggested_fix=f"更换为非关键字业务名称，如: {col_name}_item 或业务修饰词",
                        rule_id_override="RULE_COL_KEYWORD",
                        rule_name_override="字段名禁止使用保留关键字"
                    )
                )

        return violations

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """驼峰转下划线辅助提示"""
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        return re.sub(r"[^a-z0-9_]+", "_", s2).strip("_")
