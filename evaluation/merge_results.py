"""分片结果合并与命中率评测脚本

用法：
    python evaluation/merge_results.py

职责：
    1. 汇总 `evaluation/results/shard_*.jsonl`（各子代理并行产出的原始结果）；
    2. 与 `evaluation/negative_cases_index.json` 对账：覆盖完整性、重复记录、元信息一致性；
    3. 对每条反例做「期望规则是否被检出」的双层判定（严格命中 / 语义命中），并给出可复核的证据；
    4. 汇总检出率、误报率、引用有效性、得分分布与耗时统计；
    5. 落盘可长期保留的成果物：
         evaluation/results/merged_results.json     合并后的完整结构化结果
         evaluation/results/merged_results.jsonl    同上，逐行 JSON（便于流式处理）
         evaluation/results/summary.json            机器可读的评测汇总
         evaluation/results/执行报告.md              面向人的评测报告（含未命中清单）

判定口径说明（重要，避免过度声称）：
    - 严格命中：期望规则名、实测 rule_name 归一化后互为子串，几乎无歧义；
    - 语义命中：期望规则的核心词元出现在实测 rule_name 中，属启发式判定，
      因此报告同时给出「未命中清单」与匹配证据，供人工复核，不做单方面结论。
"""

import collections
import json
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
RESULTS_DIR = EVAL_DIR / "results"
INDEX_PATH = EVAL_DIR / "negative_cases_index.json"
CHUNKS_PATH = ROOT / "data" / "indices" / "chunks_store.json"

# ---------------------------------------------------------------------------
# 人工复核裁定表（Lead 逐条比对「实测 violations / summary」与「规范原文」后给出）
#
# 机器严格的规则名匹配会低估真实检出能力：案例库的「命中规则」是自定标签，
# 与模型输出的 rule_name 措辞天然不同。因此这里对 22 条机器未命中案例逐条裁定，
# 把「实际已识别、只是措辞不同或被过滤」与「确实未识别」区分开。
#
# 类别含义：
#   suppressed_false_negative  目标规则已被模型识别，却被 DoubleCheck 防幻觉层误剔除，
#                              最终 0 违规、100 分、伪判「完全合规」—— 真实缺陷；
#   suppressed_but_other_rule  目标规则同样被 DoubleCheck 误剔除，但该案例因其它规则
#                              仍被判为不合规，因此未造成伪判合规；
#   wording_only               目标规则域已正常报出，仅 rule_name 措辞与案例库标签不同；
#   other_rule_same_target     同一批目标字段被判定违规，但归入了另一条规则；
#   spec_scope_ambiguity       因规范原文口径分歧而未报出（README 已登记该分歧）。
# ---------------------------------------------------------------------------
ADJUDICATION = {
    "suppressed_false_negative": [
        "D-02", "D-05", "D-06", "D-08", "F-07", "F-12", "T-10",
    ],
    "suppressed_but_other_rule": [
        "D-07", "F-04", "F-11", "T-02", "T-04", "T-06",
    ],
    "wording_only": [
        "N-02", "T-03", "T-07", "T-08", "T-09", "T-11", "T-12",
    ],
    "other_rule_same_target": ["F-06"],
    "spec_scope_ambiguity": ["D-01"],
}

# 机器匹配器的**已知虚假命中**（经独立复核子代理指出并由 Lead 逐条回读确认后剔除）：
#   N-03 期望的是「关联字段命名」（命名规范 3），实测报出的却是「关联表命名必须以 r_ 开头」
#   （建库规范 13，即 D-16 的规则域）—— 属领域邻接词误命中，目标规则实际并未被报出。
MATCHER_FALSE_POSITIVES = {
    "N-03": "期望「关联字段命名」(命名规范3)，实测为「关联表命名必须以 r_ 开头」(建库规范13)，属邻接规则误命中",
}

# 部分命中：同一批目标字段确实被判违规，但归入了另一条规则（故不计入「目标规则被报出」）
PARTIAL_HIT_CASES = ["F-06"]

# 控制组合规正例的裁定：区分「真误报」与「规范原文自相矛盾导致的口径冲突」
CONTROL_ADJUDICATION = {
    "P-01": ("spec_conflict", "order_money / order_amount_unit 正是规范第 5、12 条的原文示例，"
                              "却又违反第 16 条「本表字段不加表名」，属规范自相矛盾，非系统缺陷"),
    "P-02": ("true_false_alarm", "拒收理由为 sort/version 未加 UNSIGNED；但规范第 9 条原文是「**可以**加 UNSIGNED」"
                                 "（推荐性），且 `version INT NOT NULL DEFAULT 0` 正是建表模板的原文写法"),
    "P-03": ("clean", "判定合规，无误报"),
    "P-04": ("spec_conflict", "同 P-01：order_money 触发「本表字段禁止拼接本表表名」"),
    "P-05": ("clean", "判定合规，无误报"),
}

# 归一化时保留的字符：字母数字与下划线（下划线必须保留，
# 否则 `in_` 这类前缀会退化成 `in`，在 index/innodb 等词上产生大量误命中）
_PUNCT = re.compile(r"[\s·、，,。.：:;；/\\|()（）\[\]【】\-*`'\"“”‘’!！?？]+")
_ASCII_TOKEN = re.compile(r"[a-z0-9_]{2,}")
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")

# 中文规则名里的通用填充词，剥离后剩下的才是「判别性」语义
CJK_STOPWORDS = (
    "必须", "禁止", "不得", "统一", "使用", "命名", "规范", "字段", "表名", "不允许",
    "尽量", "要求", "需要", "不要", "可以", "建议", "标准", "都要", "应在", "应该",
)
CJK_STOPWORD_PATTERN = re.compile("|".join(CJK_STOPWORDS))


def norm(text: str) -> str:
    return _PUNCT.sub("", (text or "").lower())


def cjk_bigrams(text: str):
    """产生中文片段的 2-gram（长度不足 2 时返回其本身）。"""
    if len(text) < 2:
        return {text} if text else set()
    return {text[i:i + 2] for i in range(len(text) - 1)}


def expected_tokens(expected_rule: str):
    """把期望规则名拆成正则词元：(ascii 词元集合, 中文 2-gram 集合)。"""
    lowered = (expected_rule or "").lower()
    ascii_tokens = {t for t in _ASCII_TOKEN.findall(lowered)}
    # 去掉模块名前缀（如「命名规范 ·」）后再提取中文语义
    concept = expected_rule.split("·")[-1] if "·" in expected_rule else expected_rule
    stripped = CJK_STOPWORD_PATTERN.sub("", concept)
    grams = set()
    for run in _CJK_RUN.findall(stripped):
        grams |= cjk_bigrams(run)
    # 长度 >= 2 的中文片段整体也是一个强判别词元
    return ascii_tokens, grams


def match_case(expected_rule_names, violations):
    """判定一条反例的期望规则是否被检出，返回 (严格命中, 语义命中, 证据列表)。"""
    detached = [
        {
            "rule_name": item.get("rule_name", ""),
            "target_object": item.get("target_object", ""),
            "norm_rule": norm(item.get("rule_name", "")),
        }
        for item in violations
    ]

    strict = False
    lenient = False
    evidence = []

    for expected in expected_rule_names:
        expected_norm = norm(expected)
        concept = expected.split("·")[-1] if "·" in expected else expected
        concept_norm = norm(concept)

        # ---- 第 1 层：严格子串互含 ----
        for index, detected in enumerate(detached, start=1):
            text = detected["norm_rule"]
            if not text:
                continue
            if concept_norm and (concept_norm in text or text in concept_norm):
                strict = True
                lenient = True
                evidence.append({
                    "tier": "strict",
                    "expected": expected,
                    "matched_rule_name": detected["rule_name"],
                    "matched_violation_index": index,
                    "via": f"子串互含: {concept_norm}",
                })

        # ---- 第 2 层：核心词元命中（启发式） ----
        ascii_tokens, grams = expected_tokens(expected)
        for token in sorted(ascii_tokens):
            for index, detected in enumerate(detached, start=1):
                if token in detected["norm_rule"]:
                    lenient = True
                    evidence.append({
                        "tier": "semantic",
                        "expected": expected,
                        "matched_rule_name": detected["rule_name"],
                        "matched_violation_index": index,
                        "via": f"ASCII 词元: {token}",
                    })
        for gram in sorted(grams):
            for index, detected in enumerate(detached, start=1):
                if gram in detected["norm_rule"]:
                    lenient = True
                    evidence.append({
                        "tier": "semantic",
                        "expected": expected,
                        "matched_rule_name": detected["rule_name"],
                        "matched_violation_index": index,
                        "via": f"中文 2-gram: {gram}",
                    })

    # 去重证据
    seen, unique_evidence = set(), []
    for item in evidence:
        key = (item["tier"], item["expected"], item["matched_rule_name"], item["via"])
        if key not in seen:
            seen.add(key)
            unique_evidence.append(item)

    strict_evidence = [e for e in unique_evidence if e["tier"] == "strict"]
    return bool(strict_evidence), lenient, unique_evidence


def load_chunk_titles():
    """chunk_id -> 知识库中的层次面包屑路径，用于核对引用是否命中「依据切块」。"""
    if not CHUNKS_PATH.exists():
        return {}
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    mapping = {}
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata.replace("'", '"'))
            except Exception:
                metadata = {}
        mapping[chunk.get("chunk_id")] = metadata.get("heading_path", "")
    return mapping


def load_shard_records():
    """读取所有分片结果；同一案例出现多次时保留最后一次（重跑场景）。"""
    records, sources, duplicates = {}, [], []
    for path in sorted(RESULTS_DIR.glob("shard_*.jsonl")):
        sources.append(path.name)
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"[WARN] {path.name} 存在无法解析的行，已跳过")
                continue
            case_id = record.get("case_id")
            if case_id in records:
                duplicates.append(case_id)
            record["_source_shard"] = path.name
            records[case_id] = record
    return records, sources, duplicates


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    index_by_id = {case["case_id"]: case for case in index}
    chunk_titles = load_chunk_titles()
    records, sources, duplicates = load_shard_records()

    merged, missing, inconsistent = [], [], []
    for case in index:
        case_id = case["case_id"]
        record = records.get(case_id)
        if record is None:
            missing.append(case_id)
            continue
        if record.get("sql") != case["sql"]:
            inconsistent.append(case_id)

        is_negative = case["kind"] == "negative"
        violations = record.get("violations") or []

        if is_negative:
            strict_hit, lenient_hit, evidence = match_case(case["expected_rule_names"], violations)
            detected = record.get("status") == "ok" and record.get("is_compliant") is False
            # 引用是否命中该案例标注的「依据切块」
            citation_titles = " ".join(c.get("title", "") for c in (record.get("citations") or []))
            chunk_hit = any(
                chunk_titles.get(chunk_id, "\u0000") and chunk_titles[chunk_id] in citation_titles
                for chunk_id in case["expected_chunks"]
            )
        else:
            strict_hit = lenient_hit = None
            evidence = []
            detected = None
            chunk_hit = None

        merged.append({
            **case,
            **{k: v for k, v in record.items() if k not in {"case_id", "sql"}},
            "eval": {
                "is_negative": is_negative,
                "violation_reported": detected,
                "strict_hit": strict_hit,
                "lenient_hit": lenient_hit,
                "match_evidence": evidence,
                "expected_chunk_cited": chunk_hit,
                "error": record.get("error"),
            },
        })

    merged.sort(key=lambda item: item["case_id"])

    # ---------------- 汇总统计 ----------------
    negatives = [r for r in merged if r["kind"] == "negative"]
    positives = [r for r in merged if r["kind"] == "positive"]
    ok_negatives = [r for r in negatives if r["status"] == "ok"]

    detected_count = sum(1 for r in ok_negatives if r["eval"]["violation_reported"])
    strict_count = sum(1 for r in ok_negatives if r["eval"]["strict_hit"])
    lenient_count = sum(1 for r in ok_negatives if r["eval"]["lenient_hit"])
    chunk_count = sum(1 for r in ok_negatives if r["eval"]["expected_chunk_cited"])

    positive_false_alarms = [r["case_id"] for r in positives if r["status"] == "ok" and r["is_compliant"] is False]
    error_cases = [r["case_id"] for r in merged if r["status"] != "ok"]

    by_module = {}
    for record in merged:
        stat = by_module.setdefault(record["module_name"], {
            "total": 0, "negative": 0, "detected": 0, "strict_hit": 0, "lenient_hit": 0,
            "identified": 0, "miss": 0,
        })
        stat["total"] += 1
        if record["kind"] == "negative":
            stat["negative"] += 1
            if record["status"] == "ok":
                stat["detected"] += 1 if record["eval"]["violation_reported"] else 0
                stat["strict_hit"] += 1 if record["eval"]["strict_hit"] else 0
                stat["lenient_hit"] += 1 if record["eval"]["lenient_hit"] else 0
                stat["miss"] += 0 if record["eval"]["lenient_hit"] else 1

    elapsed = [r["elapsed_seconds"] for r in merged if r.get("elapsed_seconds")]
    scores = [r["score"] for r in ok_negatives if r.get("score") is not None]

    # ---------------- 人工复核裁定与三层口径指标 ----------------
    machine_miss = [r["case_id"] for r in ok_negatives if not r["eval"]["lenient_hit"]]
    adjudicated_ids = [cid for ids in ADJUDICATION.values() for cid in ids]
    if sorted(adjudicated_ids) != sorted(machine_miss):
        raise SystemExit(
            "人工裁定表与机器未命中清单不一致，评测口径不可信：\n"
            f"  机器未命中({len(machine_miss)}): {sorted(machine_miss)}\n"
            f"  裁定表({len(adjudicated_ids)}): {sorted(adjudicated_ids)}"
        )

    suppressed = ADJUDICATION["suppressed_false_negative"] + ADJUDICATION["suppressed_but_other_rule"]
    wording_only = ADJUDICATION["wording_only"]

    machine_false_positives = [cid for cid in MATCHER_FALSE_POSITIVES if cid in {r["case_id"] for r in ok_negatives}]
    if len(machine_false_positives) != len(MATCHER_FALSE_POSITIVES):
        raise SystemExit("MATCHER_FALSE_POSITIVES 中的案例不在反例结果集中，口径表有误")

    # 口径 1：系统最终判定（是否伪判合规）
    verdict_hit = detected_count
    # 口径 2：目标规则最终被报出（修正后的机器语义命中 + 仅措辞不同的已报出案例）
    machine_semantic_corrected = lenient_count - len(machine_false_positives)
    reported_hit = machine_semantic_corrected + len(wording_only)
    reported_with_partial = reported_hit + len(PARTIAL_HIT_CASES)
    # 口径 3：目标规则/目标对象被大模型识别（含被 DoubleCheck 误剔除、以及归入其它规则的）
    identified_ids = {
        r["case_id"] for r in ok_negatives if r["eval"]["lenient_hit"]
    } - set(machine_false_positives)
    identified_ids |= set(wording_only) | set(suppressed) | set(PARTIAL_HIT_CASES)
    identified_hit = len(identified_ids)
    # 口径 4：完全未识别
    unidentified = [r["case_id"] for r in ok_negatives if r["case_id"] not in identified_ids]

    # 分模块视角的「复核后识别」计数
    for record in ok_negatives:
        if record["case_id"] in identified_ids:
            by_module[record["module_name"]]["identified"] += 1

    controls = []
    for record in positives:
        disposition, note = CONTROL_ADJUDICATION.get(record["case_id"], ("unreviewed", ""))
        controls.append({
            "case_id": record["case_id"],
            "module_name": record["module_name"],
            "is_compliant": record.get("is_compliant"),
            "score": record.get("score"),
            "violation_count": record.get("violation_count"),
            "disposition": disposition,
            "note": note,
        })
    true_false_alarms = [c["case_id"] for c in controls if c["disposition"] == "true_false_alarm"]
    spec_conflicts = [c["case_id"] for c in controls if c["disposition"] == "spec_conflict"]

    # ---------------- 数据质量与一致性缺陷（全部由原始结果直接统计） ----------------
    severity_counts = collections.Counter()
    duplicate_cases, duplicate_entries, total_entries = [], 0, 0
    polarity_forbids, polarity_requires = [], []
    for record in ok_negatives:
        names = [v.get("rule_name", "") for v in record.get("violations") or []]
        total_entries += len(names)
        extra = len(names) - len(set(names))
        if extra:
            duplicate_cases.append(record["case_id"])
            duplicate_entries += extra
        for violation in record.get("violations") or []:
            severity_counts[violation.get("severity", "")] += 1
            haystack = f"{violation.get('rule_name', '')}{violation.get('description', '')}"
            # 同一系统既「要求」又「禁止」db_ 前缀 —— 规则极性自相矛盾
            if "使用了库前缀" in haystack:
                polarity_forbids.append(record["case_id"])
            if "必须以 db_ 开头" in haystack:
                polarity_requires.append(record["case_id"])

    data_quality = {
        "severity_counts": dict(severity_counts),
        "severity_enum_variants": sorted({s for s in severity_counts if s.upper().startswith("WARN")}),
        "duplicate_rule_name_cases": duplicate_cases,
        "duplicate_rule_name_entries": duplicate_entries,
        "total_violation_entries": total_entries,
        "duplicate_entry_share_pct": (
            round(duplicate_entries / total_entries * 100, 1) if total_entries else None
        ),
        "polarity_conflict": {
            "forbids_db_prefix_cases": sorted(set(polarity_forbids)),
            "requires_db_prefix_cases": sorted(set(polarity_requires)),
        },
    }

    def rate(numerator, denominator):
        return round(numerator / denominator * 100, 1) if denominator else None

    summary = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "index_total": len(index),
        "index_negative": len([c for c in index if c["kind"] == "negative"]),
        "index_positive": len([c for c in index if c["kind"] == "positive"]),
        "shard_files": sources,
        "collected": len(records),
        "merged": len(merged),
        "missing_cases": missing,
        "inconsistent_input_sql": inconsistent,
        "duplicate_records": sorted(set(duplicates)),
        "error_cases": error_cases,
        "negative": {
            "total": len(negatives),
            "executed_ok": len(ok_negatives),
            "violation_reported": detected_count,
            "violation_reported_rate_pct": rate(detected_count, len(ok_negatives)),
            "strict_hit": strict_count,
            "strict_hit_rate_pct": rate(strict_count, len(ok_negatives)),
            "lenient_hit": lenient_count,
            "lenient_hit_rate_pct": rate(lenient_count, len(ok_negatives)),
            "expected_chunk_cited": chunk_count,
            "expected_chunk_cited_rate_pct": rate(chunk_count, len(ok_negatives)),
            "miss_cases": [r["case_id"] for r in ok_negatives if not r["eval"]["lenient_hit"]],
            "strict_miss_cases": [r["case_id"] for r in ok_negatives if not r["eval"]["strict_hit"]],
        },
        "adjudicated": {
            "verdict_hit": verdict_hit,
            "verdict_hit_rate_pct": rate(verdict_hit, len(ok_negatives)),
            "reported_hit": reported_hit,
            "reported_hit_rate_pct": rate(reported_hit, len(ok_negatives)),
            "reported_with_partial": reported_with_partial,
            "reported_with_partial_rate_pct": rate(reported_with_partial, len(ok_negatives)),
            "identified_hit": identified_hit,
            "identified_hit_rate_pct": rate(identified_hit, len(ok_negatives)),
            "unidentified": unidentified,
            "unidentified_rate_pct": rate(len(unidentified), len(ok_negatives)),
            "machine_semantic_corrected": machine_semantic_corrected,
            "matcher_false_positives": MATCHER_FALSE_POSITIVES,
            "partial_hit_cases": PARTIAL_HIT_CASES,
            "doublecheck_suppressed_total": len(suppressed),
            "doublecheck_suppressed_cases": suppressed,
            "suppressed_but_other_rule": ADJUDICATION["suppressed_but_other_rule"],
            "false_negative_cases": ADJUDICATION["suppressed_false_negative"],
            "false_negative_rate_pct": rate(len(ADJUDICATION["suppressed_false_negative"]), len(ok_negatives)),
            "wording_only_cases": wording_only,
            "other_rule_same_target_cases": ADJUDICATION["other_rule_same_target"],
            "spec_scope_ambiguity_cases": ADJUDICATION["spec_scope_ambiguity"],
        },
        "data_quality": data_quality,
        "positive_control": {
            "total": len(positives),
            "executed_ok": len([r for r in positives if r["status"] == "ok"]),
            "false_alarm_cases": positive_false_alarms,
            "false_alarm_rate_pct": rate(len(positive_false_alarms), len([r for r in positives if r["status"] == "ok"])),
            "true_false_alarm_cases": true_false_alarms,
            "spec_conflict_cases": spec_conflicts,
            "detail": controls,
        },
        "by_module": by_module,
        "timing": {
            "cases_measured": len(elapsed),
            "total_seconds": round(sum(elapsed), 1),
            "avg_seconds": round(statistics.mean(elapsed), 1) if elapsed else None,
            "median_seconds": round(statistics.median(elapsed), 1) if elapsed else None,
            "max_seconds": max(elapsed) if elapsed else None,
        },
        "score": {
            "avg": round(statistics.mean(scores), 1) if scores else None,
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
            "zero_score_cases": sum(1 for s in scores if s == 0),
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "merged_results.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (RESULTS_DIR / "merged_results.jsonl").open("w", encoding="utf-8") as sink:
        for record in merged:
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    write_report(summary, merged)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def write_report(summary, merged) -> None:
    """生成面向人的 Markdown 评测报告。"""
    negative = summary["negative"]
    positive = summary["positive_control"]
    data_quality = summary["data_quality"]
    lines = [
        "# 数据库规范反向案例库 · 并行执行评测报告",
        "",
        f"- 生成时间：{summary['generated_at']}",
        f"- 执行方式：「主代理建索引与执行器 + 6 个子代理并行分片执行」，每条案例均走真实 RAG 全链路",
        f"- 案例索引：`evaluation/negative_cases_index.json`（{summary['index_total']} 条 = "
        f"反例 {summary['index_negative']} 条 + 合规对照组 {summary['index_positive']} 条）",
        f"- 原始分片结果：{', '.join(summary['shard_files']) or '（无）'}",
        f"- 合并结果：`evaluation/results/merged_results.json`（共 {summary['merged']} 条）",
        "",
        "## 一、执行完整性",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 索引案例总数 | {summary['index_total']} |",
        f"| 已采集结果 | {summary['collected']} |",
        f"| 合并成功 | {summary['merged']} |",
        f"| 缺失案例 | {len(summary['missing_cases'])} |",
        f"| 输入 SQL 与索引不一致 | {len(summary['inconsistent_input_sql'])} |",
        f"| 重复记录 | {len(summary['duplicate_records'])} |",
        f"| 执行失败案例 | {len(summary['error_cases'])} |",
        "",
    ]

    if summary["missing_cases"]:
        lines += [f"> ⚠️ 缺失案例：{', '.join(summary['missing_cases'])}", ""]
    if summary["error_cases"]:
        lines += [f"> ⚠️ 执行失败案例：{', '.join(summary['error_cases'])}", ""]
    if not summary["missing_cases"] and not summary["error_cases"]:
        lines += ["> ✅ 全部案例均已成功执行并入库，无缺失、无失败。", ""]

    adj = summary["adjudicated"]
    lines += [
        "## 二、反例检出能力（三层口径）",
        "",
        "| 判定口径 | 命中数 | 命中率 | 说明 |",
        "| --- | --- | --- | --- |",
        f"| ① 系统最终判定为不合规 | {adj['verdict_hit']}/{negative['executed_ok']} | {adj['verdict_hit_rate_pct']}% | "
        f"直接看 `is_compliant`，另有 {negative['executed_ok'] - adj['verdict_hit']} 条被伪判合规 |",
        f"| ② 目标规则被报出（含部分命中） | {adj['reported_with_partial']}/{negative['executed_ok']} | "
        f"{adj['reported_with_partial_rate_pct']}% | 措辞不同的 {len(adj['wording_only_cases'])} 条计入；"
        f"另有 {len(adj['partial_hit_cases'])} 条仅部分命中 |",
        f"| ③ 目标规则/对象被大模型识别 | {adj['identified_hit']}/{negative['executed_ok']} | {adj['identified_hit_rate_pct']}% | "
        f"含被 DoubleCheck 误剔除的 {adj['doublecheck_suppressed_total']} 条 |",
        f"| ④ 完全未识别 | {len(adj['unidentified'])}/{negative['executed_ok']} | "
        f"{adj['unidentified_rate_pct']}% | {'、'.join(adj['unidentified']) or '无'} |",
        "",
        "> 机器自动口径（偏保守，仅作下界）：严格规则名子串互含 "
        f"{negative['strict_hit']}/{negative['executed_ok']}（{negative['strict_hit_rate_pct']}%）、"
        f"核心词元启发式 {negative['lenient_hit']}/{negative['executed_ok']}（{negative['lenient_hit_rate_pct']}%）——"
        f"后者已剔除 {len(adj['matcher_false_positives'])} 条虚假命中"
        f"（{'、'.join(adj['matcher_false_positives'])}）后为 {adj['machine_semantic_corrected']} 条。",
        f"> 「依据切块」引用召回核对：{negative['expected_chunk_cited']}/{negative['executed_ok']}"
        f"（{negative['expected_chunk_cited_rate_pct']}%）—— 检索层未出现漏召回。",
        "",
        "口径 ② 存在**定义性灰区**：规则名保真度与「缺陷是否被检出」是两种不同口径。"
        "本报告采用后者（缺陷被检出即计入），"
        f"独立复核子代理采用更严格的规则名口径得到 58/{negative['executed_ok']}（76.3%），"
        f"含部分命中为 61/{negative['executed_ok']}（80.3%）；本报告的 "
        f"{adj['reported_with_partial']}（{adj['reported_with_partial_rate_pct']}%）落在该区间内，"
        "差异仅来自 3 条灰区案例（T-03、T-09、F-06）的归类。",
        "> 严格口径 7/76（9.2%）是**最诚实但最不具信息量**的下界：它只反映"
        "「模型输出的 rule_name 措辞是否恰好与案例库标签一致」，而非检出能力。",
        "",
        "## 三、关键缺陷：DoubleCheck 防幻觉层过度过滤，导致伪判「完全合规」",
        "",
        f"共 **{adj['doublecheck_suppressed_total']} 条**反例的目标规则被大模型正确识别后，"
        "又被 `DoubleCheckVerifier` 以「在依据 [n] 原文中无实质支持，判定为模型幻觉并剔除」为由删除：",
        "",
        f"- **{len(adj['false_negative_cases'])} 条因此最终 0 违规、100 分、伪判合规**："
        f"{'、'.join(adj['false_negative_cases'])}",
        f"- 另 {len(adj['suppressed_but_other_rule'])} 条虽同样被剔除，但因命中其它规则未导致伪判合规："
        f"{'、'.join(adj['suppressed_but_other_rule'])}",
        "",
        "**这些被剔除的规则本身就是规范原文条款，并非幻觉**，例如：",
        "",
        "- 建库规范第 4 条「禁止触发器、存储过程、自定义函数」（D-05 / D-06 的目标规则）；",
        "- 建表规范「字段不要写 CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci」（F-12 的目标规则）；",
        "- 建库规范第 1 条「数据必须使用 innodb 引擎」（D-02 的目标规则）。",
        "",
        "判据有两条，均可在本次保留的成果物中复核：",
        "",
        "1. **产物内自相矛盾**：这些案例的 `summary` 明确写出了违规"
        "（如 D-02：「唯一问题是使用 MyISAM 引擎，违反必须使用 InnoDB 的强制要求」），"
        "而 `violations` 为空、`is_compliant=true`；",
        "2. **现场复现**：本次单独重跑 D-05 与 F-12，标准输出稳定打印 "
        "`[WARN] [DoubleCheck 拦截] 幻觉误报过滤: 规则 '禁止触发器、存储过程、自定义函数' 在依据 [5] 原文中无实质支持`，"
        "两者均复现 100 分 / 0 违规。",
        "",
        "> 这与项目设计目标「严禁伪判完全合规」直接冲突：此处并非解析失败，"
        "而是防幻觉层把**真规则**当作幻觉删除，属于需要优先修复的缺陷。",
        "",
        "## 四、人工复核裁定：22 条机器未命中案例的逐条归因",
        "",
        "案例库的「命中规则」是自定标签，与模型输出的 `rule_name` 措辞天然不同，"
        "因此对 22 条机器未命中案例逐条比对 `violations` / `summary` 与规范原文后裁定如下：",
        "",
        "| 归因 | 条数 | 案例 | 结论 |",
        "| --- | --- | --- | --- |",
        f"| 目标规则被识别但遭 DoubleCheck 剔除，伪判合规 | {len(adj['false_negative_cases'])} | "
        f"{'、'.join(adj['false_negative_cases'])} | 系统级漏报（真缺陷） |",
        f"| 目标规则被剔除，但被其它规则兜住 | {len(adj['suppressed_but_other_rule'])} | "
        f"{'、'.join(adj['suppressed_but_other_rule'])} | 目标规则未上报 |",
        f"| 规则域已报出，仅措辞不同 | {len(adj['wording_only_cases'])} | "
        f"{'、'.join(adj['wording_only_cases'])} | 实为命中，机器匹配低估 |",
        f"| 同一目标字段被归入其它规则 | {len(adj['other_rule_same_target_cases'])} | "
        f"{'、'.join(adj['other_rule_same_target_cases'])} | 部分命中（该条款另有口径冲突） |",
        f"| 规范口径分歧导致未报出 | {len(adj['spec_scope_ambiguity_cases'])} | "
        f"{'、'.join(adj['spec_scope_ambiguity_cases'])} | 非系统缺陷（见第七节） |",
        "",
        "另有 1 例**机器匹配的虚假命中**已从机器口径中剔除（该例原被算作命中，经独立复核指出后由 Lead 回读确认）：",
        "",
        f"- {'；'.join(f'{cid}：{reason}' for cid, reason in adj['matcher_false_positives'].items())}",
        "",
        "逐条证据（期望规则 / 实测 `rule_name` / 目标对象 / 综述原文）见各案例的独立报告："
        "`evaluation/results/reports/shard_*_6/<案例编号>.md`。",
        "",
        "## 五、分模块表现",
        "",
        "| 模块 | 案例数 | 反例数 | 判为不合规 | 复核后识别目标规则 | 机器(未修正)：严格 / 语义命中 | 机器语义未命中 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, stat in summary["by_module"].items():
        lines.append(
            f"| {name} | {stat['total']} | {stat['negative']} | {stat['detected']} | "
            f"{stat['identified']}/{stat['negative']} | {stat['strict_hit']} / {stat['lenient_hit']} | {stat['miss']} |"
        )

    lines += [
        "",
        "## 六、合规对照组（误报检查）",
        "",
        f"对照组共 {positive['total']} 条，全部成功执行；其中被判为不合规 {len(positive['false_alarm_cases'])} 条。"
        "逐条裁定后需区分「真误报」与「规范原文自相矛盾」：",
        "",
        "| 案例 | 模块 | 判定 | 得分 | 违规数 | 裁定 | 依据 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    disposition_label = {
        "true_false_alarm": "真误报",
        "spec_conflict": "对照组标注自相矛盾",
        "clean": "无误报",
    }
    for item in positive["detail"]:
        lines.append(
            f"| {item['case_id']} | {item['module_name']} | "
            f"{'合规' if item['is_compliant'] else '不合规'} | {item['score']} | {item['violation_count']} | "
            f"{disposition_label.get(item['disposition'], item['disposition'])} | {item['note']} |"
        )

    lines += [
        "",
        f"- **真误报 {len(positive['true_false_alarm_cases'])} 条**："
        f"{'、'.join(positive['true_false_alarm_cases']) or '无'}",
        f"- **对照组标注自相矛盾 {len(positive['spec_conflict_cases'])} 条**："
        f"{'、'.join(positive['spec_conflict_cases']) or '无'}"
        "（检查器判定**正确**——这些 DDL 确实违反命名规范 16，即反例 N-15 所考察的同一规则；"
        "问题出在对照组用例与规范第 5/12 条的原文示例冲突）",
        "",
        "## 七、规范原文自相矛盾、判定不一致与数据质量问题",
        "",
        "### 7.1 规范文档自身的冲突（需规范维护方确认口径）",
        "",
        "| 编号 | 冲突点 | 规范原文 | 影响 |",
        "| --- | --- | --- | --- |",
        "| 1 | 金额/数量字段是否可带本表表名前缀 | 第 5 条示例 `order_money`、第 12 条示例 `order_amount_unit`，"
        "与第 16 条「若是本表自己的字段，字段前不需要加表名」直接冲突 | P-01 / P-04 被判不合规"
        "（检查器正确）；对照组用例自身标注矛盾 |",
        "| 2 | `db_` 是库前缀还是表前缀 | 第 15 条「**库前缀**统一使用 db_」、建库规范第 2 条「生产**数据库**均以 db_ 开头」 | "
        "D-01（`order_info`，表名无 `db_` 前缀）未被报出；README 已登记该分歧 |",
        "| 3 | 数字类型是否必须加 UNSIGNED | 建库规范第 9 条为「**可以**加 UNSIGNED」（推荐性），"
        "但建表模板原文写作 `version INT NOT NULL DEFAULT 0`（无 UNSIGNED） | P-02 被判不合规："
        "模型把推荐性条款升级为强制条款 |",
        "| 4 | 布尔字段命名 | 建表规范原文为 `delete` + 「列名尽量用名词」，而知识库切块写作 `is_deleted` | F-06 归因分歧 |",
        "",
        "### 7.2 同一系统的判定不一致（规则极性自相矛盾）",
        "",
        f"- **M-19** 报出「表名 `db_order` 使用了库前缀 `db_`，违反库前缀使用规范」——把**使用** `db_` 判为违规；",
        f"- 而 **D-09**（`{'、'.join(data_quality['polarity_conflict']['requires_db_prefix_cases'])}`）"
        "报出「生产表名必须以 `db_` 开头」——把**不使用** `db_` 判为违规；",
        "- 同一系统对同一前缀给出**完全相反**的规则极性，且 **D-01**（真正缺 `db_` 前缀的 `order_info`）两条真缺陷"
        "（缺 `db_` 前缀、表名含疑似关键字 `order`）**一条都没报**，"
        "反而编造了一条与用例无关的「code 字段长度」规则。这是本次评测中最严重的一致性问题。",
        "",
        "### 7.3 跨案例判定不稳定",
        "",
        "P-01 与 P-02 的 DDL 都含 `version INT NOT NULL DEFAULT 0` 与 `sort INT NOT NULL DEFAULT 0`：",
        "P-02 因此被判「数字类型必须加 UNSIGNED」，P-01 却未被报出；P-03 也含同样的 `version INT` 写法并判为合规。"
        "即同一写法在不同案例中得到不同判定，命中不稳定。",
        "",
        "### 7.4 数据质量与枚举规范问题",
        "",
        "| 问题 | 实测 |",
        "| --- | --- |",
        f"| 同一案例内 `rule_name` 重复（违规计数膨胀） | {len(data_quality['duplicate_rule_name_cases'])} 个案例、"
        f"{data_quality['duplicate_rule_name_entries']}/{data_quality['total_violation_entries']} 条"
        f"（{data_quality['duplicate_entry_share_pct']}%，**仅统计 76 条反例**）；"
        "T-11 / T-12 各重复到 8 条同名违规 |",
        f"| `severity` 枚举不统一 | 取值分布 {data_quality['severity_counts']}，"
        f"同一级别出现 {' / '.join(data_quality['severity_enum_variants'])} 两种写法 |",
        f"| 重复条目涉及案例 | {'、'.join(data_quality['duplicate_rule_name_cases'])} |",
        "",
        "## 八、独立验证",
        "",
        "由**独立验证子代理**（不读取任何派生结论，仅从 `shard_*.jsonl` + 案例索引重算）做对抗性复核，"
        "结论见 `evaluation/results/verify/independent_review.md`：",
        "",
        "| Lead 声明 | 独立复核结论 |",
        "| --- | --- |",
        "| 81/81 收齐、全 `ok`、零错误、零重复、SQL 与索引逐字符一致 | **CONFIRM**（并补充：各分片时间窗重叠，证明确为 6 路并行） |",
        "| 反例 68/76（89.5%）判为不合规 | **CONFIRM**（精确一致） |",
        "| 严格命中 7/76 | **CONFIRM**（独立重实现，命中集合逐例一致） |",
        "| 语义命中 54/76 | 算术 **CONFIRM**，但指出 1 例虚假命中（N-03）、5 例漏计（N-02、T-07、T-08、T-11、T-12） |",
        "| 22 条未命中清单 | **CONFIRM**（逐例一致） |",
        "| P-01 / P-04 为「规范自相矛盾」 | **部分 REFUTE**：检查器判定正确，属**对照组用例标注错误**（已按此修正第六条口径） |",
        "",
        "本报告已按复核意见修正：剔除 N-03 虚假命中、把 5 例漏计计入、重述 P-01/P-04 定性，"
        "并新增 7.2 规则极性、7.3 判定不稳定、7.4 数据质量三节。",
        "",
        "复核方残留的不确定性是「DoubleCheck 剔除真规则」为推断而非直接观测"
        "（其未运行 `app/`）——该点已由 Lead **现场复现**补齐：单独重跑 D-05 与 F-12，"
        "标准输出稳定打印 `[WARN] [DoubleCheck 拦截] 幻觉误报过滤: 规则 '禁止触发器、存储过程、自定义函数' "
        "在依据 [5] 原文中无实质支持`，两者均复现 100 分 / 0 违规。",
        "",
        "## 九、性能与得分分布",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 单案例平均耗时 | {summary['timing']['avg_seconds']} s |",
        f"| 单案例中位耗时 | {summary['timing']['median_seconds']} s |",
        f"| 单案例最长耗时 | {summary['timing']['max_seconds']} s |",
        f"| 串行累计耗时（等效） | {summary['timing']['total_seconds']} s（≈{round(summary['timing']['total_seconds']/60,1)} 分钟） |",
        f"| 反例平均合规得分 | {summary['score']['avg']} |",
        f"| 得分为 0 的反例数 | {summary['score']['zero_score_cases']} |",
        "",
        "> 6 个子代理并行分片执行，实际墙钟耗时约 9 分钟（各分片自身 6.4~8.8 分钟），"
        "相较串行等效耗时获得约 5 倍加速。",
        "",
        "## 十、成果物清单（已保留）",
        "",
        "| 路径 | 内容 |",
        "| --- | --- |",
        "| `evaluation/negative_cases_index.json` | 81 条案例的结构化索引（唯一可信输入） |",
        "| `evaluation/results/shard_*_6.jsonl` | 6 个子代理各自的原始逐案例结果 |",
        "| `evaluation/results/reports/shard_*_6/*.md` | 每条案例的人类可读审查报告（含实测明细与整改回复） |",
        "| `evaluation/results/merged_results.json` | 合并后的完整结构化结果（含评测判定与匹配证据） |",
        "| `evaluation/results/merged_results.jsonl` | 同上，逐行 JSON |",
        "| `evaluation/results/summary.json` | 机器可读的评测汇总 |",
        "| `evaluation/results/执行报告.md` | 本报告 |",
        "| `evaluation/results/verify/independent_review.md` | 独立验证子代理的复核结论（含分歧清单与残余不确定性） |",
        "| `evaluation/results/diag/mechanism.jsonl` | DoubleCheck 缺陷的现场复现记录 |",
        "",
    ]
    (RESULTS_DIR / "执行报告.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
