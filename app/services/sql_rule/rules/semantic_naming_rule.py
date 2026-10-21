"""
第二阶段业务语义与命名风格规范规则
涵盖: 本表去前缀、r_关联表、命名后缀/前缀、三方对接表、标准名词术语与建议项
"""

import re
from typing import Dict, List, Set
from app.models.dto.sql_rule import SqlRuleViolation
from app.services.sql_rule.base_rule import BaseSqlRule
from app.services.sql_rule.constants import TERMINOLOGY_ANTI_PATTERNS
from app.services.sql_rule.parser import ParsedColumnInfo, ParsedStatementContext
from app.services.sql_rule.safe_naming import SafeNamingPipeline


class SemanticNamingRule(BaseSqlRule):
    """
    第二阶段语义与命名规范:
    1. 本表自己的字段前不需要加表名 (如 order 表的 order_code 应直接为 code)
    2. 关联表以 r_ 开头
    3. 单价 price, 金额 money, 数量 amount (严格 decimal)
    4. 编码 code, 时间 time, 排序 sort, 备注 remark, 数量单位 amount_unit
    5. 前缀: biz_, in_, out_
    6. 三方对接表必须包含 system_source 和 data_source
    7. 名词术语字典纠偏 (organization->organ, administrator->admin 等)
    8. 建议项 (WARN): 非负数建议 UNSIGNED, 建议 NOT NULL
    """
    rule_id = "RULE_SEMANTIC_NAMING"
    rule_name = "语义与命名规范"
    severity = "ERROR"
    category = "naming_rule"

    def validate(self, ctx: ParsedStatementContext) -> List[SqlRuleViolation]:
        if ctx.statement_type not in ("CREATE_TABLE", "ALTER_TABLE"):
            return []

        violations: List[SqlRuleViolation] = []

        # 1. 关联表与三方对接表校验 (针对 CREATE TABLE)
        if ctx.statement_type == "CREATE_TABLE" and ctx.main_table:
            raw_table_name = ctx.main_table.name.lower()
            # 剥离通用前缀得到纯表名 (如 t_order -> order)
            pure_table_name = re.sub(r"^(t_|tbl_|r_)", "", raw_table_name)

            # 1.1 关联表以 r_ 开头
            if "relation" in raw_table_name and not raw_table_name.startswith("r_"):
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=ctx.main_table.full_name,
                        message=f"关联表必须以 'r_' 开头，当前为: '{raw_table_name}'",
                        suggested_fix=f"将表名改为: r_{raw_table_name}",
                        rule_id_override="RULE_RELATION_TABLE_R",
                        rule_name_override="关联表必须以 r_ 开头"
                    )
                )

            # 1.2 三方对接表规范 (system_source 与 data_source)
            is_third_party = any(kw in raw_table_name for kw in ["third_", "outer_", "ext_"]) or (
                ctx.table_comment and any(kw in ctx.table_comment for kw in ["第三方", "三方", "外部", "对接"])
            )
            if is_third_party:
                col_names = {c.name.lower() for c in ctx.columns}
                missing_third_cols = []
                if "system_source" not in col_names:
                    missing_third_cols.append("system_source")
                if "data_source" not in col_names:
                    missing_third_cols.append("data_source")
                if missing_third_cols:
                    violations.append(
                        self.create_violation(
                            ctx=ctx,
                            target_object=", ".join(missing_third_cols),
                            message=f"三方对接表必须包含字段: {', '.join(missing_third_cols)} (用于区分对方系统与数据来源)",
                            suggested_fix="在表结构中增加 system_source 和 data_source 字段",
                            rule_id_override="RULE_THIRD_PARTY_TABLE",
                            rule_name_override="三方对接表必须包含来源字段"
                        )
                    )

            # 1.3 本表字段命名: 本表自己的字段前不需要加表名 (如 order 表的 order_code -> code)
            entity_keywords = [pure_table_name]
            # 如果表名由下划线分割，也识别主要实体词
            parts = pure_table_name.split("_")
            for p in parts:
                if len(p) >= 3 and p not in ["info", "detail", "item", "record", "list"]:
                    entity_keywords.append(p)

            existing_cols = {c.name.lower() for c in ctx.columns}
            for col in ctx.columns:
                col_name_lower = col.name.lower()
                for kw in set(entity_keywords):
                    prefix = f"{kw}_"
                    if col_name_lower.startswith(prefix):
                        safe_name = SafeNamingPipeline.generate_safe_column_name(
                            col_name=col.name,
                            table_prefix=prefix,
                            existing_columns=existing_cols
                        )
                        violations.append(
                            self.create_violation(
                                ctx=ctx,
                                target_object=col.name,
                                message=f"字段 '{col.name}' 包含了本表表名前缀 '{kw}_'，违反'本表字段不加表名'规范",
                                suggested_fix=f"去掉表名前缀，直接命名为: {safe_name}",
                                rule_id_override="RULE_NO_TABLE_PREFIX_IN_COLUMN",
                                rule_name_override="本表字段前不加表名",
                                category="naming_rule"
                            )
                        )
                        break

        # 2. 字段级语义规范 (CREATE TABLE 与 ALTER TABLE)
        cols_to_check: List[ParsedColumnInfo] = list(ctx.columns)
        for action in ctx.alter_actions:
            if action.column_info:
                cols_to_check.append(action.column_info)

        for col in cols_to_check:
            col_name_lower = col.name.lower()
            col_tokens = col_name_lower.split("_")

            # 2.1 排序统一命名 sort
            if col_name_lower in ("seq", "sort_no", "order_num", "sort_num"):
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=col.name,
                        message=f"排序字段统一命名为 'sort'，不建议使用 '{col.name}'",
                        suggested_fix="修改字段名为 sort",
                        rule_id_override="RULE_SORT_NAMING",
                        rule_name_override="排序统一命名为 sort"
                    )
                )

            # 2.2 备注统一全名 remark
            if col_name_lower in ("desc", "description", "note", "memo"):
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=col.name,
                        message=f"备注字段统一命名为 'remark'，禁止使用 '{col.name}'",
                        suggested_fix="修改字段名为 remark",
                        rule_id_override="RULE_REMARK_NAMING",
                        rule_name_override="备注统一命名为 remark"
                    )
                )

            # 2.3 单价、金额、数量强制使用 decimal(20, 6)
            if col_name_lower.endswith("_money") or col_name_lower == "money":
                if col.base_type not in ("DECIMAL", "DEC", "NUMERIC"):
                    violations.append(
                        self.create_violation(
                            ctx=ctx,
                            target_object=f"{col.name} {col.raw_type}",
                            message=f"金额类字段 '{col.name}' 必须统一使用 DECIMAL(20, 6) 类型",
                            suggested_fix="修改为 DECIMAL(20, 6)",
                            rule_id_override="RULE_MONEY_DECIMAL",
                            rule_name_override="金额类统一使用 decimal 类型"
                        )
                    )

            if col_name_lower.endswith("_price") or col_name_lower == "price":
                if col.base_type not in ("DECIMAL", "DEC", "NUMERIC"):
                    violations.append(
                        self.create_violation(
                            ctx=ctx,
                            target_object=f"{col.name} {col.raw_type}",
                            message=f"单价类字段 '{col.name}' 必须统一使用 DECIMAL(20, 6) 类型",
                            suggested_fix="修改为 DECIMAL(20, 6)",
                            rule_id_override="RULE_PRICE_DECIMAL",
                            rule_name_override="单价类统一使用 decimal 类型"
                        )
                    )

            if col_name_lower.endswith("_amount") or col_name_lower == "amount":
                if col.base_type not in ("DECIMAL", "DEC", "NUMERIC"):
                    violations.append(
                        self.create_violation(
                            ctx=ctx,
                            target_object=f"{col.name} {col.raw_type}",
                            message=f"数量类计算字段 '{col.name}' 必须统一使用 DECIMAL(20, 6) 类型",
                            suggested_fix="修改为 DECIMAL(20, 6)",
                            rule_id_override="RULE_AMOUNT_DECIMAL",
                            rule_name_override="数量类统一使用 decimal 类型"
                        )
                    )

            # 2.4 名词术语反例映射检查
            for token in col_tokens:
                if token in TERMINOLOGY_ANTI_PATTERNS:
                    recommended = TERMINOLOGY_ANTI_PATTERNS[token]
                    suggested_col = col_name_lower.replace(token, recommended)
                    violations.append(
                        self.create_violation(
                            ctx=ctx,
                            target_object=col.name,
                            message=f"字段中包含非标名词术语 '{token}'，规范标准术语应为 '{recommended}'",
                            suggested_fix=f"将字段改名为规范术语: {suggested_col}",
                            rule_id_override="RULE_TERMINOLOGY",
                            rule_name_override="遵循规范名词术语",
                            category="glossary"
                        )
                    )

            # 2.5 建议性条款 (WARN 级别)
            # 建议 1: 数字类型已知不存在负数的情况下可以加 UNSIGNED
            if col.base_type in ("INT", "BIGINT", "MEDIUMINT", "SMALLINT") and not col.is_unsigned:
                # 排除标准基类 version
                if col_name_lower not in ("version",):
                    violations.append(
                        self.create_violation(
                            ctx=ctx,
                            target_object=f"{col.name} {col.raw_type}",
                            message=f"建议: 字段 '{col.name}' 为正整数类型，已知不存在负数的情况下建议添加 UNSIGNED",
                            suggested_fix=f"建议修改为 {col.base_type} UNSIGNED",
                            severity="WARN",
                            rule_id_override="WARN_UNSIGNED_NUMBER",
                            rule_name_override="数字类型建议使用 UNSIGNED"
                        )
                    )

            # 建议 2: 尽量使用 NOT NULL 或 NOT NULL DEFAULT
            if not col.not_null:
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=col.name,
                        message=f"建议: 字段 '{col.name}' 允许为 NULL，建议尽量使用 NOT NULL 或 NOT NULL DEFAULT 避免索引与逻辑开销",
                        suggested_fix=f"建议在字段后追加 NOT NULL DEFAULT 默认值",
                        severity="WARN",
                        rule_id_override="WARN_NOT_NULL_DEFAULT",
                        rule_name_override="字段尽量使用 NOT NULL 约束"
                    )
                )

        return violations
