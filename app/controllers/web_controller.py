"""
Web 用户交互界面控制器 (Web Controller)

【架构说明】
- 遵循 MVC 架构设计，负责向浏览器渲染交付单页面应用 (Single Page Application) HTML 视图；
- 支持根路径 `/` 与 `/ui` 访问。
"""

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Web UI"])

# 页面模板文件绝对路径
CURRENT_DIR = Path(__file__).resolve().parent.parent
STATIC_INDEX_FILE = CURRENT_DIR / "static" / "index.html"


@router.get("/", response_class=HTMLResponse, summary="Web 交互主界面")
@router.get("/ui", response_class=HTMLResponse, summary="Web 交互界面别名")
async def serve_web_ui():
    """
    提供智能 SQL 规范审查与知识问答可视化 Web 交互控制台
    """
    if not STATIC_INDEX_FILE.exists():
        return HTMLResponse(
            content="<h3>前端静态页面未找到，请确认 app/static/index.html 存在。</h3>",
            status_code=404
        )
    
    with open(STATIC_INDEX_FILE, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content, status_code=200)
