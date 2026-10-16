"""
中转站大模型异步推理仓储 (Repository Layer - Async)

【框架与技术知识点说明】
1. 异步请求与异常熔断包装:
   - 全面使用 `httpx.AsyncClient` 进行非阻塞 HTTP 调用。
   - 针对常见的 HTTP 401 (密钥无效)、429 (频率超限)、504 (网关超时) 进行语义化解析，抛出自定义 `ModelServiceException`。
"""

import time
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.core.exceptions import ModelServiceException
from app.core.http_client import get_async_client


class RelayLlmRepository:
    """
    负责异步调用云端中转站 deepseek-flash 模型执行 SQL 审查与问答生成
    对应课件第 18、19 篇：大模型上下文理解与严格约束生成
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.settings = get_settings()
        self.base_url = self.settings.relay_api_base_url.rstrip("/")
        self.api_key = self.settings.relay_api_key
        self.model_name = self.settings.relay_llm_model
        self.timeout = self.settings.relay_timeout_seconds
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client or get_async_client()

    def _get_headers(self) -> Dict[str, str]:
        """构造带有 Bearer Token 的请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def health_check(self) -> dict:
        """
        异步健康检查：向中转站发送单字测试，验证连通性与密钥有效性
        """
        start_time = time.time()
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": "1"}],
            "max_tokens": 10
        }

        try:
            resp = await self.client.post(
                endpoint,
                headers=self._get_headers(),
                json=payload,
                timeout=10.0
            )
            latency_ms = round((time.time() - start_time) * 1000, 2)

            if resp.status_code == 200:
                return {
                    "healthy": True,
                    "latency_ms": latency_ms,
                    "model": self.model_name,
                    "endpoint": endpoint,
                    "error": None
                }
            else:
                return {
                    "healthy": False,
                    "latency_ms": latency_ms,
                    "model": self.model_name,
                    "endpoint": endpoint,
                    "error": f"中转站返回 HTTP {resp.status_code}: {resp.text}"
                }
        except httpx.ConnectError:
            return {
                "healthy": False,
                "latency_ms": None,
                "model": self.model_name,
                "endpoint": endpoint,
                "error": f"无法连接到中转站 API 服务 ({endpoint})，请检查网络连接。"
            }
        except Exception as e:
            return {
                "healthy": False,
                "latency_ms": None,
                "model": self.model_name,
                "endpoint": endpoint,
                "error": f"中转站请求异常: {str(e)}"
            }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        异步发起大模型对话生成请求

        :param messages: 对话上下文
        :param temperature: 采样温度 (RAG 严格审查推荐 0.0 ~ 0.2)
        :param max_tokens: 最大生成限制
        :param response_format: 可选结构化格式控制，如 {"type": "json_object"}
        :return: 包含 content、reasoning_content、usage 的字典
        """
        if not self.api_key:
            raise ModelServiceException("未配置中转站 RELAY_API_KEY，请检查 .env 配置文件。")

        endpoint = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        try:
            resp = await self.client.post(
                endpoint,
                headers=self._get_headers(),
                json=payload,
                timeout=float(self.timeout)
            )

            if resp.status_code != 200:
                raise ModelServiceException(
                    message=f"调用中转站大模型 API 失败 (HTTP {resp.status_code})",
                    detail=resp.text
                )

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise ModelServiceException(f"大模型响应中未找到 choices 生成结果: {data}")

            message = choices[0].get("message", {})
            content = message.get("content", "").strip()
            reasoning = message.get("reasoning_content", "")
            usage = data.get("usage", {})

            return {
                "content": content,
                "reasoning_content": reasoning,
                "usage": usage,
                "model": data.get("model", self.model_name)
            }
        except httpx.TimeoutException as e:
            raise ModelServiceException("大模型推理生成超时，请稍后重试") from e
        except httpx.RequestError as e:
            raise ModelServiceException(f"连接大模型网络出现故障: {str(e)}") from e

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        便捷方法：直接返回大模型生成的正文 content 字符串
        若 content 为空但包含 reasoning_content，自动降级回退
        """
        res = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )
        content = res.get("content", "")
        if not content and res.get("reasoning_content"):
            content = res.get("reasoning_content", "")
        return content.strip()
