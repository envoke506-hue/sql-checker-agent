"""控制器层导出"""
from app.controllers.health_controller import router as health_router
from app.controllers.sql_audit_controller import router as sql_audit_router
from app.controllers.spec_query_controller import router as spec_query_router
from app.controllers.knowledge_controller import router as knowledge_router
from app.controllers.web_controller import router as web_router

__all__ = [
    "health_router",
    "sql_audit_router",
    "spec_query_router",
    "knowledge_router",
    "web_router",
]
