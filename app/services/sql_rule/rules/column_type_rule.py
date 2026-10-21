"""
字段数据类型与精度规范规则
"""

from typing import List
from app.models.dto.sql_rule import SqlRuleViolation
from app.services.sql_rule.base_rule import BaseSqlRule
from app.services.sql_rule.parser import ParsedStatementContext


class ColumnTypeRule(BaseSqlRule):
    """
    字段类型与精度校验:
    1. 字段不可使用 double、float 类型
    2. 对于 TINYINT 类型，统一使用 TINYINT(4)
    3. 对应 decimal 类型，判断精度是否为 decimal(20,6)
    4. 字段不要写: CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
    """
    rule_id = "RULE_COLUMN_TYPE"
    rule_name = "字段类型与精度规范"
    severity = "ERROR"

    def validate(self, ctx: ParsedStatementContext) -> List[SqlRuleViolation]:
        if ctx.statement_type not in ("CREATE_TABLE", "ALTER_TABLE"):
            return []

        violations: List[SqlRuleViolation] = []

        cols_to_check = list(ctx.columns)
        for action in ctx.alter_actions:
            if action.column_info:
                cols_to_check.append(action.column_info)

        for col in cols_to_check:
            base_type = col.base_type
            col_name = col.name

            # 1. 字段不可使用 double、float 类型
            if base_type in ("DOUBLE", "FLOAT"):
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=f"{col_name} {base_type}",
                        message=f"字段 '{col_name}' 使用了禁用的浮点类型 {base_type}，存在精度丢失风险",
                        suggested_fix=f"将字段类型修改为 DECIMAL(20, 6)",
                        rule_id_override="RULE_NO_FLOAT_DOUBLE",
                        rule_name_override="禁止使用 float/double 浮点类型"
                    )
                )

            # 2. 对于 TINYINT 类型，统一使用 TINYINT(4)
            if base_type == "TINYINT":
                # 检查参数是否显式且为 4
                if not col.type_args or col.type_args != ["4"]:
                    actual_type = f"TINYINT({','.join(col.type_args)})" if col.type_args else "TINYINT"
                    violations.append(
                        self.create_violation(
                            ctx=ctx,
                            target_object=f"{col_name} {actual_type}",
                            message=f"对于 TINYINT 类型，必须统一使用 TINYINT(4)，当前为: {actual_type}",
                            suggested_fix="修改为 TINYINT(4)",
                            rule_id_override="RULE_TINYINT_4",
                            rule_name_override="TINYINT 类型统一使用 TINYINT(4)"
                        )
                    )

            # 3. 对应 decimal 类型，判断精度是否为 decimal(20,6)
            if base_type in ("DECIMAL", "DEC", "NUMERIC"):
                if col.type_args != ["20", "6"]:
                    actual_dec = f"DECIMAL({','.join(col.type_args)})" if col.type_args else "DECIMAL"
                    violations.append(
                        self.create_violation(
                            ctx=ctx,
                            target_object=f"{col_name} {actual_dec}",
                            message=f"DECIMAL 类型精度必须为 DECIMAL(20, 6)，当前为: {actual_dec}",
                            suggested_fix="修改为 DECIMAL(20, 6)",
                            rule_id_override="RULE_DECIMAL_PRECISION",
                            rule_name_override="DECIMAL 精度必须为 (20, 6)"
                        )
                    )

            # 4. 字段不要写 CHARACTER SET / COLLATE
            if col.has_collate_or_charset:
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=col_name,
                        message=f"字段 '{col_name}' 显式指定了字符集或排序规则 (如 CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci)",
                        suggested_fix="移除字段上的字符集与排序规则声明，统一继承表级 DEFAULT CHARSET=utf8mb4",
                        rule_id_override="RULE_NO_FIELD_CHARSET",
                        rule_name_override="字段不要手写字符集与排序规则"
                    )
                )

        return violations
