"""
切块实体与正文持久化仓储 (Doc Store Repository)

【架构知识点说明】
- 向量库通常只存储向量和 ID，不适宜存储超长正文；
- DocStore 负责持久化完整的 `Chunk` 实体（含 display_text 和元数据），
  在检索出候选 chunk_id 后，能以 O(1) 的时间复杂度调取出完整的正文送给大模型。
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.models.entity.chunk import Chunk


class DocStoreRepository:
    """
    负责知识库切块实体与元信息的持久化与基于 ID 的快速查找
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.settings = get_settings()
        self.storage_dir = Path(storage_dir or self.settings.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.store_file = self.storage_dir / "chunks_store.json"
        self.meta_file = self.storage_dir / "index_meta.json"

        # 内存映射字典: {chunk_id: Chunk}
        self.chunk_map: Dict[str, Chunk] = {}
        # 索引全局元数据: {doc_hash, last_updated, chunk_count...}
        self.metadata: Dict = {}

    def is_empty(self) -> bool:
        """检查当前内存中是否为空"""
        return len(self.chunk_map) == 0

    def save(self, chunks: List[Chunk], meta_info: Dict) -> None:
        """
        保存所有切块实体与索引全局元数据
        """
        self.chunk_map = {c.chunk_id: c for c in chunks}
        self.metadata = meta_info

        # 1. 序列化切块实体列表
        serializable_chunks = [c.model_dump() for c in chunks]
        with open(self.store_file, "w", encoding="utf-8") as f:
            json.dump(serializable_chunks, f, ensure_ascii=False, indent=2)

        # 2. 序列化全局元数据 (包含文件哈希与更新时间)
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def load(self) -> bool:
        """
        从磁盘加载已持久化的切块实体与元数据
        """
        if not self.store_file.exists() or not self.meta_file.exists():
            return False

        try:
            with open(self.store_file, "r", encoding="utf-8") as f:
                raw_chunks = json.load(f)
                self.chunk_map = {item["chunk_id"]: Chunk(**item) for item in raw_chunks}

            with open(self.meta_file, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

            return True
        except Exception:
            return False

    def exists(self) -> bool:
        """检查磁盘持久化文件是否存在"""
        return self.store_file.exists() and self.meta_file.exists()

    def get_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """根据 chunk_id 获取切块完整对象 (若内存为空则自动从磁盘加载)"""
        if self.is_empty() and self.exists():
            self.load()
        return self.chunk_map.get(chunk_id)

    def get_all(self) -> List[Chunk]:
        """获取所有切块列表 (若内存为空则自动从磁盘加载)"""
        if self.is_empty() and self.exists():
            self.load()
        return list(self.chunk_map.values())

    def get_metadata(self) -> Dict:
        """获取索引元信息 (若内存为空则自动从磁盘加载)"""
        if not self.metadata and self.exists():
            self.load()
        return self.metadata
