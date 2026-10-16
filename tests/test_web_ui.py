"""
Web 用户界面 (UI) 与静态资源端点测试套件
验证前端单页面交互界面的交付与路由映射
"""

import sys
from pathlib import Path

# 保证 Windows 控制台 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 将项目根目录加入 sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from app.main import app


def test_web_ui_endpoints():
    """测试 Web UI 界面端点返回"""
    client = TestClient(app)

    # 1. 测试根路径 GET /
    print("\n--- [测试 1: 验证根路径 GET / 返回 Web 控制台页面] ---")
    resp_root = client.get("/")
    assert resp_root.status_code == 200, f"根路径状态码异常: {resp_root.status_code}"
    assert "text/html" in resp_root.headers.get("content-type", "")
    html_text = resp_root.text
    assert "SQL Checker Agent" in html_text, "页面标题缺少系统名"
    assert "典型违规反例" in html_text, "缺少反例填充快捷键"
    assert "合规正例" in html_text, "缺少正例填充快捷键"
    assert "深度思考" in html_text, "缺少 DeepSeek 风格深度思考模块"
    assert "不满足项" in html_text, "缺少不满足项标红展示模块"
    print("[PASS] 根路径 GET / 成功返回完整 WebUI 单页面 HTML 应用！")

    # 2. 测试别名路由 GET /ui
    print("\n--- [测试 2: 验证别名路径 GET /ui] ---")
    resp_ui = client.get("/ui")
    assert resp_ui.status_code == 200
    assert "SQL Checker Agent" in resp_ui.text
    print("[PASS] 别名路径 GET /ui 访问成功！")

    # 3. 验证 Swagger 交互文档依然正常工作 GET /docs
    print("\n--- [测试 3: 验证 Swagger API 文档 GET /docs 保持可用] ---")
    resp_docs = client.get("/docs")
    assert resp_docs.status_code == 200
    assert "swagger" in resp_docs.text.lower()
    print("[PASS] Swagger UI 交互文档 /docs 保持正常服务！")


if __name__ == "__main__":
    test_web_ui_endpoints()
    print("\n=======================================================")
    print(">>> 恭喜！前端 Web UI 控制台集成测试全部通过！<<<")
    print("=======================================================\n")
