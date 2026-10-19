"""
SQL 审查精简 Markdown 回复渲染单元测试 (无需大模型与向量库，可离线执行)

验证点:
1. 回复仅包含「不满足项 + 整改方案 + 修改后的 SQL」三类内容；
2. 每条不满足项均带 [n] 编号引用依据；
3. 完全合规时只输出一行通过结论。
"""

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

from app.models.dto.sql_audit import CitationDetail, ViolationDetail
from app.services.audit_report_renderer import AuditReportRenderer


class TestAuditReportRenderer(unittest.TestCase):
    """
    精简 Markdown 整改回复渲染测试套件
    """

    def test_01_violation_report_is_compact_and_numbered(self):
        """测试 1: 存在不满足项时，回复只含不满足项、整改方案与修改后的 SQL"""
        print("\n--- [渲染测试 1] 违规回复精简结构与编号引用 ---")
        violations = [
            ViolationDetail(
                rule_id="rule_no_double",
                rule_name="禁止使用浮点数 double",
                severity="ERROR",
                target_object="total_amount double",
                description="金额必须使用 decimal(20, 6) 存储，double 存在精度丢失风险",
                suggested_fix="将 double 修改为 decimal(20, 6)，并命名后缀为 _money",
                citation_index=2,
            ),
            ViolationDetail(
                rule_id="rule_no_foreign_key",
                rule_name="表内禁止外键设计",
                severity="WARN",
                target_object="CONSTRAINT fk_user FOREIGN KEY",
                description="严禁使用 FOREIGN KEY，关联关系应在应用层维护",
                suggested_fix="删除外键约束定义",
                citation_index=1,
            ),
        ]
        citations = [
            CitationDetail(
                index=1,
                title="《数据库规范》- 数据库规范 > 建库规范",
                snippet="严禁使用外键约束...",
                source_file="数据库规范.md",
            ),
            CitationDetail(
                index=2,
                title="《数据库规范》- 数据库规范 > 数据类型规范",
                snippet="金额统一使用 decimal(20, 6)...",
                source_file="数据库规范.md",
            ),
        ]

        report = AuditReportRenderer.render(
            is_compliant=False,
            score=70,
            violations=violations,
            suggested_sql="CREATE TABLE `db_order_info` (\n  `id` BIGINT UNSIGNED NOT NULL\n);",
            citations=citations,
        )
        print(report)

        # 1. 两大精简章节齐备
        self.assertIn("### ⚠️ 不满足项与整改方案（共 2 项）", report)
        self.assertIn("### ✅ 修改后的 SQL", report)

        # 2. 每条不满足项均带编号引用依据 (编号 + 条款标题)
        self.assertIn("**1. 禁止使用浮点数 double** · 🔴 ERROR · 依据：[2] 《数据库规范》- 数据库规范 > 数据类型规范", report)
        self.assertIn("**2. 表内禁止外键设计** · 🟡 WARN · 依据：[1] 《数据库规范》- 数据库规范 > 建库规范", report)

        # 3. 整改方案与违规片段逐条落地
        self.assertIn("- 不满足片段：`total_amount double`", report)
        self.assertIn("- 整改方案：将 double 修改为 decimal(20, 6)，并命名后缀为 _money", report)
        self.assertIn("- 整改方案：删除外键约束定义", report)

        # 4. 修改后的 SQL 以 sql 代码块输出
        self.assertIn("```sql", report)
        self.assertIn("CREATE TABLE `db_order_info`", report)

        # 5. 旧的冗长排版必须彻底移除
        for redundant in ["审查总览看板", "待审查原始 SQL", "违规明细对照与整改建议", "规范依据清单", "| :---"]:
            self.assertNotIn(redundant, report)
        print("[PASS] 违规回复仅包含不满足项、整改方案与修改后的 SQL，且逐条带编号引用依据！")

    def test_02_compliant_report_is_single_line(self):
        """测试 2: 完全合规时仅输出一行通过结论"""
        print("\n--- [渲染测试 2] 合规回复单行结论 ---")
        report = AuditReportRenderer.render(
            is_compliant=True,
            score=100,
            violations=[],
            suggested_sql="CREATE TABLE `db_order_info` (`id` BIGINT UNSIGNED NOT NULL);",
            citations=[],
        )
        print(report)

        self.assertIn("未发现不满足项", report)
        self.assertIn("完全合规", report)
        self.assertIn("100 / 100", report)
        self.assertNotIn("```", report, "合规回复无需再输出 SQL 代码块")
        print("[PASS] 合规回复保持单行结论，无冗余排版！")


if __name__ == "__main__":
    unittest.main(verbosity=2)
