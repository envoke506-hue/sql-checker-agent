"""
企业级统一业务异常体系 (Core Exceptions)

【框架知识点说明】
1. 自定义业务异常 (Custom Business Exception):
   - 在现代企业级后端开发中，遇到业务逻辑错误（如“知识库找不到对应规范”、“大模型调用超时”），
     绝不应该粗暴抛出通用的 RuntimeError 或直接让程序崩溃。
   - 应该抛出继承自 `BusinessException` 的语义化异常，携带明确的业务错误码 (ErrorCode) 和面向用户的友好提示。
2. 与 HTTP 状态码的区别:
   - `status_code` 是 HTTP 协议层状态码（如 400, 404, 502）。
   - `code` 是应用程序的内部业务细分错误码（如 50001 代表 Ollama 挂了，50002 代表中转站挂了），便于前端精准感知并弹窗提示。
"""

from typing import Optional
from app.models.dto.common import ErrorCode


class BusinessException(Exception):
    """
    业务逻辑通用异常基类
    """

    def __init__(
        self,
        code: int = ErrorCode.BAD_REQUEST,
        message: str = "业务处理异常",
        status_code: int = 400,
        detail: Optional[str] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or message


class ModelServiceException(BusinessException):
    """大模型或向量计算服务异常 (Ollama / Relay API)"""

    def __init__(self, message: str = "大模型服务调用失败", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.RELAY_LLM_API_ERROR,
            message=message,
            status_code=502,  # Bad Gateway
            detail=detail
        )


class OllamaServiceException(BusinessException):
    """本地 Ollama 向量计算服务异常"""

    def __init__(self, message: str = "本地 Ollama 向量服务异常", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.OLLAMA_SERVICE_ERROR,
            message=message,
            status_code=503,  # Service Unavailable
            detail=detail
        )


class SpecNotFoundException(BusinessException):
    """规范文档或知识库不存在"""

    def __init__(self, message: str = "未找到对应的数据库规范文档", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.SPEC_NOT_FOUND,
            message=message,
            status_code=404,
            detail=detail
        )


class InvalidSqlException(BusinessException):
    """待审查 SQL 格式或语法严重非法"""

    def __init__(self, message: str = "输入的 SQL 语法或格式非法", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.INVALID_SQL_SYNTAX,
            message=message,
            status_code=400,
            detail=detail
        )
