"""
数据库规范结构化切块服务 (Chunking Service - Enterprise Dynamic Edition)

【企业级架构核心知识点】
1. 规范即代码与文档治理闭环 (Docs as Code):
   - 彻底废弃在代码中硬编码千行规范常量的反模式。
   - 委托通用的 `MarkdownASTParser` 从真实《数据库规范.md》源文件中动态解析。
   - 采用标准 YAML Frontmatter 声明元数据、章节分类与专有名词，正文维持高可读性 Markdown 语法树。
2. 增量哈希守卫与零成本冷启动:
   - 读取源文件计算 SHA-256 哈希值，与持久化索引元数据比对。
   - 文档发生任何修改（增删改规则），自动触发向量库与 BM25 增量全量刷新。
"""

import hashlib
from pathlib import Path
from typing import List, Tuple

from app.core.config import get_settings
from app.core.exceptions import SpecNotFoundException
from app.models.entity.chunk import Chunk
from app.services.markdown_ast_parser import MarkdownASTParser


class ChunkingService:
    """
    负责从规范 Markdown 源文档动态解析并构建高质量的标准切块列表
    """

    def __init__(self, spec_doc_path: str = None):
        self.settings = get_settings()
        self.spec_doc_path = Path(spec_doc_path or self.settings.spec_doc_path)

    def read_document_and_hash(self) -> Tuple[str, str]:
        """
        读取源文件并计算 SHA-256 内容哈希 (用于判断是否需要增量重建索引)

        :return: (文档完整纯文本, sha256哈希值)
        """
        if not self.spec_doc_path.exists():
            raise SpecNotFoundException(
                message=f"未找到数据库规范源文件: {self.spec_doc_path}",
                detail=f"请检查路径配置 SPEC_DOC_PATH 是否正确。"
            )

        content = self.spec_doc_path.read_text(encoding="utf-8")
        doc_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return content, doc_hash

    def split_specification(self) -> List[Chunk]:
        """
        对《数据库规范.md》执行基于 AST 与 Frontmatter 的动态结构化切块，
        输出具备语义自闭环与元数据富集的标准 Chunk 实体列表。
        """
        content, _ = self.read_document_and_hash()

        # 委托通用 Markdown AST 解析器进行声明式切分与元数据装配
        chunks = MarkdownASTParser.parse_document(
            markdown_content=content,
            default_doc_title="数据库规范",
            default_source_file=self.spec_doc_path.name
        )

        return chunks
