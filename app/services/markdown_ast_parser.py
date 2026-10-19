"""
通用 Markdown AST 与 Frontmatter 结构化解析器 (Markdown AST Parser)

【企业级架构知识点说明】
1. Docs as Code (规范即代码):
   - 彻底摒弃在业务代码中硬编码规范文本或编写脆弱定制正则的反模式。
   - 采用业界成熟的 YAML Frontmatter + Markdown 组合范式 (如 Docusaurus、VitePress、Kubernetes 文档体系)：
     头部为机器理解的强类型 YAML 声明 (元数据、ID、规则分类、BM25 专有名词)；
     正文为人类友好的标准 Markdown (保留代码高亮、图表、正反例示范)。
2. 通用抽象与无状态设计:
   - 解析器本身完全与特定业务解耦 (不包含任何数据库或 SQL 特征业务词)，可通用于任意 Markdown 规范切块；
   - 具备自适应关键词抽取器，自动提取代码反引号中的专有标识并动态丰富 BM25 词表；
   - 自动生成符合 RAG 向量召回标准的 `embedding_text` (头部注入层级面包屑)。
"""

import re
from typing import Any, Dict, List, Optional
import yaml

from app.models.entity.chunk import Chunk, ChunkMetadata


class MarkdownASTParser:
    """
    通用 Markdown 文档结构化解析器
    """

    # 匹配 YAML Frontmatter 区域的正则表达式:
    # 匹配以 --- 开头并以 --- 结尾的独立块
    FRONTMATTER_SPLIT_PATTERN = re.compile(
        r"(?:^|\n)---\s*\n(.*?)\n---\s*\n",
        re.DOTALL
    )

    # 提取正文代码反引号内专有词的正则
    INLINE_CODE_PATTERN = re.compile(r"`([^`\r\n]{2,60})`")

    @classmethod
    def parse_document(
        cls,
        markdown_content: str,
        default_doc_title: str = "数据库规范",
        default_source_file: str = "数据库规范.md"
    ) -> List[Chunk]:
        """
        解析整篇 Markdown 规范文档，根据 YAML Frontmatter 边界动态切割并组装为 Chunk 实体列表

        :param markdown_content: 原始 Markdown 字符串
        :param default_doc_title: 默认文档标题
        :param default_source_file: 默认源文件名称
        :return: 组装好的标准 Chunk 实体列表
        """
        chunks: List[Chunk] = []

        # 查找所有的 Frontmatter 匹配项
        matches = list(cls.FRONTMATTER_SPLIT_PATTERN.finditer(markdown_content))

        if not matches:
            # 兜底处理：若文档完全未标注 Frontmatter，按顶级 H2 标题进行自然切分
            return cls._fallback_split_by_headings(
                markdown_content,
                default_doc_title=default_doc_title,
                default_source_file=default_source_file
            )

        for i, match in enumerate(matches):
            raw_yaml = match.group(1).strip()
            start_body = match.end()
            end_body = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_content)

            body_text = markdown_content[start_body:end_body].strip()
            if not body_text:
                continue

            # 1. 解析 YAML 元数据
            try:
                meta_dict = yaml.safe_load(raw_yaml) or {}
            except Exception as e:
                meta_dict = {}

            # 2. 提取/推导元数据字段
            chunk_id = meta_dict.get("chunk_id") or f"chunk_section_{i + 1}"
            section = meta_dict.get("section") or cls._extract_first_heading(body_text) or f"小节_{i + 1}"
            heading_path = meta_dict.get("heading_path") or f"{default_doc_title} > {section}"
            category = meta_dict.get("category") or "general"
            rule_type = meta_dict.get("rule_type") or "general"
            version = meta_dict.get("version") or "v1.0"
            acl = meta_dict.get("acl") or ["all_staff"]

            metadata = ChunkMetadata(
                doc_id=meta_dict.get("doc_id", "spec-mysql-database-2026"),
                doc_title=meta_dict.get("doc_title", default_doc_title),
                source_file=meta_dict.get("source_file", default_source_file),
                heading_path=heading_path,
                section=section,
                category=category,
                rule_type=rule_type,
                version=version,
                acl=acl
            )

            # 3. 动态提取与富集 keywords
            declared_keywords: List[str] = meta_dict.get("keywords") or []
            auto_keywords = cls._extract_inline_keywords(body_text)
            
            # 去重合并，保留 Frontmatter 声明的优先级
            combined_keywords: List[str] = []
            seen = set()
            for kw in declared_keywords + auto_keywords:
                clean_kw = str(kw).strip()
                if clean_kw and clean_kw.lower() not in seen:
                    seen.add(clean_kw.lower())
                    combined_keywords.append(clean_kw)

            # 4. 生成双轨文本 (embedding_text 与 display_text 职责分离)
            # display_text: 供大模型 Prompt 阅读与前端呈现的纯净正文，严禁人工标签污染，避免大模型产生格式歧义
            display_text = body_text
            # embedding_text: 作为语义钩子，头部拼入层级面包屑路径，专供 Ollama 向量模型计算，大幅提升召回准确率
            embedding_text = f"【规范层级】{heading_path}\n{display_text}"

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    embedding_text=embedding_text,
                    display_text=display_text,
                    metadata=metadata,
                    keywords=combined_keywords
                )
            )

        return chunks

    @classmethod
    def _extract_first_heading(cls, text: str) -> Optional[str]:
        """提取正文中的第一个 Markdown 标题文本"""
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#"):
                clean_title = line.lstrip("#").strip()
                clean_title = re.sub(r"[\*\_`]", "", clean_title)  # 移除强调符
                return clean_title
        return None

    @classmethod
    def _extract_inline_keywords(cls, text: str) -> List[str]:
        """从正文中动态抽取反引号内的代码专有名词"""
        keywords = []
        for match in cls.INLINE_CODE_PATTERN.finditer(text):
            kw = match.group(1).strip()
            # 过滤常见语法保留符号或过短单词
            if len(kw) >= 2 and not kw.startswith("...") and kw not in keywords:
                keywords.append(kw)
        return keywords

    @classmethod
    def _fallback_split_by_headings(
        cls,
        text: str,
        default_doc_title: str,
        default_source_file: str
    ) -> List[Chunk]:
        """兜底逻辑：若无 Frontmatter 时基于 H2 标题进行自然切块"""
        h2_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        matches = list(h2_pattern.finditer(text))
        if not matches:
            # 无法识别 H2 时整体作为一个 Chunk
            meta = ChunkMetadata(
                heading_path=default_doc_title,
                section=default_doc_title,
                category="general"
            )
            return [
                Chunk(
                    chunk_id="chunk_entire_doc",
                    embedding_text=f"【规范层级】{default_doc_title}\n{text}",
                    display_text=text,
                    metadata=meta,
                    keywords=cls._extract_inline_keywords(text)
                )
            ]

        chunks = []
        for i, match in enumerate(matches):
            section_title = match.group(1).strip().replace("**", "").replace("`", "")
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()

            meta = ChunkMetadata(
                heading_path=f"{default_doc_title} > {section_title}",
                section=section_title,
                category="general"
            )
            chunks.append(
                Chunk(
                    chunk_id=f"chunk_auto_{i + 1}",
                    embedding_text=f"【规范层级】{default_doc_title} > {section_title}\n{body}",
                    display_text=body,
                    metadata=meta,
                    keywords=cls._extract_inline_keywords(body)
                )
            )
        return chunks
