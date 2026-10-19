"""
DoubleCheckVerifier 与 SqlAuditService 针对 oil_order 异常的优化专项单元测试

验证点:
1. 自相矛盾假阳性过滤: 描述自述「基本符合要求需统一保留」的项目被自动剔除；
2. DECIMAL 假阳性过滤: 原始 SQL 已是 decimal(20,6) 的字段，不被误报为未用 decimal；
3. 后缀假阳性清洗: listed_money 从 _money 违规列表中安全剔除；全量符合 _price 的假阳性直接整项剔除；
4. 长字符串定长 CHAR(22) 纠偏: 禁止将 char(22) 误判为 1 字符 TINYINT(4)，自动校准为 varchar(22) 规范；
5. 保留关键字 num 纠偏: 纠正为数量后缀 _amount 规范；
6. 重构 SQL 净化: 自动剔除 AUTO_INCREMENT 自增以符合雪花算法，避免裸 time 保留字。
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

from app.models.dto.sql_audit import ViolationDetail
from app.models.entity.chunk import Chunk, ChunkMetadata
from app.services.double_check_verifier import DoubleCheckVerifier
from app.services.sql_audit_service import SqlAuditService


class TestVerifierEnhancements(unittest.TestCase):
    """
    针对实际业务 DDL (oil_order) 审查误判与过度整改的防御增强测试套件
    """

    def setUp(self):
        self.verifier = DoubleCheckVerifier()
        # 准备标准规范切块模拟
        self.chunk_naming = Chunk(
            chunk_id="chunk_naming",
            embedding_text="命名规范 统一后缀 _money _price _amount",
            display_text="4. 单价的统一命名后缀为 [xxxx_]price\n5. 金额的统一命名后缀为 [xxxx_]money\n6. 数量的统一命名后缀为 [xxxx_]amount",
            metadata=ChunkMetadata(
                heading_path="数据库规范 > 命名规范",
                section="命名规范",
                category="naming"
            )
        )
        self.chunk_db = Chunk(
            chunk_id="chunk_database_rules",
            embedding_text="建库规范 decimal tinyint(4) varchar",
            display_text="11. double类型不要用，直接用decimal\n13. 对于 TINYINT 类型，统一使用 TINYINT(4)\n大于1个字符：varchar(30)",
            metadata=ChunkMetadata(
                heading_path="数据库规范 > 建库规范",
                section="建库规范",
                category="ddl_rule"
            )
        )
        self.chunk_map = {1: self.chunk_naming, 2: self.chunk_db}

        # 待测试的真实 SQL 片段
        self.sample_sql = """
        CREATE TABLE `oil_order` (
          `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT '物理主键',
          `order_price` decimal(20,6) NOT NULL COMMENT '加油金额',
          `gun_price` decimal(20,6) DEFAULT NULL COMMENT '枪价',
          `total_user_real_amount` decimal(20,6) DEFAULT NULL COMMENT '用户总实付金额',
          `listed_money` decimal(20,6) DEFAULT NULL COMMENT '挂牌金额',
          `carry_company_id` char(22) DEFAULT NULL COMMENT '承运人id',
          `num` decimal(20,6) DEFAULT NULL COMMENT '加油升数'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

    def test_01_filter_self_contradiction(self):
        """测试 1: 自相矛盾项过滤 (如描述自述「基本符合要求需统一保留」却打 ERROR)"""
        print("\n--- [测试 1] 自相矛盾假阳性过滤 ---")
        v = ViolationDetail(
            rule_id="rule_price_suffix",
            rule_name="单价字段命名后缀须为_price",
            severity="ERROR",
            target_object="order_price, gun_price",
            description="单价字段命名基本符合_price后缀要求，需统一保留",
            suggested_fix="保留_price后缀不做amount混用",
            citation_index=1
        )
        res = self.verifier.verify_and_filter(
            raw_violations=[v],
            chunk_index_map=self.chunk_map,
            sql_text=self.sample_sql
        )
        self.assertEqual(len(res.verified_violations), 0, "自相矛盾项应被完全剔除")
        self.assertEqual(len(res.hallucinations), 1)
        self.assertTrue(res.is_compliant)
        print("[PASS] 自相矛盾假阳性项已成功过滤！")

    def test_02_filter_decimal_false_positive(self):
        """测试 2: DECIMAL 假阳性过滤 (原表中指定列已经明确是 decimal)"""
        print("\n--- [测试 2] DECIMAL 假阳性过滤 ---")
        v_false_positive = ViolationDetail(
            rule_id="rule_decimal_type",
            rule_name="金额必须使用decimal类型",
            severity="ERROR",
            target_object="order_price, gun_price",
            description="金额类字段应统一decimal(20,6)，不得用其他类型",
            suggested_fix="统一使用decimal(20,6)",
            citation_index=2
        )
        res = self.verifier.verify_and_filter(
            raw_violations=[v_false_positive],
            chunk_index_map=self.chunk_map,
            sql_text=self.sample_sql
        )
        self.assertEqual(len(res.verified_violations), 0, "原 SQL 已为 decimal 的字段不应报违规")
        print("[PASS] DECIMAL 假阳性误报已成功过滤！")

    def test_03_clean_naming_suffix_targets(self):
        """测试 3: 命名后缀假阳性过滤与清单清洗"""
        print("\n--- [测试 3] 命名后缀假阳性过滤与清洗 ---")
        # listed_money 混入金额违规
        v_money = ViolationDetail(
            rule_id="rule_money_suffix",
            rule_name="金额字段命名后缀须为_money",
            severity="ERROR",
            target_object="total_user_real_amount, listed_money",
            description="金额字段误用 amount 后缀",
            suggested_fix="改为 _money 后缀",
            citation_index=1
        )
        # 全量符合 _price 后缀
        v_price = ViolationDetail(
            rule_id="rule_price_suffix",
            rule_name="单价字段命名后缀须为_price",
            severity="ERROR",
            target_object="order_price, gun_price",
            description="需遵循 _price 后缀",
            suggested_fix="修改后缀",
            citation_index=1
        )

        res = self.verifier.verify_and_filter(
            raw_violations=[v_money, v_price],
            chunk_index_map=self.chunk_map,
            sql_text=self.sample_sql
        )
        self.assertEqual(len(res.verified_violations), 1)
        # v_price 整项剔除，v_money 的 target_object 移除了 listed_money
        verified_money = res.verified_violations[0]
        self.assertEqual(verified_money.target_object, "total_user_real_amount")
        self.assertNotIn("listed_money", verified_money.target_object)
        print("[PASS] listed_money 成功剔除，合规字段清洗通过！")

    def test_04_guard_single_char_rule_char22(self):
        """测试 4: 长字符串定长 CHAR(22) 纠偏 (禁止误套单字符 TINYINT(4))"""
        print("\n--- [测试 4] 定长 CHAR(22) 误判纠偏 ---")
        v_char22 = ViolationDetail(
            rule_id="rule_single_char",
            rule_name="1个字符字段须用TINYINT(4)",
            severity="ERROR",
            target_object="carry_company_id",
            description="carry_company_id使用char(22)，不符合字符字段设计规范，建议使用TINYINT(4)",
            suggested_fix="改为 TINYINT(4)",
            citation_index=2
        )
        res = self.verifier.verify_and_filter(
            raw_violations=[v_char22],
            chunk_index_map=self.chunk_map,
            sql_text=self.sample_sql
        )
        self.assertEqual(len(res.verified_violations), 1)
        corrected = res.verified_violations[0]
        self.assertEqual(corrected.rule_name, "大于1个字符须统一使用 varchar")
        self.assertIn("varchar(22)", corrected.suggested_fix)
        self.assertNotIn("TINYINT(4)", corrected.suggested_fix)
        print(f"[PASS] 纠偏结果: {corrected.rule_name} -> {corrected.suggested_fix}")

    def test_05_guard_reserved_keyword_num(self):
        """测试 5: 保留关键字 num 误判纠偏为数量后缀规范"""
        print("\n--- [测试 5] 保留关键字 num 纠偏 ---")
        v_num = ViolationDetail(
            rule_id="rule_reserved_keyword",
            rule_name="禁止使用保留关键字",
            severity="ERROR",
            target_object="num",
            description="字段 num 语义不清且易与保留关键字混淆",
            suggested_fix="改为数量语义如 oil_amount",
            citation_index=2
        )
        res = self.verifier.verify_and_filter(
            raw_violations=[v_num],
            chunk_index_map=self.chunk_map,
            sql_text=self.sample_sql
        )
        self.assertEqual(len(res.verified_violations), 1)
        corrected = res.verified_violations[0]
        self.assertEqual(corrected.rule_name, "数量字段命名后缀须为_amount")
        self.assertIn("oil_amount", corrected.suggested_fix)
        print(f"[PASS] 纠偏结果: {corrected.rule_name} -> {corrected.suggested_fix}")

    def test_06_clean_suggested_sql(self):
        """测试 6: 重构 SQL 净化 (去 AUTO_INCREMENT，防保留字 time)"""
        print("\n--- [测试 6] 重构 SQL 净化清洗 ---")
        dirty_sql = """
        CREATE TABLE `db_oil_order` (
          `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '雪花主键',
          `time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '下单时间'
        ) ENGINE=InnoDB AUTO_INCREMENT=1000 DEFAULT CHARSET=utf8mb4;
        """
        cleaned = SqlAuditService._clean_suggested_sql(dirty_sql)
        self.assertNotIn("AUTO_INCREMENT", cleaned)
        self.assertNotIn("`time` DATETIME", cleaned)
        self.assertIn("`order_time` DATETIME", cleaned)
        print("[PASS] 重构 SQL 已净化为无自增雪花主键，且避免了 `time` DATETIME 关键字！")


if __name__ == "__main__":
    unittest.main(verbosity=2)
