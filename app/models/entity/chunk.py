"""
知识库切块领域实体 (Chunk Entity)

【架构知识点说明】
- 知识库分块是 RAG 系统的核心领域数据载荷：
  1. ChunkMetadata: 存储溯源、结构、过滤、权限四大元数据。
  2. Chunk: 存储切块正文、小块向量化文本、关联的父块 ID 以及用于稀疏检索的关键词。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """
    切块元数据结构 (严格对应课件第 16 篇规范)
    """
    # 1. 溯源用
    doc_id: str = Field(default="spec-mysql-database-2026", description="源文档唯一标识")
    doc_title: str = Field(default="数据库规范", description="源文档标题")
    source_file: str = Field(default="数据库规范.md", description="源文件名称")

    # 2. 结构用
    heading_path: str = Field(..., description="面包屑层级路径，如 '数据库规范 > 命名规范 > 规则清单'")
    section: str = Field(..., description="直接所属的小节标题")

    # 3. 过滤用
    category: str = Field(..., description="规范分类 (naming / terminology / template / ddl_rule)")
    rule_type: str = Field(default="general", description="细分类型 (field_naming / anti_pattern / table_rule 等)")

    # 4. 权限与版本用
    version: str = Field(default="v1.0", description="规范版本号")
    acl: List[str] = Field(default_factory=lambda: ["all_staff"], description="访问控制标签 (ACL)")


class Chunk(BaseModel):
    """
    标准切块实体 (包含小块向量化、大块送大模型的父子设计)
    """
    chunk_id: str = Field(..., description="切块全局唯一 ID")
    parent_id: Optional[str] = Field(default=None, description="所属父块 ID (若采用父子块架构)")
    
    # 专门用于 Embedding 模型向量化的纯净文本 (头部注入面包屑路径)
    embedding_text: str = Field(..., description="参与向量计算的增强文本")
    
    # 真正喂给大模型并在前端展示的完整上下文正文
    display_text: str = Field(..., description="实际提供给 LLM 组装与展示的正文")
    
    # 丰富的元数据
    metadata: ChunkMetadata = Field(..., description="元数据对象")

    # 向量与关键词辅助
    vector: Optional[List[float]] = Field(default=None, description="计算后的稠密向量 (本地 Qwen3-Embedding:4b 生成)")
    keywords: List[str] = Field(default_factory=list, description="该切块包含的专有名词与核心特征关键词 (供 BM25 检索)")

    @property
    def id(self) -> str:
        """便捷获取切块 ID"""
        return self.chunk_id

    @property
    def title(self) -> str:
        """便捷获取切块小节标题"""
        return self.metadata.section
