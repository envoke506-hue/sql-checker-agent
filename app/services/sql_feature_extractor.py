"""
SQL 语法与合规特征提取器 (SQL Feature Extractor)

【课程与业务核心知识点说明 (落地第 18 篇)】
1. 为什么必须做 SQL 意图提取与查询改写 (Query Rewriting):
   - 原始 DDL SQL 包含大量通用语法关键字（CREATE, TABLE, BIGINT, NULL）与符号（括号、分号、逗号）。
   - 如果直接对整段 SQL 文本做 Embedding 向量检索，关键违规特征（如一个隐蔽的 `double` 或 `order_id`）
     会被大量语法符号严重冲淡稀释，导致向量相似度难以排到第一位。
2. 规则特征感知与高靶向性 Query 生成:
   - 本解析器采用轻量高效的正则与模式匹配，深度扫描 SQL 的 5 大核心合规维度：
     ① 表名规范：是否缺少 `db_` 前缀、是否命中保留关键字；
     ② 字段命名：是否出现本表冗余前缀反例（如 order 表出现 order_id）；
     ③ 数据类型：是否出现禁用的 `double`、非法的 `tinyint(1)`，金额是否是 `decimal(20, 6)`；
     ④ 外键禁令：是否定义了 `FOREIGN KEY`；
     ⑤ 基类审计字段：是否缺失 `version`, `deleted`, `disabled`, `create_time`, `modify_time` 等 7 大审计字段。
   - 扫描后自动生成针对性极强的规范检索问句（Targeted Queries），保证 RAG 检索命中率达到 100%。
"""

import re
from typing import Dict, List, Set
from pydantic import BaseModel, Field


class SqlInspectionFeatures(BaseModel):
    """
    SQL 预检提取出的特征要素实体
    """
    table_name: str = Field(default="", description="提取出的数据表名称")
    has_db_prefix: bool = Field(default=True, description="表名是否以规范的 db_ 开头")
    is_table_keyword: bool = Field(default=False, description="表名是否命中了常见保留关键字")
    
    fields: List[str] = Field(default_factory=list, description="提取出的字段名称清单")
    types: List[str] = Field(default_factory=list, description="提取出的字段数据类型清单")
    
    has_foreign_key: bool = Field(default=False, description="是否定义了外键约束 (禁止外键)")
    has_double_type: bool = Field(default=False, description="是否使用了禁用的 double 类型")
    has_tinyint_1: bool = Field(default=False, description="是否使用了易产生语义分歧的 tinyint(1)")
    has_table_prefix_in_column: bool = Field(default=False, description="字段是否包含了本表表名前缀反例 (如 order 表的 order_id)")
    redundant_columns: List[str] = Field(default_factory=list, description="冗余表名前缀的字段名")
    
    missing_base_fields: List[str] = Field(default_factory=list, description="缺失的规范必填基类字段")
    base_field_type_mismatches: List[str] = Field(
        default_factory=list,
        description="已声明但类型与规范模板不符的基类字段 (如 create_id 写成 VARCHAR)"
    )
    has_id_primary_key: bool = Field(default=True, description="是否拥有标准的大整数无符号主键 id")


class SqlFeatureExtractor:
    """
    SQL 语法与合规特征提取器
    """

    # 规范要求的 7 大必须基类字段
    REQUIRED_BASE_FIELDS: Set[str] = {
        "version", "deleted", "disabled",
        "create_id", "create_time", "modify_id", "modify_time"
    }

    # 规范建表模板中各基类字段的数据类型 (用正则，避免 int 误命中 bigint)
    BASE_FIELD_TYPE_PATTERNS: Dict[str, str] = {
        "id": r"\bbigint\s+unsigned\b",
        "version": r"\bint\b",
        "deleted": r"\btinyint\s*\(\s*4\s*\)",
        "disabled": r"\btinyint\s*\(\s*4\s*\)",
        "create_id": r"\bbigint\s+unsigned\b",
        "create_time": r"\bdatetime\b",
        "modify_id": r"\bbigint\s+unsigned\b",
        "modify_time": r"\bdatetime\b",
    }

    # 常见容易被误用作表名的关键字
    RESERVED_KEYWORDS: Set[str] = {
        "order", "user", "group", "select", "delete", "table", "desc", "asc",
        "index", "key", "rank", "limit", "status", "lock", "check", "system"
    }

    def extract_features(self, sql_text: str) -> SqlInspectionFeatures:
        """
        深度解析 SQL 语句并提取合规特征要素
        """
        clean_sql = sql_text.strip()
        features = SqlInspectionFeatures()

        # 1. 提取表名
        # 匹配 CREATE TABLE [IF NOT EXISTS] `?([a-zA-Z0-9_]+)`?
        table_match = re.search(
            r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:[`'\"\s]*)([a-zA-Z0-9_]+)(?:[`'\"\s]*)",
            clean_sql,
            re.IGNORECASE
        )
        if table_match:
            raw_table_name = table_match.group(1).lower()
            features.table_name = raw_table_name
            features.has_db_prefix = raw_table_name.startswith("db_")
            # 去除 db_ 前缀后检查是否是关键字
            pure_name = raw_table_name[3:] if features.has_db_prefix else raw_table_name
            features.is_table_keyword = pure_name in self.RESERVED_KEYWORDS

        # 2. 检查外键禁令 (FOREIGN KEY)
        if re.search(r"\bforeign\s+key\b", clean_sql, re.IGNORECASE):
            features.has_foreign_key = True

        # 3. 检查数据类型 (double 与 tinyint(1))
        if re.search(r"\bdouble\b", clean_sql, re.IGNORECASE):
            features.has_double_type = True
        if re.search(r"\btinyint\s*\(\s*1\s*\)", clean_sql, re.IGNORECASE):
            features.has_tinyint_1 = True

        # 4. 提取各字段名与其类型
        # 截取 CREATE TABLE (...) 括号内部的列定义行
        paren_match = re.search(r"\((.*)\)[^)]*$", clean_sql, re.DOTALL)
        if paren_match:
            body = paren_match.group(1)
            # 按逗号分割每一行声明 (忽略括号内的逗号如 decimal(20, 6))
            lines = re.split(r",\s*(?![^()]*\))", body)
            
            extracted_fields: Set[str] = set()
            field_definitions: Dict[str, str] = {}
            for line in lines:
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                # 跳过 SQL 注释行 (如 "-- 通用审计字段")
                if stripped_line.startswith("--") or stripped_line.startswith("#"):
                    continue
                # 跳过表级约束如 PRIMARY KEY, KEY, CONSTRAINT, UNIQUE
                if re.match(r"^(primary\s+key|key|unique|constraint|index|foreign\s+key)", stripped_line, re.IGNORECASE):
                    continue

                # 提取列名：首个非关键字标识符
                col_match = re.match(r"^[`'\"\s]*([a-zA-Z0-9_]+)[`'\"\s]*\s+([a-zA-Z0-9_]+(?:\([0-9,\s]+\))?)", stripped_line)
                if col_match:
                    col_name = col_match.group(1).lower()
                    col_type = col_match.group(2).lower()
                    extracted_fields.add(col_name)
                    features.fields.append(col_name)
                    features.types.append(col_type)
                    field_definitions[col_name] = re.sub(r"\s+", " ", stripped_line).lower()

            # 5. 检查本表字段前缀反例 (如在 order 表中写了 order_id, order_code)
            if features.table_name:
                pure_name = features.table_name[3:] if features.has_db_prefix else features.table_name
                prefix_pattern = f"{pure_name}_"
                for col in features.fields:
                    # 本表自己的字段前不需要加表名 (如 order 表的 order_id, order_code, order_name, order_money 等均违规)
                    if col.startswith(prefix_pattern):
                        features.has_table_prefix_in_column = True
                        features.redundant_columns.append(col)

            # 6. 检查基类审计字段缺失项
            missing = self.REQUIRED_BASE_FIELDS - extracted_fields
            features.missing_base_fields = sorted(list(missing))

            # 7. 检查已声明的基类字段类型是否与规范模板一致
            #    基础字段类型和 BASE_FIELD_TYPE_PATTERNS 中定义的类型不一致时进行收集
            for field_name, type_pattern in self.BASE_FIELD_TYPE_PATTERNS.items():
                definition = field_definitions.get(field_name)
                if definition and not re.search(type_pattern, definition):
                    features.base_field_type_mismatches.append(field_name)

            # 8. 检查主键是否包含 id
            features.has_id_primary_key = "id" in extracted_fields

        return features

    def generate_retrieval_queries(self, sql_text: str) -> List[str]:
        """
        根据 SQL 特征提取结果，动态生成高命中率的针对性规范检索意图清单
        对应课件第 18 篇：多查询检索与意图分解
        """
        features = self.extract_features(sql_text)
        queries: List[str] = []

        # 意图 1: 外键禁令
        if features.has_foreign_key:
            queries.append("建库规范 表内禁止外键设计 严禁 FOREIGN KEY")

        # 意图 2: double 类型与数据类型规范
        if features.has_double_type:
            queries.append("建库规范 double类型不要用 必须直接用 decimal")

        # 意图 3: tinyint 语义分歧规范
        if features.has_tinyint_1:
            queries.append("建表规范 对于 TINYINT 类型统一使用 TINYINT(4) 规避语义分歧")

        # 意图 4: 本表字段冗余表名前缀反例
        if features.has_table_prefix_in_column:
            queries.append("命名规范 若是本表自己的字段 字段前不需要加表名 反例 order_id 应直接写 id code")

        # 意图 5: 基类必填审计字段与建表模板
        # 字段缺失、主键不合规、或字段虽然存在但类型与模板不符时，都必须把模板条款召回来对照
        if (
            features.missing_base_fields
            or features.base_field_type_mismatches
            or not features.has_id_primary_key
        ):
            queries.append("建表模板 必须严格包含的基础基类字段 version deleted disabled create_time modify_time 主键 id BIGINT UNSIGNED")

        # 意图 6: 表名保留关键字与关联表前缀规范
        if features.is_table_keyword:
            queries.append("建库规范 表与字段不允许用关键字 或者看着像关键字的单词")
        if features.table_name and "relation" in features.table_name and not features.table_name.startswith("r_"): #表名非空，且表名里含有 relation，但又不是以 r_ 开头。
            queries.append("建库规范 关联表以 r_ 开头")

        # 意图 7: 根据表里的字段名和字段类型，判断是否可能涉及“金额/价格/数量/时间/状态/编码”这类业务字段，如果涉及，就往 queries 里追加一条命名规范提示。
        field_types_str = " ".join(features.fields + features.types)
        if any(kw in field_types_str for kw in ["price", "money", "amount", "time", "status", "code"]):
            queries.append("命名规范 单价统一命名后缀 price 金额统一后缀 money 数量后缀 amount 时间后缀 time")

        # 意图 8: 1 个字符与布尔类型规范 (统一 TINYINT(4))
        if re.search(r"\bchar\s*\(\s*1\s*\)|\bvarchar\s*\(\s*1\s*\)", sql_text, re.IGNORECASE):
            queries.append("建表规范 1个字符统一使用 TINYINT(4) 字段设计与类型规则")

        # 意图 9: 外键关联字段命名规范 (表名_字段) 与标准术语
        if any(col in ["uid", "dept", "org", "user", "rel_id"] for col in features.fields):
            queries.append("命名规范 外键关系采用 表名_字段 的命名方式 关联 relation")

        # 兜底查询：若 SQL 非常简单且未触发特殊规则，检索建表与命名通用规范
        if not queries:
            queries.append("数据库建表合规规范 命名规范与建表模板标准")

        return queries
