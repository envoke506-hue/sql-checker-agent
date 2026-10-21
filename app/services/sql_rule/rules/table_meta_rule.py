"""
建表元数据规范规则 (表名关键字、字符集 utf8mb4、InnoDB 引擎)
"""

from typing import List
from app.models.dto.sql_rule import SqlRuleViolation
from app.services.sql_rule.base_rule import BaseSqlRule
from app.services.sql_rule.constants import MYSQL_RESERVED_WORDS
from app.services.sql_rule.parser import ParsedStatementContext


class TableMetaRule(BaseSqlRule):
    """
    建表模板校验:
    1. 表名不能使用关键字
    2. 建表指定字符集为: utf8mb4
    3. 建表必须使用 innodb 引擎
    """
    rule_id = "RULE_TABLE_META"
    rule_name = "建表元数据规范"
    severity = "ERROR"

    def validate(self, ctx: ParsedStatementContext) -> List[SqlRuleViolation]:
        if ctx.statement_type != "CREATE_TABLE" or not ctx.main_table:
            return []

        violations: List[SqlRuleViolation] = []
        table_name = ctx.main_table.name.lower()

        # 1. 表名不能使用关键字
        if table_name in MYSQL_RESERVED_WORDS:
            violations.append(
                self.create_violation(
                    ctx=ctx,
                    target_object=ctx.main_table.full_name,
                    message=f"表名 '{table_name}' 命中了 MySQL 保留关键字",
                    suggested_fix=f"请修改表名，避免使用保留字 '{table_name}'",
                    rule_id_override="RULE_TABLE_KEYWORD",
                    rule_name_override="表名禁止使用保留关键字"
                )
            )

        # 2. 建表必须使用 innodb 引擎
        if not ctx.engine:
            violations.append(
                self.create_violation(
                    ctx=ctx,
                    target_object=ctx.main_table.full_name,
                    message="建表语句缺少存储引擎声明，必须显式指定 ENGINE=InnoDB",
                    suggested_fix="在语句末尾追加 ENGINE=InnoDB",
                    rule_id_override="RULE_TABLE_ENGINE",
                    rule_name_override="建表必须使用 InnoDB 引擎"
                )
            )
        elif ctx.engine != "innodb":
            violations.append(
                self.create_violation(
                    ctx=ctx,
                    target_object=ctx.main_table.full_name,
                    message=f"存储引擎必须为 InnoDB，当前声明为: '{ctx.engine}'",
                    suggested_fix="修改为 ENGINE=InnoDB",
                    rule_id_override="RULE_TABLE_ENGINE",
                    rule_name_override="建表必须使用 InnoDB 引擎"
                )
            )

        # 3. 建表指定字符集为: utf8mb4
        if not ctx.charset:
            violations.append(
                self.create_violation(
                    ctx=ctx,
                    target_object=ctx.main_table.full_name,
                    message="建表语句缺少字符集声明，必须显式指定 DEFAULT CHARSET=utf8mb4",
                    suggested_fix="在语句末尾追加 DEFAULT CHARSET=utf8mb4",
                    rule_id_override="RULE_TABLE_CHARSET",
                    rule_name_override="建表必须指定字符集为 utf8mb4"
                )
            )
        elif ctx.charset != "utf8mb4":
            violations.append(
                self.create_violation(
                    ctx=ctx,
                    target_object=ctx.main_table.full_name,
                    message=f"字符集必须指定为 utf8mb4，当前声明为: '{ctx.charset}'",
                    suggested_fix="修改为 DEFAULT CHARSET=utf8mb4",
                    rule_id_override="RULE_TABLE_CHARSET",
                    rule_name_override="建表必须指定字符集为 utf8mb4"
                )
            )

        return violations
