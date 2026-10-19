"""
系统全局配置模块 (Core Config)

【框架知识点说明】
1. Pydantic Settings (BaseSettings):
   - 在现代 Python 工程化中，我们避免在业务代码里到处写 `os.getenv("XXX")`。
   - `BaseSettings` 是 Pydantic 提供的配置管理基类，它会自动从环境变量或 `.env` 文件中读取配置，
     并根据 Python 类型注解（如 str, int, bool）自动进行类型转换和校验（例如将字符串 "8000" 转为整数 8000）。
2. lru_cache 装饰器:
   - `functools.lru_cache` 是 Python 原生的缓存装饰器。
   - 它可以让 `get_settings()` 函数只实例化一次配置对象（单例模式），避免每次需要配置时都重复读取磁盘上的 `.env` 文件。
"""

import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用全局配置类
    属性名称对应 .env 中的环境变量键名（大小写不敏感）
    """

    # ---------------- 基础服务配置 ----------------
    app_name: str = "SQL Checker Agent"
    app_version: str = "v1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_env: str = "development"

    # ---------------- 本地 Ollama 配置 (Embedding) ----------------
    # 本地向量计算服务地址
    ollama_base_url: str = "http://127.0.0.1:11434"
    # 本地向量模型名称 (经测试支持 2560 维输出)
    ollama_embedding_model: str = "qwen3-embedding:4b"
    # 向量计算超时时间 (秒)
    ollama_timeout_seconds: int = 60

    # ---------------- 中转站大模型 API 配置 (LLM 推理) ----------------
    # 中转站 API 基础地址 (标准 OpenAI 兼容协议)
    relay_api_base_url: str = "http://gsccswitch.sepzg.vip/v1"
    # 中转站访问密钥
    relay_api_key: str = ""
    # 调用的主力推理模型
    relay_llm_model: str = "deepseek-flash"
    # LLM 调用超时时间 (秒)
    relay_timeout_seconds: int = 120

    # 规范 Markdown 文档的绝对路径 (默认指向当前项目的 doc/数据库规范.md)
    spec_doc_path: str = str(Path(__file__).resolve().parent.parent.parent / "doc" / "数据库规范.md")
    # 索引与持久化缓存存储目录
    storage_dir: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "indices")

    # ---------------- Pydantic 设置元信息 ----------------
    # 指定加载同级或项目根目录的 .env 文件，编码为 utf-8
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略未在类中声明的多余环境变量，防止抛出校验异常
    )


@lru_cache
def get_settings() -> Settings:
    """
    获取全局唯一的配置实例 (单例模式)
    
    调用示例：
        from app.core.config import get_settings
        settings = get_settings()
        print(settings.app_port)
    """
    return Settings()
