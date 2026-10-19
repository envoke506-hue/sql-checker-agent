"""反向案例库结构校验脚本

用法：
    python doc/negative_cases/validate_cases.py

校验目标（不依赖任何外部 SQL 解析库）：
1. 每条案例的元信息完整：违反条款 / 命中规则 / 级别 / 依据切块；
2. 每条案例恰好有一个 ```sql 代码块；
3. SQL 括号配对，且按 BEGIN...END 感知切分后没有残缺语句；
4. 可选：若仓库内的 SqlFeatureExtractor 可导入，输出每条案例命中的静态特征。
"""

import importlib.util
import re
import sys
from pathlib import Path

CASE_FILE_PATTERN = re.compile(r"^\d\d_.*\.md$")
REQUIRED_META = ("违反条款", "命中规则", "级别", "依据切块")

# 由案例的「命中规则」文字推断该案例期望命中的特征槽位。
# 只有槽位与提取器输出对应上的案例，才算「可被静态规则覆盖」；
# 命名/术语类反例映射不到任何槽位，必须交给大模型做语义判定。
RULE_KEY_SLOTS = (
    ("double", {"has_double_type"}),
    ("TINYINT(4)", {"has_tinyint_1"}),
    ("外键", {"has_foreign_key"}),
    ("db_ 前缀", {"no_db_prefix"}),
    ("关键字", {"is_table_keyword"}),
    ("基类字段", {"missing_base_fields", "base_field_type_mismatches"}),
    ("审计字段", {"missing_base_fields"}),
    ("主键", {"base_field_type_mismatches", "no_id_field"}),
    ("表名前缀", {"has_table_prefix_in_column"}),
)


def expected_slots(rule_text: str) -> set:
    slots = set()
    for token, keys in RULE_KEY_SLOTS:
        if token in rule_text:
            slots |= keys
    return slots


def split_statements(sql: str):
    """按分号切分 SQL，但忽略 BEGIN...END 块内部的分号。"""
    statements, buf, depth = [], [], 0
    for line in sql.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if re.match(r"^(BEGIN|START\s+TRANSACTION)\b", upper):
            depth += 1
        buf.append(line)
        if depth > 0 and re.match(r"^END\s*;?$", upper):
            depth -= 1
            if not upper.endswith(";"):
                continue
        if depth == 0:
            joined = "\n".join(buf)
            if ";" in joined:
                statements.append(joined.strip())
                buf = []
    rest = "\n".join(buf).strip()
    if rest:
        statements.append(rest)
    return [s for s in statements if s.strip(";").strip()]


def balanced(sql: str):
    pairs = {")": "(", "]": "["}
    stack = []
    in_str = None
    for ch in sql:
        if in_str:
            if ch == in_str:
                in_str = None
            continue
        if ch in "'\"`":
            in_str = ch
        elif ch in "([":
            stack.append(ch)
        elif ch in ")]":
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack


def parse_cases(text: str):
    cases = []
    for block in re.split(r"^### ", text, flags=re.MULTILINE)[1:]:
        # 案例正文到下一个二级标题（如「本模块合规正例」）为止
        block = re.split(r"^##\s", block, flags=re.MULTILINE)[0]
        title = block.splitlines()[0].strip()
        sqls = re.findall(r"```sql\s*\n(.*?)```", block, re.DOTALL)
        cases.append({"title": title, "body": block, "sqls": sqls})
    return cases


def load_extractor(repo_root: Path):
    """直接按文件路径加载 SqlFeatureExtractor，避免触发 app 包的重量级依赖。"""
    module_path = repo_root / "app" / "services" / "sql_feature_extractor.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("_negative_case_extractor", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:  # pragma: no cover - 依赖缺失时降级为纯结构校验
        return None
    return module.SqlFeatureExtractor()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent
    extractor = load_extractor(root.parent.parent)

    detail = "--detail" in sys.argv
    total, problems, detectable = 0, [], 0
    hits_by_case = {}
    for path in sorted(root.glob("*.md")):
        if not CASE_FILE_PATTERN.match(path.name):
            continue
        for case in parse_cases(path.read_text(encoding="utf-8")):
            total += 1
            where = f"{path.name} :: {case['title']}"
            for key in REQUIRED_META:
                if f"**{key}**" not in case["body"]:
                    problems.append(f"{where} 缺少元信息 `{key}`")
            if len(case["sqls"]) != 1:
                problems.append(f"{where} 期望 1 个 sql 代码块，实际 {len(case['sqls'])}")
                continue
            sql = case["sqls"][0]
            if not balanced(sql):
                problems.append(f"{where} 括号不配对")
            for stmt in split_statements(sql):
                if not stmt.rstrip().endswith(";"):
                    problems.append(f"{where} 语句未以分号结尾: {stmt.strip()[:60]}")
            if extractor is not None:
                features = extractor.extract_features(sql)
                fired = set()
                if features.has_foreign_key:
                    fired.add("has_foreign_key")
                if features.has_double_type:
                    fired.add("has_double_type")
                if features.has_tinyint_1:
                    fired.add("has_tinyint_1")
                if not features.has_db_prefix:
                    fired.add("no_db_prefix")
                if features.is_table_keyword:
                    fired.add("is_table_keyword")
                if features.redundant_columns:
                    fired.add("has_table_prefix_in_column")
                if features.missing_base_fields:
                    fired.add("missing_base_fields")
                if features.base_field_type_mismatches:
                    fired.add("base_field_type_mismatches")
                if not features.has_id_primary_key:
                    fired.add("no_id_field")

                rule_match = re.search(r"\*\*命中规则\*\*：(.+)", case["body"])
                slots = expected_slots(rule_match.group(1) if rule_match else "")
                matched = sorted(slots & fired)
                hits_by_case[where] = (slots, matched)
                if matched:
                    detectable += 1

    print(f"案例总数: {total}")
    print(f"结构问题: {len(problems)}")
    for item in problems:
        print("  -", item)
    if extractor is not None:
        print(f"可被提取器特征覆盖的规则域: {detectable}/{total}")
        print(f"需大模型语义判定: {total - detectable}/{total}")
        if detail:
            print("--- 明细 (无 [x] 的案例需依赖 LLM 语义判定) ---")
            for name, (slots, matched) in hits_by_case.items():
                mark = "x" if matched else " "
                note = f"命中 {', '.join(matched)}" if matched else "规则域不在提取器特征内"
                print(f"  [{mark}] {name} | {note}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
