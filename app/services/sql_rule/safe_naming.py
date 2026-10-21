"""
安全字段命名与建议生成管道 (Safe Suggestion Pipeline)
确保去前缀、术语纠偏与保留字规避一步到位，杜绝建议相互冲突
"""

import re
from typing import Optional, Set
from app.services.sql_rule.constants import MYSQL_RESERVED_WORDS, TERMINOLOGY_ANTI_PATTERNS


class SafeNamingPipeline:
    """安全字段命名生成器"""

    @staticmethod
    def generate_safe_column_name(
        col_name: str,
        table_prefix: str,
        existing_columns: Set[str]
    ) -> str:
        """
        根据本表前缀剥离并生成完全合规、无冲突的终态字段建议名
        :param col_name: 原始字段名 (如 station_type)
        :param table_prefix: 表名前缀 (如 station_)
        :param existing_columns: 当前表内所有已声明的列名集合 (小写)
        :return: 合法终态建议名 (如 biz_type)
        """
        col_lower = col_name.lower()
        if not col_lower.startswith(table_prefix):
            return col_name

        # 1. 基础剥离表名前缀
        candidate = col_lower[len(table_prefix):]

        # 2. 术语反例纠偏 (如 tel -> phone)
        if candidate in TERMINOLOGY_ANTI_PATTERNS:
            candidate = TERMINOLOGY_ANTI_PATTERNS[candidate]

        # 3. 避免保留关键字冲突 (如 type -> biz_type, desc -> remark)
        if candidate in MYSQL_RESERVED_WORDS:
            if candidate == "type":
                candidate = "biz_type"
            elif candidate == "desc":
                candidate = "remark"
            elif candidate == "status":
                # status 在有些 MySQL 版本是关键字或容易混淆，但规范允许 status
                candidate = "status"
            elif candidate == "time":
                candidate = "biz_time"
            else:
                candidate = f"biz_{candidate}"

        # 4. 避免与表内已有主键 id 重名冲突
        if candidate == "id" and "id" in existing_columns and col_lower != "id":
            # 如果表里已经有主键 id，本字段不能叫 id，避免重名语法报错，规范推荐 code
            candidate = "code"

        return candidate
