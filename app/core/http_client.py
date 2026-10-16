"""
全局异步 HTTP 客户端与连接池管理 (Core HTTP Client Pool)

【框架与性能知识点深度说明】
1. 为什么弃用 requests 改用 httpx.AsyncClient:
   - `requests` 是纯同步阻塞库。在 FastAPI 的异步路由 `async def` 中调用 `requests.post()` 会卡住主线程的事件循环（Event Loop），
     导致在此期间并发到达的其他请求无法被调度处理，服务器吞吐量骤降。
   - `httpx.AsyncClient` 原生基于 `async/await`，当等待网络 I/O 返回时会自动让出 CPU，使 Python 可以继续处理其他并发请求。
2. 连接池 (Connection Pooling) 与 Keep-Alive:
   - 传统方式每次发请求都新建连接，会重复经历 TCP 三次握手和 TLS/SSL 握手协商，耗时高达几十毫秒。
   - `httpx.Limits(max_keepalive_connections=20, max_connections=50)` 会在内存中维持长连接池，
     后续请求复用已有连接，网络调用延迟大幅降低。
3. 生命周期管理 (Lifespan):
   - 在应用启动时创建单例客户端，在应用退出时调用 `await client.aclose()` 优雅释放底层 Socket 资源。
"""

from typing import Optional
import httpx

# 全局单例异步 HTTP 客户端
_async_client: Optional[httpx.AsyncClient] = None


def get_async_client() -> httpx.AsyncClient:
    """
    获取全局复用的异步 HTTP 客户端单例

    :return: 线程安全且支持连接池复用的 httpx.AsyncClient
    """
    global _async_client
    if _async_client is None or _async_client.is_closed:
        # 配置连接池规格
        limits = httpx.Limits(
            max_keepalive_connections=20,  # 允许保持空闲的长连接数
            max_connections=50,            # 最大并发连接上限
            keepalive_expiry=30.0          # 空闲连接存活时间 (秒)
        )
        _async_client = httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(timeout=120.0, connect=10.0)  # 默认总体超时 120s，建连超时 10s
        )
    return _async_client


async def close_async_client() -> None:
    """
    应用停机时优雅关闭客户端连接池，释放底层系统 Socket
    """
    global _async_client
    if _async_client is not None and not _async_client.is_closed:
        await _async_client.aclose()
        _async_client = None
