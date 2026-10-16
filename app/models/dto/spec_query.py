"""
规范知识问答领域 DTO (Specification Query DTO)
"""

from typing import List
from pydantic import BaseModel, Field
from app.models.dto.sql_audit import CitationDetail


class SpecQueryRequest(BaseModel):
    """
    规范问答检索请求参数
    """
    question: str = Field(
        ...,
        min_length=2,
        description="用户关于数据库规范的自然语言提问",
        examples=["金额和单价字段有什么命名规范？"]
    )
    history: List[dict] = Field(
        default_factory=list,
        description="多轮对话历史记录，每项格式为 {'role': 'user'|'assistant', 'content': '...'}"
    )


class SpecQueryResponseData(BaseModel):
    """
    规范问答业务响应结果
    """
    answer: str = Field(..., description="依据规范库生成的纯文本答案 (带 [1] 等角标)")
    citations: List[CitationDetail] = Field(default_factory=list, description="答案引用的规范条款详情")
    markdown_content: str = Field(..., description="排版完善的标准 Markdown 问答结果")
