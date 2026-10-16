"""
系统健康检查业务服务 (Service Layer - Async & Injected)

【架构知识点说明】
- 遵循依赖注入原则：构造函数显式接收 Repository 实例，不再在内部私自 new 实例。
- 纯异步非阻塞：采用 `async def`，使用 `asyncio.gather` 并发检测两个模型服务的健康状况，将串行耗时降到最低！
"""

import asyncio
from typing import List, Optional
from app.core.config import get_settings
from app.models.dto.health import HealthResponseData, ModelServiceStatus
from app.repositories.ollama_embedding_repository import OllamaEmbeddingRepository
from app.repositories.relay_llm_repository import RelayLlmRepository


class HealthService:
    """
    负责异步执行系统全链路连通性健康体检
    """

    def __init__(
        self,
        ollama_repo: Optional[OllamaEmbeddingRepository] = None,
        relay_repo: Optional[RelayLlmRepository] = None
    ):
        self.settings = get_settings()
        self.ollama_repo = ollama_repo or OllamaEmbeddingRepository()
        self.relay_repo = relay_repo or RelayLlmRepository()

    async def check_system_health(self) -> HealthResponseData:
        """
        并发检测本地 Ollama Embedding 与云端中转站 LLM 的连接状况
        使用 asyncio.gather 实现双路并发探测，耗时取决于最慢的一方（而非两者相加）
        """
        # 并发执行健康体检
        ollama_task = self.ollama_repo.health_check()
        relay_task = self.relay_repo.health_check()
        # 并发执行两个异步任务，并等它们都完成，把结果按顺序解包。
        ollama_res, relay_res = await asyncio.gather(ollama_task, relay_task)

        services_status: List[ModelServiceStatus] = [
            ModelServiceStatus(
                name="Local Ollama Embedding",
                model=ollama_res["model"],
                status="healthy" if ollama_res["healthy"] else "unreachable",
                latency_ms=ollama_res["latency_ms"],
                message=f"向量输出维度: {ollama_res['dimension']}" if ollama_res["healthy"] else ollama_res["error"]
            ),
            ModelServiceStatus(
                name="Relay DeepSeek LLM",
                model=relay_res["model"],
                status="healthy" if relay_res["healthy"] else "unreachable",
                latency_ms=relay_res["latency_ms"],
                message="API 响应正常" if relay_res["healthy"] else relay_res["error"]
            )
        ]

        # 汇总全局状态
        all_healthy = all(s.status == "healthy" for s in services_status)
        global_status = "running_healthy" if all_healthy else "running_degraded"

        return HealthResponseData(
            app_status=global_status,
            version=self.settings.app_version,
            services=services_status
        )
