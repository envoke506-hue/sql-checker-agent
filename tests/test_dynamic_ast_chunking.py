"""
动态 Markdown AST 切块器专项单元测试 (Test Dynamic AST Chunking)
"""

import sys
import unittest
from pathlib import Path

# Windows 控制台编码配置
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.markdown_ast_parser import MarkdownASTParser
from app.services.chunking_service import ChunkingService


class TestDynamicASTChunking(unittest.TestCase):
    """验证动态 Markdown AST 解析器与源文档联动能力"""

    def test_01_parse_real_spec_doc(self):
        """测试 1: 验证从实际《数据库规范.md》动态切出的切块完整性"""
        chunking_svc = ChunkingService()
        chunks = chunking_svc.split_specification()

        self.assertEqual(len(chunks), 6, "从源文件动态切出的切块数量应精确为 6")
        chunk_map = {c.chunk_id: c for c in chunks}

        # 验证 6 个关键 chunk_id 全部动态就绪
        expected_ids = [
            "chunk_naming_rules",
            "chunk_terminology",
            "chunk_table_template",
            "chunk_database_rules",
            "chunk_field_and_index_rules",
            "chunk_framework_mybatis",
        ]
        for cid in expected_ids:
            self.assertIn(cid, chunk_map, f"切块 ID {cid} 缺失")

        # 验证元数据与双轨文本
        naming_chunk = chunk_map["chunk_naming_rules"]
        self.assertEqual(naming_chunk.metadata.category, "naming")
        self.assertTrue(naming_chunk.embedding_text.startswith("【规范层级】"))
        self.assertFalse(naming_chunk.display_text.startswith("【规范层级】"))
        self.assertIn("db_order.order.order_id", naming_chunk.display_text)
        print("[PASS] 真实源文档动态解析切块验证成功！")

    def test_02_dynamic_new_rule_addition(self):
        """测试 2: 验证如果在文档中动态新增第 7 个规则章节，系统能自动识别扩展"""
        sample_doc_with_new_rule = """---
chunk_id: chunk_naming_rules
heading_path: 数据库规范 > 命名规范
section: 命名规范
category: naming
keywords: [lower_snake_case]
---
## 命名规范
1. 采用 lower_snake_case

---
chunk_id: chunk_redis_rules
heading_path: 数据库规范 > 缓存架构规范 > Redis 命名与过期时间
section: Redis 缓存规范
category: cache_rule
rule_type: redis_policy
keywords: [redis_key, expire_seconds, redis]
---
## Redis 缓存规范
1. Key 命名格式统一为 `biz:module:id`
2. 必须设置合理的过期时间 `expire_seconds`，严禁永不过期的热点 Key
"""
        parsed_chunks = MarkdownASTParser.parse_document(sample_doc_with_new_rule)
        self.assertEqual(len(parsed_chunks), 2)

        redis_chunk = parsed_chunks[1]
        self.assertEqual(redis_chunk.chunk_id, "chunk_redis_rules")
        self.assertEqual(redis_chunk.metadata.category, "cache_rule")
        self.assertEqual(redis_chunk.metadata.section, "Redis 缓存规范")
        # 验证自动抽取反引号关键词 `biz:module:id`
        self.assertIn("biz:module:id", redis_chunk.keywords)
        self.assertIn("expire_seconds", redis_chunk.keywords)
        print("[PASS] 动态扩展新规范章节与反引号关键词自动提取验证成功！")

    def test_03_fallback_pure_markdown_headings(self):
        """测试 3: 验证对纯 Markdown (无 Frontmatter) 的 H2 自动降级切块"""
        pure_md = """# 敏捷开发规范

## 分支管理规范
Feature 分支必须从 dev 拉取。

## 代码评审规范
必须至少有 1 位 Reviewer 通过。
"""
        fallback_chunks = MarkdownASTParser.parse_document(pure_md, default_doc_title="敏捷开发规范")
        self.assertEqual(len(fallback_chunks), 2)
        self.assertEqual(fallback_chunks[0].chunk_id, "chunk_auto_1")
        self.assertIn("分支管理规范", fallback_chunks[0].metadata.heading_path)
        self.assertEqual(fallback_chunks[1].chunk_id, "chunk_auto_2")
        self.assertIn("代码评审规范", fallback_chunks[1].metadata.heading_path)
        print("[PASS] 纯 Markdown 无 Frontmatter 自动降级切块验证成功！")


if __name__ == "__main__":
    unittest.main()
