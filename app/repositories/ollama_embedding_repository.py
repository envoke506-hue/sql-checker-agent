"""
本地 Ollama 向量模型异步仓储 (Repository Layer - Async)

【框架与技术知识点说明】
1. 纯异步 I/O (async/await):
   - 所有与底层外部服务的通信方法均使用 `async def` 声明。
   - 使用 `await client.post(...)` 实现非阻塞调用，高并发下不会挂起主事件循环。
2. 异常精准转化:
   - 底层网络错误（超时、连接拒绝）统一捕获并转化为语义清晰的 `OllamaServiceException`，
     携带具体业务错误码，交由全局异常拦截器统一处理。
"""

import time
from typing import List, Optional
import httpx

from app.core.config import get_settings
from app.core.exceptions import OllamaServiceException
from app.core.http_client import get_async_client


class OllamaEmbeddingRepository:
    """
    负责异步调用本地 Ollama 服务计算文本向量 (Embedding)
    对应课件第 17 篇：向量化模型交互
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url.rstrip("/")
        self.model_name = self.settings.ollama_embedding_model
        self.timeout = self.settings.ollama_timeout_seconds
        # 允许外部注入 client (单测 Mock 友好)，默认使用全局连接池客户端
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client or get_async_client()

    async def health_check(self) -> dict:
        """
        异步健康检查：测试本地 Ollama 服务连通性与模型是否就绪
        """
        start_time = time.time()
        endpoint = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model_name,
            "prompt": "health_check"
        }

        try:
            resp = await self.client.post(endpoint, json=payload, timeout=5.0)
            latency_ms = round((time.time() - start_time) * 1000, 2)

            if resp.status_code == 200:
                data = resp.json()
                vec = data.get("embedding", [])
                return {
                    "healthy": True,
                    "latency_ms": latency_ms,
                    "dimension": len(vec),
                    "model": self.model_name,
                    "error": None
                }
            else:
                return {
                    "healthy": False,
                    "latency_ms": latency_ms,
                    "dimension": 0,
                    "model": self.model_name,
                    "error": f"Ollama 返回错误状态码: {resp.status_code}, 内容: {resp.text}"
                }
        except httpx.ConnectError:
            return {
                "healthy": False,
                "latency_ms": None,
                "dimension": 0,
                "model": self.model_name,
                "error": f"无法连接到本地 Ollama 服务 ({self.base_url})，请检查 Ollama 是否已启动。"
            }
        except Exception as e:
            return {
                "healthy": False,
                "latency_ms": None,
                "dimension": 0,
                "model": self.model_name,
                "error": f"Ollama 调用异常: {str(e)}"
            }

    async def get_embedding(self, text: str) -> List[float]:
        """
        异步获取单段文本的向量表示 (2560 维浮点数组)

        :param text: 输入文本 (已注入面包屑路径)
        :return: 浮点向量数组
        """
        clean_text = text.strip()
        if not clean_text:
            raise OllamaServiceException("待向量化的文本不能为空字符串")

        endpoint = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model_name,
            "prompt": clean_text
        }

        try:
            resp = await self.client.post(endpoint, json=payload, timeout=float(self.timeout))
            if resp.status_code != 200:
                raise OllamaServiceException(
                    message=f"Ollama 计算向量失败 (HTTP {resp.status_code})",
                    detail=resp.text
                )

            data = resp.json()
            embedding = data.get("embedding")
            if not embedding or not isinstance(embedding, list):
                raise OllamaServiceException(f"Ollama 返回的 embedding 格式无效: {data}")
            return embedding
        except httpx.TimeoutException as e:
            raise OllamaServiceException("Ollama 向量计算响应超时，请检查显卡或本地负载") from e
        except httpx.RequestError as e:
            raise OllamaServiceException(f"连接 Ollama 向量服务网络故障: {str(e)}") from e

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量异步计算文本向量
        """
        results: List[List[float]] = []
        for text in texts:
            vec = await self.get_embedding(text)
            results.append(vec)
        return results
