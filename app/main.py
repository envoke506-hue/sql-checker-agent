"""
SQL Checker Agent 应用程序核心主入口 (Application Main Entry - Enterprise Edition)

【企业级核心知识点深度说明】
1. 全局异常拦截器 (@app.exception_handler):
   - 自动截获参数校验失败 (422) 与自定义业务异常 (BusinessException)，包装为标准统一信封格式。
2. 启动期自动加载/构建知识库索引 (Lifespan Hook):
   - 在应用启动期间通过 `KnowledgeService.initialize_or_load()` 自动检查本地规范文件哈希。
   - 若索引已存在且源文件未变动，执行秒级反序列化加载至内存；若首次运行或文件改动，自动执行切块与 Ollama 向量计算。
3. 停机连接池释放闭环:
   - 调用 `close_async_client()` 优雅释放底层网络 Socket。
"""

import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import get_settings
from app.core.exceptions import BusinessException
from app.core.http_client import close_async_client
from app.controllers.health_controller import router as health_router
from app.controllers.sql_audit_controller import router as sql_audit_router
from app.controllers.spec_query_controller import router as spec_query_router
from app.controllers.knowledge_controller import router as knowledge_router
from app.controllers.web_controller import router as web_router
from app.models.dto.common import ApiResponse, ErrorCode
from app.services.health_service import HealthService
from app.services.knowledge_service import KnowledgeService

# 解决 Windows 控制台默认编码非 UTF-8 导致的打印乱码问题
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    FastAPI 异步生命周期上下文管理器
    """
    settings = get_settings()
    print("=" * 65)
    print(f"🚀 【{settings.app_name}】正在启动 (Enterprise Edition)...")
    print(f"📌 系统版本: {settings.app_version} | 运行环境: {settings.app_env}")
    print(f"🤖 本地 Ollama 向量端点: {settings.ollama_base_url} (模型: {settings.ollama_embedding_model})")
    print(f"🧠 中转站推理端点: {settings.relay_api_base_url} (模型: {settings.relay_llm_model})")
    print(f"📄 规范源文档路径: {settings.spec_doc_path}")
    print("=" * 65)

    # 1. 启动时执行一次基础连通性体检
    try:
        health_svc = HealthService()
        health_info = await health_svc.check_system_health()
        print("🔍 启动期依赖服务体检报告:")
        for svc in health_info.services:
            status_icon = "✅" if svc.status == "healthy" else "❌"
            latency = f"{svc.latency_ms}ms" if svc.latency_ms else "N/A"
            print(f"   {status_icon} [{svc.name}] 状态: {svc.status} | 耗时: {latency} | 信息: {svc.message}")
    except Exception as e:
        print(f"⚠️ 启动期体检提示: {e}")

    # 2. 启动期自动加载或增量构建规范知识库双路索引
    try:
        knowledge_svc = KnowledgeService()
        index_info = await knowledge_svc.initialize_or_load(force=False)
        print(f"📚 知识库索引就绪: 包含 {index_info.chunk_count} 个切块 | 向量维度: {index_info.dimension} | 更新时间: {index_info.last_updated}")
    except Exception as e:
        print(f"⚠️ 知识库索引加载提示: {e}")

    yield  # 应用正式对外提供 HTTP 服务

    # 3. 停机时优雅关闭全局异步 HTTP 客户端连接池
    await close_async_client()
    print("🛑 【SQL Checker Agent】异步连接池已释放，服务正常关闭。")


# 实例化 FastAPI 核心应用对象
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于 RAG 的智能 SQL 规范合规审查与数据库表设计知识库问答系统 (企业级规范版)",
    lifespan=app_lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 注册 CORS 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================================
# 企业级全局异常拦截器 (Global Exception Handlers)
# ========================================================

@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    """拦截自定义业务异常 (BusinessException)"""
    response_body = ApiResponse(
        code=exc.code,
        message=exc.message,
        data={"detail": exc.detail} if exc.detail != exc.message else None
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response_body.model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """拦截入参校验失败异常，格式化字段报错信息"""
    error_msgs = []
    for error in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "参数非法")
        error_msgs.append(f"字段 [{field_loc}]: {msg}")

    friendly_msg = " | ".join(error_msgs) if error_msgs else "请求入参校验失败"
    response_body = ApiResponse(
        code=ErrorCode.VALIDATION_ERROR,
        message=f"参数校验失败: {friendly_msg}",
        data={"raw_errors": exc.errors()}
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_body.model_dump()
    )


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    """兜底拦截所有未处理的系统异常"""
    print(f"🔥 [未捕获系统异常] 路径: {request.url.path} | 异常: {str(exc)}")
    response_body = ApiResponse(
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="服务器内部处理异常，请联系管理员或稍后重试",
        data={"error_type": type(exc).__name__}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_body.model_dump()
    )


# ---------------- 注册 API 路由分组 (统一挂载在 /api/v1 前缀下) ----------------
app.include_router(health_router, prefix="/api/v1")
app.include_router(sql_audit_router, prefix="/api/v1")
app.include_router(spec_query_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")

# ---------------- 注册 Web UI 界面路由 (挂载在根路径 / 与 /ui) ----------------
app.include_router(web_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=(settings.app_env == "development")
    )
