"""
规范违规领域实体 (Violation Entity)
"""

from pydantic import BaseModel, Field


class RuleViolation(BaseModel):
    """内部流转的单项违规记录实体"""
    rule_id: str = Field(..., description="规范规则 ID")
    rule_name: str = Field(..., description="规范规则名称")
    severity: str = Field(default="ERROR", description="严重等级 ERROR / WARN")
    target_object: str = Field(..., description="违规目标对象字段或代码片段")
    description: str = Field(..., description="违规详细说明")
    suggested_fix: str = Field(..., description="修改建议")
    citation_index: int = Field(..., description="对应的依据序号")
