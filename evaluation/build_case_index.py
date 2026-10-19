"""反向案例索引构建脚本 (评测语料装载器)

用法：
    python evaluation/build_case_index.py

职责：
    把 doc/negative_cases/*.md 中的 76 条反例（以及各模块末尾的「合规正例」对照组）
    解析成一份**唯一可信的结构化索引** `evaluation/negative_cases_index.json`。

为什么要有这一层：
    多个子代理要并行执行不同分片。如果每个子代理各自去正则解析 Markdown，一旦解析口径
    出现细微差异，分片之间的结果就不可比。因此由主代理一次性生成索引，所有分片只读同一份
    JSON，保证每条案例的输入 SQL 完全一致、可复现。

输出字段：
    case_id            案例编号 (N-01 / T-03 / M-20 / D-15 / F-05 / P-01)
    kind               negative (反例) / positive (合规对照组)
    module             所属规范模块
    title              案例标题
    clause             违反条款原文
    expected_rule_names 期望审查系统报出的 rule_name 列表
    expected_severity  期望级别 ERROR / WARN
    expected_chunks    依据切块 chunk_id 列表
    sql                可直接提交审查接口的完整 DDL
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "doc" / "negative_cases"
OUT_PATH = Path(__file__).resolve().parent / "negative_cases_index.json"

CASE_FILE_PATTERN = re.compile(r"^(\d\d)_(.+)\.md$")

# 模块文件 -> (模块键, 模块中文名, 正例编号)
MODULE_MAP = {
    "01_naming": ("naming", "命名规范", "P-01"),
    "02_terminology": ("terminology", "名词术语", "P-02"),
    "03_table_template": ("table_template", "建表模板", "P-03"),
    "04_database_rules": ("database_rules", "建库规范", "P-04"),
    "05_field_and_index": ("field_and_index", "字段与索引", "P-05"),
}

META_PATTERNS = {
    "clause": re.compile(r"^- \*\*违反条款\*\*：(.+)$", re.MULTILINE),
    "rule": re.compile(r"^- \*\*命中规则\*\*：(.+)$", re.MULTILINE),
    "severity": re.compile(r"^- \*\*级别\*\*：(.+)$", re.MULTILINE),
    "chunks": re.compile(r"^- \*\*依据切块\*\*：(.+)$", re.MULTILINE),
}

BACKTICK = re.compile(r"`([^`]+)`")


def _find(pattern_key: str, body: str) -> str:
    match = META_PATTERNS[pattern_key].search(body)
    return match.group(1).strip() if match else ""


def split_cases(text: str):
    """按 `### ` 切分案例块；每块到下一个 `## ` 为止（过滤掉「本模块合规正例」段）。"""
    blocks = re.split(r"^### ", text, flags=re.MULTILINE)[1:]
    for block in blocks:
        yield re.split(r"^##\s", block, flags=re.MULTILINE)[0]


def split_positive_section(text: str):
    """取出末尾 `## 本模块合规正例` 段落（若存在）。"""
    parts = re.split(r"^##\s+本模块合规正例\s*$", text, flags=re.MULTILINE)
    return parts[1] if len(parts) > 1 else ""


def parse_module(path: Path):
    key = path.stem
    module_key, module_name, positive_id = MODULE_MAP[key]
    raw = path.read_text(encoding="utf-8")
    cases = []

    for block in split_cases(raw):
        heading = block.splitlines()[0].strip()
        id_match = re.match(r"^([A-Z]+-\d+)\s+(.*)$", heading)
        if not id_match:
            raise ValueError(f"{path.name}: 无法从标题解析案例编号 -> {heading!r}")
        case_id, title = id_match.group(1), id_match.group(2).strip()

        sqls = re.findall(r"```sql\s*\n(.*?)```", block, re.DOTALL)
        if len(sqls) != 1:
            raise ValueError(f"{path.name}::{case_id} 期望 1 个 sql 代码块，实际 {len(sqls)}")

        severity_raw = _find("severity", block)
        severity = "ERROR" if severity_raw.startswith("ERROR") else "WARN"

        cases.append({
            "case_id": case_id,
            "kind": "negative",
            "module": module_key,
            "module_name": module_name,
            "source_file": path.name,
            "title": title,
            "clause": _find("clause", block),
            "expected_rule_names": BACKTICK.findall(_find("rule", block)),
            "expected_severity": severity,
            "expected_chunks": BACKTICK.findall(_find("chunks", block)),
            "sql": sqls[0].strip(),
        })

    positive_block = split_positive_section(raw)
    if positive_block:
        sqls = re.findall(r"```sql\s*\n(.*?)```", positive_block, re.DOTALL)
        for offset, sql in enumerate(sqls, start=1):
            cases.append({
                "case_id": positive_id if offset == 1 else f"{positive_id}-{offset}",
                "kind": "positive",
                "module": module_key,
                "module_name": module_name,
                "source_file": path.name,
                "title": f"{module_name} · 合规正例对照组",
                "clause": "对照条款：本模块全部规范要求均未违反",
                "expected_rule_names": [],
                "expected_severity": "NONE",
                "expected_chunks": [],
                "sql": sql.strip(),
            })

    return cases


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    index = []
    for path in sorted(CASES_DIR.glob("[0-9][0-9]_*.md")):
        if not CASE_FILE_PATTERN.match(path.name):
            continue
        index.extend(parse_module(path))

    ids = [c["case_id"] for c in index]
    if len(ids) != len(set(ids)):
        raise ValueError("案例编号重复，索引不可用")

    negatives = [c for c in index if c["kind"] == "negative"]
    positives = [c for c in index if c["kind"] == "positive"]

    OUT_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"索引文件: {OUT_PATH}")
    print(f"案例总数: {len(index)} (反例 {len(negatives)} / 合规对照组 {len(positives)})")
    by_module = {}
    for case in negatives:
        by_module[case["module_name"]] = by_module.get(case["module_name"], 0) + 1
    for name, count in by_module.items():
        print(f"  - {name}: {count}")
    missing_rule = [c["case_id"] for c in negatives if not c["expected_rule_names"]]
    if missing_rule:
        print(f"[WARN] 缺少「命中规则」的案例: {missing_rule}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
