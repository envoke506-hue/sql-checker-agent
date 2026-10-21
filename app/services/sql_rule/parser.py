"""
SQL AST 语法树解析器 (基于 sqlglot)
负责多语句切分、AST 结构化提取与元数据上下文封装
"""

import re
from typing import Any, Dict, List, Optional, Set
import sqlglot
from sqlglot import exp


class ParsedColumnInfo:
    """结构化列元数据"""
    def __init__(
        self,
        name: str,
        base_type: str,
        raw_type: str,
        is_unsigned: bool,
        type_args: List[str],
        not_null: bool,
        default_val: Optional[str],
        comment: Optional[str],
        has_collate_or_charset: bool,
        ast_node: exp.ColumnDef
    ):
        self.name = name
        self.base_type = base_type.upper()
        self.raw_type = raw_type.upper()
        self.is_unsigned = is_unsigned
        self.type_args = type_args
        self.not_null = not_null
        self.default_val = default_val
        self.comment = comment or ""
        self.has_collate_or_charset = has_collate_or_charset
        self.ast_node = ast_node


class ParsedTableRef:
    """物理表引用"""
    def __init__(self, db: str, name: str, is_primary_target: bool = False):
        self.db = db.strip() if db else ""
        self.name = name.strip() if name else ""
        self.is_primary_target = is_primary_target

    @property
    def full_name(self) -> str:
        if self.db:
            return f"{self.db}.{self.name}"
        return self.name


class ParsedAlterAction:
    """ALTER 动作元数据"""
    def __init__(
        self,
        action_type: str,
        column_name: str,
        column_info: Optional[ParsedColumnInfo],
        position: Optional[str],
        has_after: bool
    ):
        self.action_type = action_type
        self.column_name = column_name
        self.column_info = column_info
        self.position = position
        self.has_after = has_after


class ParsedStatementContext:
    """单条 SQL 语句的解析上下文"""
    def __init__(
        self,
        index: int,
        raw_sql: str,
        ast: Optional[exp.Expression],
        statement_type: str,
        main_table: Optional[ParsedTableRef] = None,
        all_tables: Optional[List[ParsedTableRef]] = None,
        columns: Optional[List[ParsedColumnInfo]] = None,
        engine: Optional[str] = None,
        charset: Optional[str] = None,
        table_comment: Optional[str] = None,
        has_foreign_key: bool = False,
        alter_actions: Optional[List[ParsedAlterAction]] = None,
        parse_error: Optional[str] = None
    ):
        self.index = index
        self.raw_sql = raw_sql
        self.ast = ast
        self.statement_type = statement_type
        self.main_table = main_table
        self.all_tables = all_tables or []
        self.columns = columns or []
        self.engine = engine
        self.charset = charset
        self.table_comment = table_comment
        self.has_foreign_key = has_foreign_key
        self.alter_actions = alter_actions or []
        self.parse_error = parse_error


class SqlAstParser:
    """SQL AST 解析器"""

    @staticmethod
    def parse_sql(sql_text: str) -> List[ParsedStatementContext]:
        """
        切分并解析多条 SQL 语句
        """
        clean_sql = sql_text.strip()
        if not clean_sql:
            return []

        try:
            expressions = sqlglot.parse(clean_sql, read="mysql")
        except Exception as e:
            # 语法解析严重失败时兜底
            return [
                ParsedStatementContext(
                    index=1,
                    raw_sql=clean_sql,
                    ast=None,
                    statement_type="PARSE_ERROR",
                    parse_error=str(e)
                )
            ]

        results: List[ParsedStatementContext] = []
        for idx, expr in enumerate(expressions, 1):
            if expr is None:
                continue
            context = SqlAstParser._build_statement_context(idx, expr)
            results.append(context)

        return results

    @staticmethod
    def _build_statement_context(index: int, expr: exp.Expression) -> ParsedStatementContext:
        """从单个 sqlglot Expression 构建结构化上下文"""
        raw_sql = expr.sql(dialect="mysql")

        # 1. 判断触发器、存储过程、自定义函数禁令
        if isinstance(expr, exp.Command):
            cmd_upper = (expr.this or "").upper() + " " + (expr.expression or "").upper()
            if any(kw in cmd_upper for kw in ["TRIGGER", "PROCEDURE", "FUNCTION"]):
                return ParsedStatementContext(
                    index=index,
                    raw_sql=raw_sql,
                    ast=expr,
                    statement_type="PROHIBITED_OBJECT"
                )
        if isinstance(expr, exp.Create) and expr.kind in ("TRIGGER", "PROCEDURE", "FUNCTION"):
            return ParsedStatementContext(
                index=index,
                raw_sql=raw_sql,
                ast=expr,
                statement_type="PROHIBITED_OBJECT"
            )

        # 2. 提取所有涉及的物理表 (用于库名前缀校验)
        all_tables: List[ParsedTableRef] = []
        raw_tables = list(expr.find_all(exp.Table))
        for t in raw_tables:
            # 过滤派生表/子查询别名
            db_name = t.db
            tbl_name = t.name
            if tbl_name:
                all_tables.append(ParsedTableRef(db=db_name, name=tbl_name))

        # 3. 按语句类型细分提取
        if isinstance(expr, exp.Create) and expr.kind == "TABLE":
            return SqlAstParser._parse_create_table(index, expr, raw_sql, all_tables)

        if isinstance(expr, exp.Alter):
            return SqlAstParser._parse_alter_table(index, expr, raw_sql, all_tables)

        if isinstance(expr, exp.Insert):
            main_t = all_tables[0] if all_tables else None
            return ParsedStatementContext(
                index=index,
                raw_sql=raw_sql,
                ast=expr,
                statement_type="INSERT",
                main_table=main_t,
                all_tables=all_tables
            )

        if isinstance(expr, exp.Update):
            main_t = all_tables[0] if all_tables else None
            return ParsedStatementContext(
                index=index,
                raw_sql=raw_sql,
                ast=expr,
                statement_type="UPDATE",
                main_table=main_t,
                all_tables=all_tables
            )

        if isinstance(expr, exp.Delete):
            main_t = all_tables[0] if all_tables else None
            return ParsedStatementContext(
                index=index,
                raw_sql=raw_sql,
                ast=expr,
                statement_type="DELETE",
                main_table=main_t,
                all_tables=all_tables
            )

        if isinstance(expr, exp.Select):
            return ParsedStatementContext(
                index=index,
                raw_sql=raw_sql,
                ast=expr,
                statement_type="SELECT",
                all_tables=all_tables
            )

        return ParsedStatementContext(
            index=index,
            raw_sql=raw_sql,
            ast=expr,
            statement_type="OTHER",
            all_tables=all_tables
        )

    @staticmethod
    def _parse_create_table(
        index: int,
        expr: exp.Create,
        raw_sql: str,
        all_tables: List[ParsedTableRef]
    ) -> ParsedStatementContext:
        """解析 CREATE TABLE"""
        # 提取目标主表
        main_table: Optional[ParsedTableRef] = None
        target_table_node = expr.find(exp.Table)
        if target_table_node:
            main_table = ParsedTableRef(
                db=target_table_node.db,
                name=target_table_node.name,
                is_primary_target=True
            )

        # 提取表属性 (Engine, Charset, Comment)
        engine: Optional[str] = None
        charset: Optional[str] = None
        table_comment: Optional[str] = None

        props = expr.find(exp.Properties)
        if props:
            for p in props.expressions:
                if isinstance(p, exp.EngineProperty):
                    engine = p.this.name.lower() if hasattr(p.this, "name") else str(p.this).lower()
                elif isinstance(p, exp.CharacterSetProperty):
                    charset = p.this.name.lower() if hasattr(p.this, "name") else str(p.this).lower()
                elif isinstance(p, exp.SchemaCommentProperty):
                    raw_comment = p.this.name if hasattr(p.this, "name") else str(p.this)
                    table_comment = raw_comment.strip("'\"")

        # 提取字段定义 (ColumnDef)
        columns: List[ParsedColumnInfo] = []
        for col in expr.find_all(exp.ColumnDef):
            col_info = SqlAstParser._extract_column_info(col)
            if col_info:
                columns.append(col_info)

        # 提取外键 (Foreign Key)
        has_fk = bool(list(expr.find_all(exp.ForeignKey))) or bool(list(expr.find_all(exp.Reference)))

        return ParsedStatementContext(
            index=index,
            raw_sql=raw_sql,
            ast=expr,
            statement_type="CREATE_TABLE",
            main_table=main_table,
            all_tables=all_tables,
            columns=columns,
            engine=engine,
            charset=charset,
            table_comment=table_comment,
            has_foreign_key=has_fk
        )

    @staticmethod
    def _parse_alter_table(
        index: int,
        expr: exp.Alter,
        raw_sql: str,
        all_tables: List[ParsedTableRef]
    ) -> ParsedStatementContext:
        """解析 ALTER TABLE"""
        main_table: Optional[ParsedTableRef] = None
        target_node = expr.find(exp.Table)
        if target_node:
            main_table = ParsedTableRef(
                db=target_node.db,
                name=target_node.name,
                is_primary_target=True
            )

        alter_actions: List[ParsedAlterAction] = []
        # 遍历 actions
        actions = expr.actions if hasattr(expr, "actions") else []
        for action in actions:
            col_def = action.find(exp.ColumnDef)
            pos_node = action.args.get("position")
            pos_str = str(pos_node).upper() if pos_node else None
            has_after = bool(pos_str and "AFTER" in pos_str)

            col_info = SqlAstParser._extract_column_info(col_def) if col_def else None
            col_name = col_def.name if col_def else ""

            alter_actions.append(
                ParsedAlterAction(
                    action_type="ADD_COLUMN",
                    column_name=col_name,
                    column_info=col_info,
                    position=pos_str,
                    has_after=has_after
                )
            )

        return ParsedStatementContext(
            index=index,
            raw_sql=raw_sql,
            ast=expr,
            statement_type="ALTER_TABLE",
            main_table=main_table,
            all_tables=all_tables,
            alter_actions=alter_actions
        )

    @staticmethod
    def _extract_column_info(col: Optional[exp.ColumnDef]) -> Optional[ParsedColumnInfo]:
        """从 ColumnDef 节点提取结构化字段信息"""
        if not col or not col.name:
            return None

        k = col.kind
        if not k:
            return None

        raw_type = k.this.name if hasattr(k.this, "name") else str(k.this)
        type_args = [
            str(a.this) if hasattr(a, "this") else str(a)
            for a in k.expressions
        ]

        # 判断是否为 unsigned
        # sqlglot 会将 BIGINT UNSIGNED 转换为 UBIGINT, TINYINT UNSIGNED 转换为 UTINYINT
        is_unsigned = raw_type.startswith("U") or any(
            "unsigned" in str(c).lower()
            for c in col.find_all(exp.ColumnConstraint)
        )
        base_type = raw_type[1:] if (raw_type.startswith("U") and len(raw_type) > 1) else raw_type

        # 检查 NOT NULL
        not_null = bool(col.find(exp.NotNullColumnConstraint))

        # 检查 DEFAULT
        default_node = col.find(exp.DefaultColumnConstraint)
        default_val = None
        if default_node:
            default_val = default_node.sql().replace("DEFAULT", "").strip().strip("'\"")

        # 检查 COMMENT
        comment = ""
        for c in col.find_all(exp.CommentColumnConstraint):
            raw_c = c.this.name if hasattr(c.this, "name") else str(c.this)
            comment = raw_c.strip("'\"")

        # 检查是否存在 CHARACTER SET 或 COLLATE 约束
        has_charset_or_collate = bool(
            list(col.find_all(exp.CharacterSetColumnConstraint))
            or list(col.find_all(exp.CollateColumnConstraint))
        )

        return ParsedColumnInfo(
            name=col.name.strip("`'\""),
            base_type=base_type,
            raw_type=raw_type,
            is_unsigned=is_unsigned,
            type_args=type_args,
            not_null=not_null,
            default_val=default_val,
            comment=comment,
            has_collate_or_charset=has_charset_or_collate,
            ast_node=col
        )
