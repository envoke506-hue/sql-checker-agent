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


class FullRetrievalService:
    """提供全套规范切块的桩化检索服务，支持保留字、名词术语、建表模板、建库规范"""

    async def retrieve_for_sql(self, sql_text: str, top_k: int = 5):
        chunks = [
            Chunk(
                chunk_id="chunk_naming",
                embedding_text="字段名禁止使用保留关键字，遵循规范名词术语，英文单词拼写规范",
                display_text=(
                    "### 字段设计与索引命名\n"
                    "1. 字段名禁止使用保留关键字，如 type, order 等。\n"
                    "2. 电话类字段必须使用 phone，严禁使用 tel。\n"
                    "3. 字段命名规范：严格避免拼写错误，英文单词拼写错误必须纠正。"
                ),
                metadata=ChunkMetadata(
                    doc_title="数据库规范",
                    heading_path="数据库规范 > 建表规范 > 字段设计与索引命名",
                    section="字段设计与索引命名",
                    category="naming_rule",
                ),
            ),
            Chunk(
                chunk_id="chunk_template",
                embedding_text="实体基类必须包含 7 大审计字段与主键",
                display_text=(
                    "### 实体基类必须字段\n"
                    "包含 id, deleted, disabled, version, create_id, create_time, modify_id, modify_time。"
                ),
                metadata=ChunkMetadata(
                    doc_title="数据库规范",
                    heading_path="数据库规范 > 建表模板 > 实体基类必须字段",
                    section="实体基类必须字段",
                    category="sql_template",
                ),
            ),
            Chunk(
                chunk_id="chunk_glossary",
                embedding_text="标准命名单词字典，电话 phone，联系 contact",
                display_text=(
                    "### 标准命名单词字典\n"
                    "标准词字典：phone (电话), contact (联系人)。"
                ),
                metadata=ChunkMetadata(
                    doc_title="数据库规范",
                    heading_path="数据库规范 > 名词术语 > 标准命名单词字典",
                    section="标准命名单词字典",
                    category="glossary",
                ),
            ),
            Chunk(
                chunk_id="chunk_db",
                embedding_text="库名前缀必须为 db_，必须使用 utf8mb4，字段必须使用 NOT NULL",
                display_text=(
                    "### 建库规范\n"
                    "库名前缀必须为 db_，字符集 utf8mb4，字段尽量使用 NOT NULL DEFAULT 避免存储开销。"
                ),
                metadata=ChunkMetadata(
                    doc_title="数据库规范",
                    heading_path="数据库规范 > 建表规范 > 建库规范",
                    section="建库规范",
                    category="database_rule",
                ),
            ),
        ]
        return [(c, 0.95 - idx * 0.05) for idx, c in enumerate(chunks)]


# 兼容别名
StaticRetrievalService = FullRetrievalService


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
            retrieval_svc=FullRetrievalService(),
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
        self.assertTrue(result.score < 100)
        self.assertIn("不满足项与整改方案", result.markdown_report)
        self.assertIn("依据：[1] 《数据库规范》", result.markdown_report)
        self.assertIn("decimal(20, 6)", result.markdown_report.lower())
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

    def test_03_duplicate_suppression_for_charge_station(self):
        """测试 3: 验证企业级语义抑制机制，彻底杜绝大模型在硬规则上的重复报送 (11项 -> 严格8项)"""
        print("\n--- [离线测试 3] 验证重复违规项彻底抑制 ---")
        charge_station_sql = (
            "CREATE TABLE `charge_station` (\n"
            "  `station_id` bigint(20) DEFAULT NULL COMMENT '站点ID',\n"
            "  `station_name` varchar(64) DEFAULT NULL COMMENT '站点名称',\n"
            "  `station_tel` varchar(32) DEFAULT NULL COMMENT '站点电话',\n"
            "  `station_type` varchar(32) DEFAULT NULL COMMENT '站点类型',\n"
            "  `station_status` varchar(32) DEFAULT NULL COMMENT '站点状态',\n"
            "  `station_lng` varchar(32) DEFAULT NULL COMMENT '经度',\n"
            "  `station_lat` varchar(32) DEFAULT NULL COMMENT '纬度',\n"
            "  `service_tel` varchar(32) DEFAULT NULL COMMENT '服务电话',\n"
            "  `type` varchar(32) DEFAULT NULL COMMENT '类型',\n"
            "  `carrier_company_id` bigint(20) DEFAULT NULL,\n"
            "  `carrier_company_name` varchar(64) DEFAULT NULL,\n"
            "  `operator_id` bigint(20) DEFAULT NULL,\n"
            "  `equipment_owner_id` bigint(20) DEFAULT NULL,\n"
            "  `country_code` varchar(32) DEFAULT NULL,\n"
            "  `area_code` varchar(32) DEFAULT NULL,\n"
            "  `version` bigint(20) DEFAULT NULL,\n"
            "  PRIMARY KEY (`id`)\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='充电站表';"
        )

        # 模拟大模型输出：大模型返回了 Suggested SQL，并且带有与代码规则重复的3项违规
        llm_payload = {
            "is_compliant": False,
            "summary": "charge_station 存在多处违规。",
            "violations": [
                {
                    "rule_id": "rule_reserved_keyword",
                    "rule_name": "字段名禁止使用保留关键字",
                    "severity": "ERROR",
                    "target_object": "type",
                    "description": "字段名 type 命中了 MySQL 保留关键字",
                    "suggested_fix": "改名为 type_item 等非关键字名称",
                    "citation_index": 1,
                },
                {
                    "rule_id": "rule_glossary",
                    "rule_name": "遵循规范名词术语",
                    "severity": "ERROR",
                    "target_object": "service_tel, station_tel",
                    "description": "电话类字段使用非标术语 tel，应使用规范术语 phone",
                    "suggested_fix": "service_tel 改 service_phone；station_tel 去前缀改 phone",
                    "citation_index": 1,
                },
                {
                    "rule_id": "rule_not_null",
                    "rule_name": "字段尽量使用 NOT NULL 约束",
                    "severity": "WARN",
                    "target_object": "station_id, station_name, carrier_company_id, carrier_company_name, operator_id, equipment_owner_id, country_code, area_code 等27个字段",
                    "description": "27 个字段未显式指定 NOT NULL，建议避免 NULL 带来的开销",
                    "suggested_fix": "追加 NOT NULL DEFAULT 默认值",
                    "citation_index": 1,
                }
            ],
            "suggested_sql": "CREATE TABLE `db_charge_station` (`id` BIGINT NOT NULL AUTO_INCREMENT, PRIMARY KEY (`id`));"
        }
        relay = ScriptedRelayRepository([json.dumps(llm_payload, ensure_ascii=False)])

        result = asyncio.run(
            self._service(relay).audit_sql(
                SqlAuditRequest(sql_text=charge_station_sql)
            )
        )

        print(f"最终违规项数量: {len(result.violations)}")
        for idx, item in enumerate(result.violations, 1):
            print(f"  [{idx}] {item.rule_name} | {item.target_object} | {item.description}")
        print(f"生成的 Markdown 报告前 500 字符:\n{result.markdown_report[:500]}")

        # 验证总项数必须为代码静态规则发现的 10 项，大模型的 3 项同义重复必须被 100% 滤除 (绝不能变成 10 + 3 = 13 项)
        self.assertEqual(len(result.violations), 10, f"预期为 10 项静态违规，实际得到 {len(result.violations)} 项，说明仍有重复未滤除！")

        rule_names = [v.rule_name for v in result.violations]
        self.assertEqual(rule_names.count("字段名禁止使用保留关键字"), 1, "保留关键字规则重复！")
        self.assertEqual(rule_names.count("遵循规范名词术语"), 1, "名词术语规则重复！")
        self.assertEqual(rule_names.count("字段尽量使用 NOT NULL 约束"), 1, "NOT NULL 规则重复！")

        # 验证 Markdown 中是否存在 (共 10 项) 且无第 11 项
        self.assertIn("共 10 项", result.markdown_report)
        self.assertNotIn("11. ", result.markdown_report)
        print("[PASS] 成功将大模型的 3 项同义重复彻底滤除，绝无双份重复报错！")

    def test_04_semantic_incremental_violation_is_preserved(self):
        """测试 4: 验证当大模型识别出独特的纯业务语义违规时 (如拼写错误)，能够被正常吸收保留"""
        print("\n--- [离线测试 4] 验证纯业务语义增量被正常吸收 ---")
        simple_sql = "CREATE TABLE `db_test`.`t_order` (`id` BIGINT NOT NULL, `busine_hours` VARCHAR(32) NOT NULL, `deleted` TINYINT NOT NULL DEFAULT 0, `disabled` TINYINT NOT NULL DEFAULT 0, `version` INT NOT NULL DEFAULT 0, `create_time` DATETIME NOT NULL, `modify_time` DATETIME NOT NULL, `create_id` BIGINT NOT NULL, `modify_id` BIGINT NOT NULL, PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"

        llm_payload = {
            "is_compliant": False,
            "summary": "busine_hours 存在拼写错误。",
            "violations": [
                {
                    "rule_id": "rule_semantic_typo",
                    "rule_name": "英文单词拼写错误",
                    "severity": "WARN",
                    "target_object": "busine_hours",
                    "description": "busine_hours 拼写错误，疑似笔误",
                    "suggested_fix": "修改为标准拼写 business_hours",
                    "citation_index": 1,
                }
            ],
            "suggested_sql": "CREATE TABLE `db_test`.`t_order` (`id` BIGINT NOT NULL, `business_hours` VARCHAR(32) NOT NULL, PRIMARY KEY (`id`));"
        }
        relay = ScriptedRelayRepository([json.dumps(llm_payload, ensure_ascii=False)])

        result = asyncio.run(
            self._service(relay).audit_sql(
                SqlAuditRequest(sql_text=simple_sql)
            )
        )

        rule_names = [v.rule_name for v in result.violations]
        self.assertIn("英文单词拼写错误", rule_names, "大模型的纯业务语义增量未被正确保留！")
        print(f"[PASS] 独特的纯业务语义增量被成功吸收！当前总违规项数: {len(result.violations)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
