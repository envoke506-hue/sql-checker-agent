"""
SQL 规范规则抽象基类
"""

from abc import ABC, abstractmethod
from typing import List
from app.models.dto.sql_rule import SqlRuleViolation
from app.services.sql_rule.parser import ParsedStatementContext


class BaseSqlRule(ABC):
    """SQL 规范校验规则抽象基类"""

    rule_id: str
    rule_name: str
    severity: str = "ERROR"
    category: str = "database_rule"

    @abstractmethod
    def validate(self, ctx: ParsedStatementContext) -> List[SqlRuleViolation]:
        """
        对单条 SQL 语句执行规范断言校验
        :param ctx: 单条语句的 AST 解析上下文
        :return: 违规详情列表
        """
        pass

    def create_violation(
        self,
        ctx: ParsedStatementContext,
        target_object: str,
        message: str,
        suggested_fix: str,
        severity: str = None,
        category: str = None,
        rule_id_override: str = None,
        rule_name_override: str = None
    ) -> SqlRuleViolation:
        """快速构建结构化违规项实体"""
        return SqlRuleViolation(
            rule_id=rule_id_override or self.rule_id,
            rule_name=rule_name_override or self.rule_name,
            severity=severity or self.severity,
            category=category or self.category,
            target_object=target_object,
            message=message,
            suggested_fix=suggested_fix,
            statement_index=ctx.index
        )
