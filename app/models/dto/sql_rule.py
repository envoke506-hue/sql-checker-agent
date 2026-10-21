"""
SQL 静态规则校验与审计 DTO 模型定义
遵循 RESTful API 设计标准
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SqlRuleViolation(BaseModel):
    """单条规范违规项"""
    rule_id: str = Field(..., description="规范规则唯一编码，如 RULE_SCHEMA_PREFIX")
    rule_name: str = Field(..., description="规范规则名称")
    severity: str = Field(default="ERROR", description="违规级别: ERROR(阻断) / WARN(建议)")
    category: str = Field(default="database_rule", description="规范依据分类: database_rule, sql_template, naming_rule, glossary")
    target_object: str = Field(default="", description="违规目标对象，如表名、字段名或语句")
    message: str = Field(..., description="违规详细说明")
    suggested_fix: str = Field(default="", description="落地的修复建议")
    statement_index: int = Field(default=1, description="所属 SQL 语句在多语句批次中的序号(从1开始)")


class StatementRuleResult(BaseModel):
    """单条 SQL 语句的校验结果"""
    index: int = Field(..., description="语句在批次中的序号(从1开始)")
    statement_type: str = Field(..., description="语句类型: CREATE_TABLE, ALTER_TABLE, INSERT, UPDATE, DELETE, SELECT, OTHER")
    target_table: Optional[str] = Field(default=None, description="操作的主表名(包含库名)")
    is_compliant: bool = Field(..., description="本条语句是否完全合规")
    violations: List[SqlRuleViolation] = Field(default_factory=list, description="本条语句检测出的违规列表")


class SqlValidateRequest(BaseModel):
    """SQL 规则校验请求参数"""
    sql_text: str = Field(..., min_length=1, description="待校验的单条或由分号分隔的多条 SQL 文本")


class SqlValidateResponseData(BaseModel):
    """SQL 规则校验响应主体数据"""
    is_compliant: bool = Field(..., description="整体是否完全合规(无任何 ERROR 级违规)")
    total_statements: int = Field(..., description="解析出的 SQL 语句总数")
    total_violations: int = Field(..., description="违规项总数(包含 ERROR 和 WARN)")
    error_count: int = Field(..., description="ERROR 阻断级违规数量")
    warn_count: int = Field(..., description="WARN 建议级违规数量")
    results: List[StatementRuleResult] = Field(default_factory=list, description="逐条语句的详细结果")
