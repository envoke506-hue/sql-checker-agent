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
        【知识库摄取核心主入口】
        解析整篇 Markdown 规范文档，根据 YAML Frontmatter 语法边界动态切割、
        抽取元数据、提炼检索关键词，并组装为符合 RAG 双轨设计标准的 Chunk 实体列表。

        【执行流程概述】
        1. 语法边界探测：利用正则表达式扫描所有的 `--- ... ---` YAML Frontmatter 区域；
        2. 降级保护：若文档未配置任何 Frontmatter，平滑降级为按 Markdown 二级标题 (##) 自然切分；
        3. 遍历每个章节切片：
           - 提取当前章节对应的原始 YAML 字符串与正文 Markdown 区域；
           - 安全反序列化 YAML（容错机制：格式损坏时回退为空字典，不阻断主流程）；
           - 推导与补齐核心元数据（chunk_id、层级面包屑路径 heading_path、规则类别 category 等）；
           - 双重抽取专有名词关键词：合并 Frontmatter 显式声明的词表与正文中反引号代码词，专供 BM25 稀疏检索；
           - 践行“双轨设计”：
             * display_text 保持纯净 Markdown 正文（面向大模型 Prompt 与用户前端 UI，无人工标签干扰）；
             * embedding_text 头部拼接全局面包屑路径（作为高维向量空间的“语义检索钩子”，提高余弦相似度召回率）；
        4. 实例化并返回强类型的 `List[Chunk]`。

        :param markdown_content: 原始 Markdown 完整文本（通常从规范 .md 文件读取）
        :param default_doc_title: 源文档默认标题，缺省为 "数据库规范"
        :param default_source_file: 源文件默认名称，缺省为 "数据库规范.md"
        :return: 组装就绪的 Chunk 实体列表，可直接用于向量化与倒排索引构建
        """
        chunks: List[Chunk] = []

        # =========================================================================
        # 步骤 1: 扫描文档中所有的 YAML Frontmatter 匹配项 (以 --- 开头并以 --- 结尾)
        # =========================================================================
        matches = list(cls.FRONTMATTER_SPLIT_PATTERN.finditer(markdown_content))

        # =========================================================================
        # 步骤 2: 降级容错机制 (Graceful Fallback)
        # 若外部输入的是未标注 Frontmatter 的纯自然 Markdown，自动按 H2 (##) 进行降级切块
        # =========================================================================
        if not matches:
            return cls._fallback_split_by_headings(
                markdown_content,
                default_doc_title=default_doc_title,
                default_source_file=default_source_file
            )

        # =========================================================================
        # 步骤 3: 循环遍历扫描到的每个规范切片
        # =========================================================================
        for i, match in enumerate(matches):
            # 3.1 提取 Frontmatter 内部的 YAML 文本
            raw_yaml = match.group(1).strip()

            # 3.2 计算当前切片正文 (Body) 的起止字符偏移量
            # 正文起点：当前 Frontmatter 结束位置 (match.end())
            # 正文终点：下一个 Frontmatter 的开始位置，若已经是最后一个切片，则截取到文档末尾
            start_body = match.end()
            end_body = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_content)

            # 3.3 剥离首尾空白字符，获取当前章节纯正文
            body_text = markdown_content[start_body:end_body].strip()
            if not body_text:
                # 若章节正文为空（仅有元数据无正文），跳过该无效切片
                continue

            # ---------------------------------------------------------------------
            # 3.4 解析 YAML 元数据 (带异常防御，保证局部语法错误不导致全量解析崩溃)
            # ---------------------------------------------------------------------
            try:
                meta_dict = yaml.safe_load(raw_yaml) or {}
            except Exception:
                # 若 YAML 语法解析失败，回退为空字典，依靠后续默认值兜底
                meta_dict = {}

            # ---------------------------------------------------------------------
            # 3.5 提取与推导元数据字段 (Metadata Derivation)
            # 优先采用 YAML 显式声明的值；未声明时自动从正文或上下文推导
            # ---------------------------------------------------------------------
            # 切块全局唯一 ID (如 chunk_naming_rules)
            chunk_id = meta_dict.get("chunk_id") or f"chunk_section_{i + 1}"
            
            # 所属小节标题 (未声明则通过正则抓取正文中的第一个 Markdown 标题，如 '命名规范')
            section = meta_dict.get("section") or cls._extract_first_heading(body_text) or f"小节_{i + 1}"
            
            # 面包屑层级路径 (如 '数据库规范 > 命名规范 > 规则清单与反例')，为 RAG 提供全局位置坐标
            heading_path = meta_dict.get("heading_path") or f"{default_doc_title} > {section}"
            
            # 规范业务分类 (如 naming, template, ddl_rule 等)
            category = meta_dict.get("category") or "general"
            
            # 细分规则类型 (如 naming_rule, sql_template, database_rule 等)
            rule_type = meta_dict.get("rule_type") or "general"
            
            # 规范版本号与访问控制列表 (ACL)
            version = meta_dict.get("version") or "v1.0"
            acl = meta_dict.get("acl") or ["all_staff"]

            # 构造不可变的 ChunkMetadata 元数据对象
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

            # ---------------------------------------------------------------------
            # 3.6 专有名词与关键词双重抽取 (供 BM25 稀疏检索使用)
            # 来源 1: Frontmatter 中人工声明的关键词 (如 'lower_snake_case', 'decimal(20, 6)')
            # 来源 2: 正文中被反引号包裹的代码词 (如 `is_deleted`、`TINYINT(4)`)，通过正则自适应抽词
            # ---------------------------------------------------------------------
            declared_keywords: List[str] = meta_dict.get("keywords") or []
            auto_keywords = cls._extract_inline_keywords(body_text)
            
            # 合并关键词并执行大小写不敏感去重，同时保持声明词的原始顺序
            combined_keywords: List[str] = []
            seen = set()
            for kw in declared_keywords + auto_keywords:
                clean_kw = str(kw).strip()
                if clean_kw and clean_kw.lower() not in seen:
                    seen.add(clean_kw.lower())
                    combined_keywords.append(clean_kw)

            # ---------------------------------------------------------------------
            # 3.7 双轨文本生成 (Dual Representation - 核心架构设计)
            # ---------------------------------------------------------------------
            # 轨 1: display_text (纯净正文)
            # 专供【推理大模型 (DeepSeek)】阅读以及【前端 Web UI】呈现。
            # 必须保持纯净干净的 Markdown 排版，严禁注入人工系统标签，避免污染 Prompt、浪费 Token
            # 或引发大模型复读内部标签导致格式歧义；同时供 DoubleCheckVerifier 进行规则反向断言。
            display_text = body_text

            # 轨 2: embedding_text (语义检索钩子)
            # 专供【本地向量模型 (Ollama qwen3-embedding:4b)】计算稠密向量。
            # 在正文头部强制拼接全局层级面包屑路径 (heading_path)，使其作为高维空间中的“语义锚点钩子”。
            # 即使正文中缺少“数据库”等宏观字眼，也能牢牢锚定在对应领域向量子空间，大幅提升检索召回率。
            # 仅在离线建索引期使用一次存为 dense_vectors.npy，后续在线审查期间终身不再被业务读取。
            embedding_text = f"【规范层级】{heading_path}\n{display_text}"

            # ---------------------------------------------------------------------
            # 3.8 组装并追加标准领域实体 Chunk
            # ---------------------------------------------------------------------
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
