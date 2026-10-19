"""
通用基础 DTO 与错误码枚举 (Common DTO)

【框架知识点说明】
1. 枚举类 (Enum / IntEnum):
   - 生产环境中严禁裸写魔法数字（如到处写 200, 500, 40001）。
   - 使用 IntEnum 统一管理业务错误码，具备类型安全与自动补全支持。
2. 泛型响应实体 Generic[T]:
   - 保证前后端数据通信契约绝对标准化，所有成功的响应都遵循 {code, message, data}。
"""

from enum import IntEnum
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorCode(IntEnum):
    """
    企业级统一业务错误码枚举规范
    - 200xx: 成功
    - 400xx: 客户端请求参数/语法错误
    - 404xx: 资源或知识库未找到
    - 422xx: 数据校验非法
    - 500xx: 系统与外部模型故障
    """
    SUCCESS = 20000                     # 操作成功
    BAD_REQUEST = 40001                 # 请求语法错误
    INVALID_SQL_SYNTAX = 40002          # 待审查 SQL 存在基础语法错误
    VALIDATION_ERROR = 42201            # 入参字段校验未通过
    SPEC_NOT_FOUND = 40401              # 规范文件或知识库条目未找到
    INTERNAL_SERVER_ERROR = 50000       # 服务器未知内部异常
    OLLAMA_SERVICE_ERROR = 50001        # 本地 Ollama 向量模型通信异常
    RELAY_LLM_API_ERROR = 50002         # 云端中转站大模型调用异常
    MODEL_TIMEOUT_ERROR = 50003         # 大模型推理超时
    VECTOR_STORE_ERROR = 50004          # 向量数据库存储或检索异常


class ApiResponse(BaseModel, Generic[T]):
    """
    RESTful 统一接口响应规范结构 (类似 Java 的 Result<T>)
    所有接口均返回该格式，便于前端与客户端统一拦截与解析
    """
    code: int = Field(default=ErrorCode.SUCCESS, description="业务状态码，20000 表示成功，非 20000 表示具体业务异常")
    message: str = Field(default="success", description="状态提示信息")
    data: Optional[T] = Field(default=None, description="具体的业务数据载荷")
