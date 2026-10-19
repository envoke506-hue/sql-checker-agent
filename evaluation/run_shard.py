"""反向案例分片执行器 (Shard Runner)

用法：
    # 执行第 1 个分片（共 6 个分片），结果追加写入指定的 JSONL，并为每条案例落盘 Markdown 报告
    python evaluation/run_shard.py --shard 1/6

    # 只跑指定案例（调试用）
    python evaluation/run_shard.py --ids N-01,N-02

设计要点：
1. **单写者、互不重叠**：每个分片只写自己的 `--out` 与 `--reports-dir`，多个子代理之间不存在写冲突；
2. **增量落盘**：每跑完一条案例立即 flush 到 JSONL，进程中途被杀也不会丢掉已完成的结果；
3. **断点续跑**：重跑同一分片时，`--out` 中已成功记录的案例会被自动跳过（`--no-resume` 可关闭）；
4. **失败隔离**：单条案例抛异常只记为该条的 `status=error`，不会中断整个分片；
5. **共享只读输入**：案例 SQL 一律来自主代理生成的 `negative_cases_index.json`，保证各分片输入完全一致。

本脚本直接以进程内方式调用 `SqlAuditService`（复用真实 RAG 全链路：双路检索 + RRF + 上下文编排
+ 大模型审查 + Double Check 防幻觉核验），不依赖任何 HTTP 服务端，避免与占用 8000 端口的其它服务冲突。
"""

import argparse
import asyncio
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.http_client import close_async_client  # noqa: E402
from app.core.dependencies import get_sql_audit_service  # noqa: E402
from app.models.dto.sql_audit import SqlAuditRequest  # noqa: E402

DEFAULT_INDEX = EVAL_DIR / "negative_cases_index.json"
DEFAULT_RESULTS_DIR = EVAL_DIR / "results"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_index(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def select_cases(index, shard: str | None, ids: str | None):
    """按分片编号（1-based）或显式 ID 列表选取本分片要执行的案例。"""
    if ids:
        wanted = {item.strip() for item in ids.split(",") if item.strip()}
        picked = [c for c in index if c["case_id"] in wanted]
        missing = wanted - {c["case_id"] for c in picked}
        if missing:
            raise SystemExit(f"索引中不存在这些案例编号: {sorted(missing)}")
        return picked

    if not shard:
        raise SystemExit("必须指定 --shard i/N 或 --ids")

    shard_index, shard_total = shard.split("/")
    shard_index, shard_total = int(shard_index), int(shard_total)
    if not 1 <= shard_index <= shard_total:
        raise SystemExit(f"非法分片编号: {shard}")

    # 轮转切分：把案例轮流分配到各分片，使每个分片的案例数与模块分布尽量均衡
    return [c for position, c in enumerate(index) if position % shard_total == shard_index - 1]


def load_completed(out_path: Path):
    """读取已成功落盘的案例编号，用于断点续跑。"""
    done = set()
    if not out_path.exists():
        return done
    for line in out_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("status") == "ok":
            done.add(record.get("case_id"))
    return done


async def run_case(service, case) -> dict:
    """执行单条案例，返回完整、可追溯的结果记录。"""
    record = {
        "case_id": case["case_id"],
        "kind": case["kind"],
        "module": case["module"],
        "module_name": case["module_name"],
        "source_file": case["source_file"],
        "title": case["title"],
        "clause": case["clause"],
        "expected_rule_names": case["expected_rule_names"],
        "expected_severity": case["expected_severity"],
        "expected_chunks": case["expected_chunks"],
        "sql": case["sql"],
    }

    started_at = now_iso()
    started = time.perf_counter()
    try:
        result = await service.audit_sql(SqlAuditRequest(sql_text=case["sql"], db_type="mysql"))
        record.update({
            "status": "ok",
            "error": None,
            "is_compliant": result.is_compliant,
            "score": result.score,
            "summary": result.summary,
            "violations": [item.model_dump() for item in result.violations],
            "violation_count": len(result.violations),
            "citations": [item.model_dump() for item in result.citations],
            "suggested_sql": result.suggested_sql,
            "markdown_report": result.markdown_report,
        })
    except Exception as exc:  # 单条失败不影响分片内其它案例
        record.update({
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc()[-4000:],
            "is_compliant": None,
            "score": None,
            "summary": "",
            "violations": [],
            "violation_count": 0,
            "citations": [],
            "suggested_sql": "",
            "markdown_report": "",
        })

    record["started_at"] = started_at
    record["finished_at"] = now_iso()
    record["elapsed_seconds"] = round(time.perf_counter() - started, 2)
    return record


def write_report(reports_dir: Path, record) -> None:
    """为单条案例落盘一份人类可读的 Markdown 报告。"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    expected = "、".join(record["expected_rule_names"]) or "（合规对照组，期望 0 违规）"
    lines = [
        f"# {record['case_id']} · {record['title']}",
        "",
        f"- 案例类型：{'反例' if record['kind'] == 'negative' else '合规正例对照组'}",
        f"- 所属模块：{record['module_name']}（{record['source_file']}）",
        f"- 违反条款：{record['clause']}",
        f"- 期望命中规则：{expected}",
        f"- 期望级别：{record['expected_severity']}",
        f"- 依据切块：{'、'.join(record['expected_chunks']) or '—'}",
        f"- 执行状态：{record['status']}（耗时 {record['elapsed_seconds']}s，开始于 {record['started_at']}）",
        "",
    ]
    if record["status"] == "ok":
        lines += [
            f"- 审查判定：{'合规' if record['is_compliant'] else '不合规'}",
            f"- 合规得分：{record['score']}",
            f"- 检出违规数：{record['violation_count']}",
            f"- 审查综述：{record['summary']}",
            "",
            "## 实测检出明细",
            "",
        ]
        if record["violations"]:
            lines += ["| 序号 | rule_name | 级别 | 目标对象 | 引用编号 |", "| --- | --- | --- | --- | --- |"]
            for position, item in enumerate(record["violations"], start=1):
                target = str(item.get("target_object", "")).replace("|", "\\|")
                lines.append(
                    f"| {position} | {item.get('rule_name', '')} | {item.get('severity', '')} "
                    f"| {target} | [{item.get('citation_index', '')}] |"
                )
        else:
            lines.append("（本次未检出任何违规项）")
        lines += ["", "## 整改回复 (markdown_report)", "", record["markdown_report"] or "（无）", ""]
    else:
        lines += ["## 执行异常", "", "```text", record["error"], "```", ""]

    lines += ["## 原始输入 DDL", "", "```sql", record["sql"], "```", ""]
    (reports_dir / f"{record['case_id']}.md").write_text("\n".join(lines), encoding="utf-8")


async def main_async(args) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    index = load_index(Path(args.index))
    cases = select_cases(index, args.shard, args.ids)

    out_path = Path(args.out) if args.out else DEFAULT_RESULTS_DIR / f"shard_{args.shard.replace('/', '_')}.jsonl"
    reports_dir = Path(args.reports_dir) if args.reports_dir else DEFAULT_RESULTS_DIR / "reports" / f"shard_{args.shard.replace('/', '_')}"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    completed = set() if args.no_resume else load_completed(out_path)
    pending = [c for c in cases if c["case_id"] not in completed]

    print(f"[分片 {args.shard or 'ID选择'}] 案例 {len(cases)} 条 | 已完成 {len(completed)} 条 | 待执行 {len(pending)} 条")
    print(f"[输出] {out_path}")
    print(f"[报告] {reports_dir}")

    service = get_sql_audit_service()
    ok_count = error_count = 0
    total_started = time.perf_counter()

    with out_path.open("a", encoding="utf-8") as sink:
        for position, case in enumerate(pending, start=1):
            record = await run_case(service, case)
            record["shard"] = args.shard or "ids"
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
            sink.flush()
            write_report(reports_dir, record)

            if record["status"] == "ok":
                ok_count += 1
                verdict = "合规" if record["is_compliant"] else "不合规"
                print(
                    f"  [{position}/{len(pending)}] {record['case_id']} {verdict} "
                    f"score={record['score']} 违规={record['violation_count']} "
                    f"耗时={record['elapsed_seconds']}s"
                )
            else:
                error_count += 1
                print(f"  [{position}/{len(pending)}] {record['case_id']} 执行失败: {record['error']}")

    await close_async_client()

    print(
        f"[分片 {args.shard or 'ID选择'}] 完成: 成功 {ok_count} / 失败 {error_count} / 本轮总计 {len(pending)} 条, "
        f"总耗时 {round(time.perf_counter() - total_started, 1)}s"
    )
    return 1 if error_count else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="反向案例分片执行器")
    parser.add_argument("--shard", help="分片编号，格式 i/N，例如 1/6")
    parser.add_argument("--ids", help="逗号分隔的案例编号，例如 N-01,N-02")
    parser.add_argument("--index", default=str(DEFAULT_INDEX), help="案例索引 JSON 路径")
    parser.add_argument("--out", help="本分片结果 JSONL 路径 (默认 evaluation/results/shard_i_N.jsonl)")
    parser.add_argument("--reports-dir", help="本分片 Markdown 报告目录")
    parser.add_argument("--no-resume", action="store_true", help="忽略已完成记录，强制重跑全部案例")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
