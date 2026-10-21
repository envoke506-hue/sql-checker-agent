"""
SQL 静态规则引擎 (SqlRuleEngine)
负责多语句解析调度、规则集执行与违规报告聚合
"""

from typing import List
from app.models.dto.sql_rule import (
    SqlRuleViolation,
    SqlValidateResponseData,
    StatementRuleResult,
)
from app.services.sql_rule.aggregator import RuleViolationAggregator
from app.services.sql_rule.base_rule import BaseSqlRule
from app.services.sql_rule.parser import ParsedStatementContext, SqlAstParser
from app.services.sql_rule.rules import (
    AlterTableAfterRule,
    BaseTemplateRule,
    ColumnNamingRule,
    ColumnTypeRule,
    ProhibitedObjectsRule,
    SchemaPrefixRule,
    SemanticNamingRule,
    TableMetaRule,
)


class SqlRuleEngine:
    """SQL 规范校验引擎"""

    def __init__(self, rules: List[BaseSqlRule] = None):
        if rules is not None:
            self.rules = rules
        else:
            # 默认注册全量规则体系 (第一阶段语法与结构硬规范 + 第二阶段语义与命名规范)
            self.rules = [
                SchemaPrefixRule(),
                TableMetaRule(),
                ColumnNamingRule(),
                ColumnTypeRule(),
                BaseTemplateRule(),
                ProhibitedObjectsRule(),
                AlterTableAfterRule(),
                SemanticNamingRule(),
            ]

    def validate(self, sql_text: str) -> SqlValidateResponseData:
        """
        对输入的单条或由分号分隔的多条 SQL 执行全量规范校验
        """
        contexts: List[ParsedStatementContext] = SqlAstParser.parse_sql(sql_text)
        if not contexts:
            return SqlValidateResponseData(
                is_compliant=True,
                total_statements=0,
                total_violations=0,
                error_count=0,
                warn_count=0,
                results=[]
            )

        statement_results: List[StatementRuleResult] = []
        total_errors = 0
        total_warns = 0

        for ctx in contexts:
            # 处理语法解析报错
            if ctx.statement_type == "PARSE_ERROR":
                parse_violation = SqlRuleViolation(
                    rule_id="RULE_SYNTAX_ERROR",
                    rule_name="SQL 语法错误",
                    severity="ERROR",
                    target_object="SQL 语句",
                    message=f"SQL 无法解析，存在语法错误: {ctx.parse_error}",
                    suggested_fix="请检查 SQL 语法是否符合标准 MySQL 规范",
                    statement_index=ctx.index
                )
                statement_results.append(
                    StatementRuleResult(
                        index=ctx.index,
                        statement_type="PARSE_ERROR",
                        target_table=None,
                        is_compliant=False,
                        violations=[parse_violation]
                    )
                )
                total_errors += 1
                continue

            # 执行规则链
            stmt_violations: List[SqlRuleViolation] = []
            for rule in self.rules:
                try:
                    res = rule.validate(ctx)
                    if res:
                        stmt_violations.extend(res)
                except Exception as e:
                    # 单条规则内部异常兜底保护
                    stmt_violations.append(
                        SqlRuleViolation(
                            rule_id=f"{rule.rule_id}_EXEC_ERROR",
                            rule_name=rule.rule_name,
                            severity="ERROR",
                            target_object="RULE_ENGINE",
                            message=f"规则执行异常: {str(e)}",
                            suggested_fix="请联系系统管理员排查",
                            statement_index=ctx.index
                        )
                    )

            # 执行单规则多字段降噪聚合
            final_violations = RuleViolationAggregator.aggregate(stmt_violations)

            # 统计严重度
            stmt_errors = sum(1 for v in final_violations if v.severity == "ERROR")
            stmt_warns = sum(1 for v in final_violations if v.severity == "WARN")
            total_errors += stmt_errors
            total_warns += stmt_warns

            main_target = ctx.main_table.full_name if ctx.main_table else (
                ctx.all_tables[0].full_name if ctx.all_tables else None
            )

            statement_results.append(
                StatementRuleResult(
                    index=ctx.index,
                    statement_type=ctx.statement_type,
                    target_table=main_target,
                    is_compliant=(stmt_errors == 0),
                    violations=final_violations
                )
            )

        total_violations = total_errors + total_warns
        return SqlValidateResponseData(
            is_compliant=(total_errors == 0),
            total_statements=len(contexts),
            total_violations=total_violations,
            error_count=total_errors,
            warn_count=total_warns,
            results=statement_results
        )
