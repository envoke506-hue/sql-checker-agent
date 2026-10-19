"""
SqlAuditService 离线链路测试 (桩化检索与 LLM，无需网络与向量服务)

验证点:
1. 正常审查: 回复仅含「不满足项 + 整改方案 + 修改后的 SQL」，且逐条带 [n] 编号引用依据；
2. 大模型只输出思考文字不返回 JSON 时: 自动重试一次，仍失败则显式报错，
   绝不伪判「完全合规 100 分」把不合规 SQL 放过。
"""

import asyncio
import json
import sys
import unittest
from pathlib import Path

# 保证 Windows 控制台 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.core.exceptions import ModelServiceException
from app.models.dto.sql_audit import SqlAuditRequest
from app.models.entity.chunk import Chunk, ChunkMetadata
from app.services.context_orchestrator import ContextOrchestrator
from app.services.double_check_verifier import DoubleCheckVerifier
from app.services.sql_audit_service import SqlAuditService


class StaticRetrievalService:
    """桩化检索服务: 直接返回一个真实的 decimal 类型规范切块"""

    async def retrieve_for_sql(self, sql_text: str, top_k: int = 3):
        chunk = Chunk(
            chunk_id="chunk_data_type",
            embedding_text="金额统一使用 decimal(20, 6)",
            display_text=(
                "### 数据类型规范\n"
                "17. 数量、金额类统一使用 decimal 类型，精确如无特殊需求统一使用 decimal(20, 6)，严禁 double。"
            ),
            metadata=ChunkMetadata(
                doc_title="数据库规范",
                heading_path="数据库规范 > 数据类型规范",
                section="数据类型规范",
                category="ddl_rule",
            ),
        )
        return [(chunk, 0.9)]


class ScriptedRelayRepository:
    """桩化 LLM 仓储: 按脚本顺序返回预设输出，并记录调用次数"""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    async def generate(self, messages, **kwargs) -> str:
        self.calls += 1
        return self.outputs[min(self.calls - 1, len(self.outputs) - 1)]


class TestSqlAuditServiceOffline(unittest.TestCase):
    """
    SQL 审查核心服务离线链路测试套件
    """

    def _service(self, relay: ScriptedRelayRepository) -> SqlAuditService:
        return SqlAuditService(
            relay_repo=relay,
            retrieval_svc=StaticRetrievalService(),
            orchestrator=ContextOrchestrator(),
            double_checker=DoubleCheckVerifier(),
        )

    def test_01_audit_reply_contains_only_violations_fix_and_sql(self):
        """测试 1: 正常审查只输出不满足项、整改方案与修改后的 SQL"""
        print("\n--- [离线测试 1] 正常审查回复精简结构 ---")
        llm_json = json.dumps({
            "is_compliant": False,
            "summary": "金额字段使用了 double。",
            "violations": [{
                "rule_id": "rule_no_double",
                "rule_name": "禁止使用浮点数 double",
                "severity": "ERROR",
                "target_object": "total_amount double",
                "description": "double 存在精度丢失风险，金额必须用 decimal(20, 6)",
                "suggested_fix": "改为 decimal(20, 6)，命名后缀为 _money",
                "citation_index": 1,
            }],
            "suggested_sql": "CREATE TABLE `db_order_info` (`order_money` DECIMAL(20, 6) NOT NULL);",
        }, ensure_ascii=False)
        relay = ScriptedRelayRepository([llm_json])

        result = asyncio.run(
            self._service(relay).audit_sql(
                SqlAuditRequest(sql_text="CREATE TABLE `order` (`total_amount` double);")
            )
        )
        print(result.markdown_report)

        self.assertEqual(relay.calls, 1, "正常路径不应触发重试")
        self.assertFalse(result.is_compliant)
        self.assertEqual(result.score, 80)
        self.assertIn("### ⚠️ 不满足项与整改方案（共 1 项）", result.markdown_report)
        self.assertIn("依据：[1] 《数据库规范》- 数据库规范 > 数据类型规范", result.markdown_report)
        self.assertIn("- 整改方案：改为 decimal(20, 6)，命名后缀为 _money", result.markdown_report)
        self.assertIn("### ✅ 修改后的 SQL", result.markdown_report)
        self.assertNotIn("审查总览看板", result.markdown_report)
        print("[PASS] 回复仅含不满足项、整改方案与修改后的 SQL，且带编号引用依据！")

    def test_02_invalid_json_is_retried_then_raises_instead_of_false_pass(self):
        """测试 2: 模型只输出思考文字时重试一次，仍失败则显式报错而非伪判合规"""
        print("\n--- [离线测试 2] 非 JSON 输出严禁伪判「完全合规」 ---")
        prose = "我们需要分析这段 DDL：表名 order 是保留字，order_id 属于冗余前缀，需要整改……"
        relay = ScriptedRelayRepository([prose, prose])

        with self.assertRaises(ModelServiceException) as ctx:
            asyncio.run(
                self._service(relay).audit_sql(
                    SqlAuditRequest(sql_text="CREATE TABLE `order` (`total_amount` double);")
                )
            )

        print(f"拦截提示: {ctx.exception.message}")
        self.assertEqual(relay.calls, 2, "解析失败后应恰好重试一次")
        self.assertNotIn("完全合规", str(ctx.exception.message))
        print("[PASS] 解析失败不会伪装成 100 分完全合规，而是明确报错要求重试！")


if __name__ == "__main__":
    unittest.main(verbosity=2)
