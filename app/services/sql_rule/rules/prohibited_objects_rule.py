"""
禁止外键与高级数据库对象规范规则
"""

from typing import List
from app.models.dto.sql_rule import SqlRuleViolation
from app.services.sql_rule.base_rule import BaseSqlRule
from app.services.sql_rule.parser import ParsedStatementContext


class ProhibitedObjectsRule(BaseSqlRule):
    """
    禁令校验:
    1. 表内禁止外键设计 (FOREIGN KEY)
    2. 禁止触发器、存储过程、自定义函数
    """
    rule_id = "RULE_PROHIBITED_OBJECTS"
    rule_name = "禁止外键与高级数据库对象"
    severity = "ERROR"

    def validate(self, ctx: ParsedStatementContext) -> List[SqlRuleViolation]:
        violations: List[SqlRuleViolation] = []

        # 1. 禁止触发器、存储过程、自定义函数
        if ctx.statement_type == "PROHIBITED_OBJECT":
            violations.append(
                self.create_violation(
                    ctx=ctx,
                    target_object="TRIGGER / PROCEDURE / FUNCTION",
                    message="禁止在数据库中创建触发器、存储过程或自定义函数，业务逻辑必须在应用层实现",
                    suggested_fix="删除触发器/存储过程/函数定义，将计算与联动逻辑移至应用代码层",
                    rule_id_override="RULE_NO_TRIGGER_PROCEDURE",
                    rule_name_override="禁止使用触发器/存储过程/自定义函数"
                )
            )

        # 2. 表内禁止外键设计
        if ctx.has_foreign_key:
            violations.append(
                self.create_violation(
                    ctx=ctx,
                    target_object="FOREIGN KEY",
                    message="表内禁止外键设计 (FOREIGN KEY)，外键完整性关系必须由应用层业务逻辑保证",
                    suggested_fix="移除 FOREIGN KEY 与 REFERENCES 外键约束定义，如有需要可改建普通索引",
                    rule_id_override="RULE_NO_FOREIGN_KEY",
                    rule_name_override="表内禁止外键设计"
                )
            )

        return violations
