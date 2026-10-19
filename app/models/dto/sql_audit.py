"""
SQL 规范合规审查领域 DTO (SQL Audit DTO)
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


class SqlAuditRequest(BaseModel):
    """
    SQL 审查请求参数实体
    """
    sql_text: str = Field(
        ...,
        min_length=5,
        description="待检查的 SQL 语句 (支持 DDL 建表或改表语句)",
        examples=["CREATE TABLE order (\n  order_id bigint,\n  price double\n);"]
    )
    db_type: str = Field(
        default="mysql",
        description="数据库类型，目前默认为 mysql"
    )
    user_roles: List[str] = Field(
        default=["all_staff"],
        description="发起请求的用户角色标签，用于 RAG 权限过滤 (ACL)"
    )


class ViolationDetail(BaseModel):
    """违规项详细说明"""
    rule_id: str = Field(..., description="命中的规范规则唯一标识")
    rule_name: str = Field(..., description="规则名称 (如 '禁止外键设计', '本表字段不加表名前缀')")
    severity: str = Field(default="ERROR", description="严重级别 (ERROR: 强制阻断 / WARN: 建议优化)")
    target_object: str = Field(..., description="违规的具体字段或语法片段 (如 'order_id', 'price double')")
    description: str = Field(..., description="具体违规原因分析")
    suggested_fix: str = Field(default="", description="建议的修改修复方案")
    citation_index: int = Field(..., description="对应的依据编号 [1], [2]...")

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: str) -> str:
        val = str(v).strip().upper()
        if val in ("WARN", "WARNING"):
            return "WARN"
        return "ERROR"


class CitationDetail(BaseModel):
    """规范依据引用明细"""
    index: int = Field(..., description="引用序号编号 (如 1, 2)")
    title: str = Field(..., description="引用的规范章节路径")
    snippet: str = Field(..., description="规范原文关键语句摘录")
    source_file: str = Field(default="数据库规范.md", description="来源规范文档名称")


class SqlAuditResponseData(BaseModel):
    """
    SQL 审查业务响应结果
    """
    is_compliant: bool = Field(..., description="是否完全符合规范 (True: 通过 / False: 存在违规)")
    score: int = Field(..., ge=0, le=100, description="合规健康评分 (0~100)")
    summary: str = Field(..., description="审查结果综述")
    violations: List[ViolationDetail] = Field(default_factory=list, description="检测到的违规条目列表")
    suggested_sql: str = Field(..., description="重构后符合团队规范的标准 SQL")
    citations: List[CitationDetail] = Field(default_factory=list, description="本次审查所依据的规范条目引用")
    markdown_report: str = Field(
        ...,
        description="精简 Markdown 整改回复: 不满足项 (含编号引用依据) + 整改方案 + 修改后的 SQL"
    )
