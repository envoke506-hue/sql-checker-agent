"""
建表模板 8 大基类字段与主键规范规则
"""

from typing import Dict, List, Set
from app.models.dto.sql_rule import SqlRuleViolation
from app.services.sql_rule.base_rule import BaseSqlRule
from app.services.sql_rule.constants import REQUIRED_BASE_COLUMNS
from app.services.sql_rule.parser import ParsedColumnInfo, ParsedStatementContext


class BaseTemplateRule(BaseSqlRule):
    """
    建表默认字段模板校验 (注释不用强校验):
    必须严格包含 8 大基础字段，且类型与默认值完全对齐规范模板:
    id BIGINT UNSIGNED NOT NULL (PRIMARY KEY)
    version INT NOT NULL DEFAULT 0
    deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0
    disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0
    create_id BIGINT UNSIGNED NOT NULL
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    modify_id BIGINT UNSIGNED NOT NULL
    modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    """
    rule_id = "RULE_BASE_TEMPLATE"
    rule_name = "建表基类模板规范"
    severity = "ERROR"
    category = "sql_template"

    def validate(self, ctx: ParsedStatementContext) -> List[SqlRuleViolation]:
        if ctx.statement_type != "CREATE_TABLE":
            return []

        violations: List[SqlRuleViolation] = []
        cols_by_name: Dict[str, ParsedColumnInfo] = {c.name.lower(): c for c in ctx.columns}

        # 1. 检查主键是否为 id BIGINT UNSIGNED
        id_col = cols_by_name.get("id")
        if not id_col:
            violations.append(
                self.create_violation(
                    ctx=ctx,
                    target_object="PRIMARY KEY (id)",
                    message="建表缺少标准主键字段 'id'，必须使用 'id BIGINT UNSIGNED NOT NULL'",
                    suggested_fix="补充字段: id BIGINT UNSIGNED NOT NULL COMMENT '主键', PRIMARY KEY(id)"
                )
            )
        else:
            if id_col.base_type != "BIGINT" or not id_col.is_unsigned:
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=f"id {id_col.raw_type}",
                        message=f"主键 'id' 类型必须为 BIGINT UNSIGNED，当前为: {id_col.raw_type}",
                        suggested_fix="修改为 id BIGINT UNSIGNED NOT NULL"
                    )
                )
            if not id_col.not_null:
                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object="id",
                        message="主键 'id' 必须声明为 NOT NULL",
                        suggested_fix="追加 NOT NULL 约束"
                    )
                )

        # 2. 检查 7 大通用审计字段是否存在及类型一致性
        audit_fields = [
            "version", "deleted", "disabled",
            "create_id", "create_time", "modify_id", "modify_time"
        ]

        missing_fields: List[str] = []
        for field_name in audit_fields:
            if field_name not in cols_by_name:
                missing_fields.append(field_name)

        if missing_fields:
            violations.append(
                self.create_violation(
                    ctx=ctx,
                    target_object=", ".join(missing_fields),
                    message=f"建表模板缺少必需的基类审计字段: {', '.join(missing_fields)}",
                    suggested_fix="请按照建表模板补充缺失的 7 大基类审计字段"
                )
            )

        # 3. 对已存在的基类字段进行类型、unsigned、not_null 与 default 综合比对 (按字段聚合，避免单字段多条报错)
        for field_name, expected in REQUIRED_BASE_COLUMNS.items():
            if field_name == "id" or field_name not in cols_by_name:
                continue

            actual = cols_by_name[field_name]
            issues = []

            # 比对 base_type
            if actual.base_type != expected["type"]:
                issues.append(f"类型应为 {expected['type']} (当前为: {actual.raw_type})")

            # 比对 length (如 TINYINT(4))
            if expected["length"] is not None:
                exp_len_str = str(expected["length"])
                if not actual.type_args or actual.type_args != [exp_len_str]:
                    issues.append(f"长度应指定为 {expected['type']}({exp_len_str})")

            # 比对 unsigned
            if expected["unsigned"] and not actual.is_unsigned:
                issues.append("缺少 UNSIGNED 修饰")

            # 比对 not null
            if expected["not_null"] and not actual.not_null:
                issues.append("缺少 NOT NULL 约束")

            # 比对 default 值
            if expected["default"] is not None:
                exp_def = expected["default"].upper()
                act_def = (actual.default_val or "").upper()
                if "CURRENT_TIMESTAMP" in exp_def:
                    if "CURRENT_TIMESTAMP" not in act_def:
                        issues.append("默认值应为 DEFAULT CURRENT_TIMESTAMP")
                else:
                    if act_def != exp_def:
                        issues.append(f"默认值应为 DEFAULT {exp_def}")

            if issues:
                # 拼接标准建表声明建议
                std_type = expected["type"]
                if expected["length"]:
                    std_type += f"({expected['length']})"
                if expected["unsigned"]:
                    std_type += " UNSIGNED"
                if expected["not_null"]:
                    std_type += " NOT NULL"
                if expected["default"]:
                    std_type += f" DEFAULT {expected['default']}"

                violations.append(
                    self.create_violation(
                        ctx=ctx,
                        target_object=f"{field_name} {actual.raw_type}",
                        message=f"基类字段 '{field_name}' 定义不符合规范模板: {'; '.join(issues)}",
                        suggested_fix=f"修改为: {field_name} {std_type}",
                        rule_id_override="RULE_BASE_FIELD_MISMATCH",
                        rule_name_override="基类字段定义与模板不符"
                    )
                )

        return violations
