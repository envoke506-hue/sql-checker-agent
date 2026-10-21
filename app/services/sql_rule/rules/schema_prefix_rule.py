"""
库名前缀必须为 db_ 规范规则 (DDL + DML 通用)
"""

from typing import List, Set
from app.models.dto.sql_rule import SqlRuleViolation
from app.services.sql_rule.base_rule import BaseSqlRule
from app.services.sql_rule.parser import ParsedStatementContext


class SchemaPrefixRule(BaseSqlRule):
    """
    DDL 和 DML 语句必须有库名前缀，库前缀必须为：db_
    """
    rule_id = "RULE_SCHEMA_PREFIX"
    rule_name = "库名前缀必须为 db_"
    severity = "ERROR"

    def validate(self, ctx: ParsedStatementContext) -> List[SqlRuleViolation]:
        violations: List[SqlRuleViolation] = []
        checked_tables: Set[str] = set()

        for table in ctx.all_tables:
            table_key = f"{table.db}.{table.name}"
            if table_key in checked_tables:
                continue
            checked_tables.add(table_key)

            # 1. 检查是否显式声明了库名
            if not table.db:
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=table.name,
                        message=f"表 '{table.name}' 必须显式声明数据库名，且库前缀必须为 'db_'",
                        suggested_fix=f"显式指定库名，格式如: db_xxx.{table.name}"
                    )
                )
            # 2. 检查库名是否以 db_ 开头
            elif not table.db.lower().startswith("db_"):
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=table.full_name,
                        message=f"数据库名 '{table.db}' 必须以 'db_' 开头，当前为: '{table.db}'",
                        suggested_fix=f"将库名规范化为以 'db_' 开头，如: db_{table.db}.{table.name}"
                    )
                )

        return violations
