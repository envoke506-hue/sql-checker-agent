"""
SQL 规范审查常量定义与字典配置
包括 MySQL 保留字、基类审计字段标准模板、标准名词术语与反例映射
"""

from typing import Any, Dict, Set

# MySQL 官方保留字与高危关键字集合 (统一小写)
MYSQL_RESERVED_WORDS: Set[str] = {
    "accessible", "add", "all", "alter", "analyze", "and", "as", "asc",
    "asensitive", "before", "between", "bigint", "binary", "blob", "both",
    "by", "call", "cascade", "case", "change", "char", "character", "check",
    "collate", "column", "condition", "constraint", "continue", "convert",
    "create", "cross", "cube", "cume_dist", "current_date", "current_time",
    "current_timestamp", "current_user", "cursor", "database", "databases",
    "day_hour", "day_microsecond", "day_minute", "day_second", "dec", "decimal",
    "declare", "default", "delayed", "delete", "dense_rank", "desc", "describe",
    "deterministic", "distinct", "distinctrow", "div", "double", "drop", "dual",
    "each", "else", "elseif", "empty", "enclosed", "escaped", "except", "exists",
    "exit", "explain", "false", "fetch", "first_value", "float", "float4", "float8",
    "for", "force", "foreign", "from", "fulltext", "function", "group", "grouping",
    "groups", "having", "high_priority", "hour_microsecond", "hour_minute",
    "hour_second", "if", "ignore", "in", "index", "infile", "inner", "inout",
    "insensitive", "insert", "int", "int1", "int2", "int3, int4, int8", "integer",
    "interval", "into", "io_after_gtids", "io_before_gtids", "is", "iterate", "join",
    "json_table", "key", "keys", "kill", "lag", "last_value", "lead", "leading",
    "leave", "left", "like", "limit", "linear", "lines", "load", "localtime",
    "localtimestamp", "lock", "long", "longblob", "longtext", "loop", "low_priority",
    "master_bind", "master_ssl_verify_server_cert", "match", "maxvalue",
    "mediumblob", "mediumint", "mediumtext", "middleint", "minute_microsecond",
    "minute_second", "mod", "modifies", "natural", "not", "no_write_to_binlog",
    "nth_value", "ntile", "null", "numeric", "of", "on", "optimize", "optimizer_costs",
    "option", "optionally", "or", "order", "out", "outer", "outfile", "over",
    "partition", "percent_rank", "precision", "primary", "procedure", "purge",
    "range", "rank", "read", "reads", "read_write", "real", "recursive", "references",
    "regexp", "release", "rename", "repeat", "replace", "require", "resignal",
    "restrict", "return", "revoke", "right", "rlike", "row", "rows", "row_number",
    "schema", "schemas", "second_microsecond", "select", "sensitive", "separator",
    "set", "show", "signal", "smallint", "spatial", "specific", "sql", "sqlexception",
    "sqlstate", "sqlwarning", "sql_after_gtids", "sql_before_gtids",
    "sql_big_result", "sql_calc_found_rows", "sql_small_result", "ssl", "starting",
    "stored", "straight_join", "system", "table", "terminated", "then", "tinyblob",
    "tinyint", "tinytext", "to", "trailing", "trigger", "true", "undo", "union",
    "unique", "unlock", "unsigned", "update", "usage", "use", "using", "utc_date",
    "utc_time", "utc_timestamp", "values", "varbinary", "varchar", "varcharacter",
    "varying", "virtual", "when", "where", "while", "window", "with", "write",
    "xor", "year_month", "zerofill", "user", "status", "count", "type", "limit"
}

# 基类必须包含的 8 大标准字段及属性规范
# 格式:
# col_name: {
#   "type": "BIGINT" | "INT" | "TINYINT" | "DATETIME",
#   "length": int | None,
#   "unsigned": bool,
#   "not_null": bool,
#   "default": str | None
# }
REQUIRED_BASE_COLUMNS: Dict[str, Dict[str, Any]] = {
    "id": {
        "type": "BIGINT",
        "length": None,
        "unsigned": True,
        "not_null": True,
        "default": None,
        "is_primary": True,
    },
    "version": {
        "type": "INT",
        "length": None,
        "unsigned": False,
        "not_null": True,
        "default": "0",
        "is_primary": False,
    },
    "deleted": {
        "type": "TINYINT",
        "length": 4,
        "unsigned": True,
        "not_null": True,
        "default": "0",
        "is_primary": False,
    },
    "disabled": {
        "type": "TINYINT",
        "length": 4,
        "unsigned": True,
        "not_null": True,
        "default": "0",
        "is_primary": False,
    },
    "create_id": {
        "type": "BIGINT",
        "length": None,
        "unsigned": True,
        "not_null": True,
        "default": None,
        "is_primary": False,
    },
    "create_time": {
        "type": "DATETIME",
        "length": None,
        "unsigned": False,
        "not_null": True,
        "default": "CURRENT_TIMESTAMP",
        "is_primary": False,
    },
    "modify_id": {
        "type": "BIGINT",
        "length": None,
        "unsigned": True,
        "not_null": True,
        "default": None,
        "is_primary": False,
    },
    "modify_time": {
        "type": "DATETIME",
        "length": None,
        "unsigned": False,
        "not_null": True,
        "default": "CURRENT_TIMESTAMP",
        "is_primary": False,
    },
}

# 常见非标反例词 -> 推荐标准名词术语映射字典
TERMINOLOGY_ANTI_PATTERNS: Dict[str, str] = {
    "organization": "organ",
    "administrator": "admin",
    "state": "status",
    "description": "remark",
    "desc": "remark",
    "note": "remark",
    "memo": "remark",
    "seq": "sort",
    "sort_no": "sort",
    "order_num": "sort",
    "pic": "url",
    "image": "url",
    "img": "url",
    "uid": "user_id",
    "department": "dept",
    "tel": "phone",
    "mobile_phone": "mobile",
    "telephone": "phone",
    "comment_text": "remark",
}
