"""
第一阶段工程骨架与服务连通性自动化测试脚本 (Async Edition)
"""

import sys
import unittest
from pathlib import Path

# 解决 Windows 控制台编码问题
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 将项目根目录加入 sys.path 以支持模块导入
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.core.http_client import close_async_client
from app.repositories.ollama_embedding_repository import OllamaEmbeddingRepository
from app.repositories.relay_llm_repository import RelayLlmRepository
from app.services.health_service import HealthService
from app.models.dto.sql_audit import SqlAuditRequest
from app.models.dto.spec_query import SpecQueryRequest
from app.services.sql_audit_service import SqlAuditService
from app.services.spec_query_service import SpecQueryService


class TestPhase1SkeletonAsync(unittest.IsolatedAsyncioTestCase):
    """
    第一阶段核心骨架异步单元测试套件
    继承自 unittest.IsolatedAsyncioTestCase，原生支持 async def 测试方法
    """

    async def asyncSetUp(self):
        self.settings = get_settings()

    async def asyncTearDown(self):
        # 释放全局异步连接池
        await close_async_client()

    def test_01_config_loaded(self):
        """测试 1: 验证环境变量与配置是否正确加载"""
        print("\n--- [测试 1] 验证配置加载 ---")
        self.assertEqual(self.settings.app_name, "SQL Checker Agent")
        self.assertTrue(bool(self.settings.relay_api_key), "中转站 API Key 不能为空")
        self.assertEqual(self.settings.ollama_embedding_model, "qwen3-embedding:4b")
        self.assertEqual(self.settings.relay_llm_model, "deepseek-flash")
        
        spec_path = Path(self.settings.spec_doc_path)
        self.assertTrue(spec_path.exists(), f"数据库规范文件不存在: {spec_path}")
        print(f"[PASS] 配置加载成功，规范源文件存在，大小: {spec_path.stat().st_size} 字节")

    async def test_02_ollama_embedding_repo_async(self):
        """测试 2: 验证异步 Ollama 向量计算能力"""
        print("\n--- [测试 2] 验证异步 Ollama 向量计算 ---")
        repo = OllamaEmbeddingRepository()
        health = await repo.health_check()
        print(f"Ollama 健康体检: {health}")
        self.assertTrue(health["healthy"], f"Ollama 服务异常: {health['error']}")
        self.assertEqual(health["dimension"], 2560, "Qwen3-Embedding:4b 输出维度应为 2560")

        # 异步测试单文本向量化
        test_text = "数据库规范：主键使用雪花算法"
        vec = await repo.get_embedding(test_text)
        self.assertEqual(len(vec), 2560)
        self.assertIsInstance(vec[0], float)
        print(f"[PASS] 异步 Ollama 向量计算成功，输出维度: {len(vec)}，首个浮点值: {vec[0]}")

    async def test_03_relay_llm_repo_async(self):
        """测试 3: 验证异步中转站 DeepSeek-Flash 模型推理"""
        print("\n--- [测试 3] 验证异步中转站 DeepSeek-Flash 模型推理 ---")
        repo = RelayLlmRepository()
        health = await repo.health_check()
        print(f"中转站健康体检: {health}")
        self.assertTrue(health["healthy"], f"中转站服务异常: {health['error']}")

        # 异步测试生成
        messages = [
            {"role": "system", "content": "你是一个严谨的助手。"},
            {"role": "user", "content": "请只回复字符 'OK'，不要输出任何其他内容。"}
        ]
        resp = await repo.chat_completion(messages=messages, max_tokens=100)
        print(f"模型回复内容: '{resp['content']}'")
        self.assertIn("OK", resp["content"])
        print("[PASS] 异步中转站大模型调用成功！")

    async def test_04_health_service_async(self):
        """测试 4: 验证健康体检业务服务并发整合"""
        print("\n--- [测试 4] 验证系统健康服务并发整合 ---")
        service = HealthService()
        res = await service.check_system_health()
        print(f"系统汇总状态: {res.app_status}")
        for s in res.services:
            print(f" - {s.name}: {s.status} ({s.latency_ms}ms)")
        self.assertEqual(res.app_status, "running_healthy")
        print("[PASS] 全链路并发健康体检服务通过！")

    async def test_05_services_contract_async(self):
        """测试 5: 验证业务 Service 异步契约骨架"""
        print("\n--- [测试 5] 验证业务 Service 异步契约骨架 ---")
        audit_svc = SqlAuditService()
        audit_req = SqlAuditRequest(sql_text="CREATE TABLE order (id bigint);")
        audit_resp = await audit_svc.audit_sql(audit_req)
        self.assertIsNotNone(audit_resp.markdown_report)

        query_svc = SpecQueryService()
        query_req = SpecQueryRequest(question="金额字段怎么存？")
        query_resp = await query_svc.query_spec(query_req)
        self.assertIsNotNone(query_resp.markdown_content)
        print("[PASS] 业务 Service 异步契约验证通过！")


if __name__ == "__main__":
    unittest.main()
