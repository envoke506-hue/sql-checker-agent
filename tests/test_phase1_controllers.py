"""
第一阶段 RESTful Controller 接口层自动化集成测试 (Injected & Global Exception)
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

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from app.main import app
from app.models.dto.common import ErrorCode


class TestPhase1Controllers(unittest.TestCase):
    """
    Controller 层 HTTP 端点测试套件
    """

    def setUp(self):
        self.client = TestClient(app)

    def test_01_health_endpoint(self):
        """测试 1: 验证 GET /api/v1/health 并发健康检查"""
        print("\n--- [接口测试 1] GET /api/v1/health ---")
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        print(f"响应内容: {data}")
        self.assertEqual(data["code"], 20000)
        self.assertEqual(data["message"], "系统与依赖服务体检完成")
        self.assertIn("services", data["data"])
        print("[PASS] GET /api/v1/health 接口测试通过！")

    def test_02_sql_audit_endpoint_success(self):
        """测试 2: 验证 POST /api/v1/sql/audits 依赖注入正常请求"""
        print("\n--- [接口测试 2] POST /api/v1/sql/audits 正常请求 ---")
        payload = {
            "sql_text": "CREATE TABLE order (order_id bigint);",
            "db_type": "mysql"
        }
        resp = self.client.post("/api/v1/sql/audits", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        print(f"响应内容摘要: {data['data']['summary']}")
        self.assertEqual(data["code"], 20000)
        self.assertIn("markdown_report", data["data"])
        self.assertIn("score", data["data"])
        print("[PASS] POST /api/v1/sql/audits 接口测试通过！")

    def test_03_sql_audit_endpoint_validation_error(self):
        """测试 3: 验证 POST /api/v1/sql/audits 触发全局异常拦截器 (统一返回 ApiResponse 结构)"""
        print("\n--- [接口测试 3] POST /api/v1/sql/audits 全局参数校验异常拦截 ---")
        payload = {
            "sql_text": "abc"  # 长度小于 5，触发校验失败
        }
        resp = self.client.post("/api/v1/sql/audits", json=payload)
        self.assertEqual(resp.status_code, 422)  # Unprocessable Entity
        data = resp.json()
        print(f"统一格式校验拦截响应: {data}")
        # 验证全局异常拦截器是否将 422 包装成了 ApiResponse 契约
        self.assertEqual(data["code"], ErrorCode.VALIDATION_ERROR)
        self.assertIn("参数校验失败", data["message"])
        self.assertIn("sql_text", data["message"])
        print("[PASS] 全局异常拦截器统一信封包装成功！")

    def test_04_spec_query_endpoint(self):
        """测试 4: 验证 POST /api/v1/spec/queries 正常请求"""
        print("\n--- [接口测试 4] POST /api/v1/spec/queries ---")
        payload = {
            "question": "金额字段统一使用什么类型？"
        }
        resp = self.client.post("/api/v1/spec/queries", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        print(f"响应内容: {data['data']['answer']}")
        self.assertEqual(data["code"], 20000)
        print("[PASS] POST /api/v1/spec/queries 接口测试通过！")


if __name__ == "__main__":
    unittest.main()
