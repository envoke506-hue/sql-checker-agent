# 反向案例库并行执行与评测 (evaluation)

本目录是 `doc/negative_cases/` 中**反向案例（反例）批量执行与检出率评测**的完整工具链与成果物归档。
一次完整执行 = 「主代理生成唯一索引与执行器 → 多个子代理并行分片执行真实 RAG 全链路 → 合并评测」。
所有原始结果与评测结论均已落盘保留，可随时复核、复跑。

---

## 1. 目录与脚本

| 文件 | 作用 |
| --- | --- |
| `build_case_index.py` | 解析 `doc/negative_cases/0*.md`，生成唯一可信的结构化索引（81 条 = 反例 76 + 合规对照组 5） |
| `negative_cases_index.json` | 上一步的产物；**所有分片只读同一份索引**，保证各分片输入完全一致、可复现 |
| `run_shard.py` | 分片执行器：进程内直接调用 `SqlAuditService`（不依赖 HTTP 服务，避免与占用 8000 端口的其它服务冲突） |
| `merge_results.py` | 合并 6 个分片结果，做对账与命中率评测，生成汇总报告 |
| `results/` | 全部成果物（原始分片结果、逐案例报告、合并结果、评测报告） |

### 为什么由主代理统一定义输入与执行器

多个子代理并行时，若各自去正则解析 Markdown、各自实现判定口径，分片之间的结果将不可比。
因此索引与执行器只由主代理编写一次，子代理仅「执行自己的分片」，
每个子代理只写自己的 `shard_i_6.jsonl` 与 `reports/shard_i_6/`，写范围完全互不重叠。

---

## 2. 复跑步骤

```bash
# 1) 生成/刷新案例索引（源文档变更后需重跑）
.venv\Scripts\python.exe evaluation/build_case_index.py

# 2) 并行执行 6 个分片（可分别在不同终端/子代理中同时运行）
.venv\Scripts\python.exe evaluation/run_shard.py --shard 1/6
.venv\Scripts\python.exe evaluation/run_shard.py --shard 2/6
.venv\Scripts\python.exe evaluation/run_shard.py --shard 3/6
.venv\Scripts\python.exe evaluation/run_shard.py --shard 4/6
.venv\Scripts\python.exe evaluation/run_shard.py --shard 5/6
.venv\Scripts\python.exe evaluation/run_shard.py --shard 6/6

# 3) 合并并生成评测报告
.venv\Scripts\python.exe evaluation/merge_results.py

# 调试：只跑指定案例
.venv\Scripts\python.exe evaluation/run_shard.py --ids N-01,D-14 --out evaluation/results/diag/x.jsonl
```

执行器特性：

- **增量落盘**：每跑完一条就 flush 到 JSONL，进程中途中断不丢结果；
- **断点续跑**：重跑同一分片会跳过已记录为 `status: "ok"` 的案例（`--no-resume` 可强制重跑）；
- **失败隔离**：单条案例异常只记为 `status: "error"`，不中断整个分片。

---

## 3. 依赖与前置条件（本次执行环境实测可用）

| 依赖 | 说明 |
| --- | --- |
| 本地 Ollama + `qwen3-embedding:4b` | 稠密向量路；`http://127.0.0.1:11434` |
| 中转站大模型 API | 审查推理；配置见项目根 `.env` 的 `RELAY_*` |
| `data/indices/` 双路索引 | 已构建（6 个切块 / 2560 维），哈希未变则秒级加载 |
| 规范原文 | `.env` 的 `SPEC_DOC_PATH` 指向的《数据库规范.md》 |

单案例耗时约 6~77 秒（本次均值 33.1 秒）；6 分片并行墙钟约 9 分钟。

---

## 4. 成果物清单

| 路径 | 内容 |
| --- | --- |
| `results/shard_1_6.jsonl` … `shard_6_6.jsonl` | 6 个子代理各自产出的**原始**逐案例结果（权威数据源） |
| `results/reports/shard_*_6/<案例编号>.md` | 每条案例的人类可读报告：期望规则、实测违规明细、整改回复、原始 DDL |
| `results/merged_results.json` / `.jsonl` | 合并后的 81 条完整结果，含评测判定（`eval`）与匹配证据 |
| `results/summary.json` | 机器可读的评测汇总（命中率、分模块、耗时、缺陷裁定） |
| `results/执行报告.md` | **面向人的总报告**（结论、缺陷分析、人工复核裁定、口径分歧登记） |
| `results/verify/independent_review.md` | 独立验证子代理的复核结论（对上述结论做对抗性校验） |
| `results/diag/mechanism.jsonl` | DoubleCheck 过度过滤缺陷的现场复现记录 |

### 结果记录的关键字段

每条 `*.jsonl` 记录包含：`case_id`、`kind`、`module`、`status`、`sql`、
`is_compliant`、`score`、`summary`、`violations[]`、`citations[]`、`suggested_sql`、
`markdown_report`、`elapsed_seconds`、`started_at` / `finished_at`，
以及来自索引的 `expected_rule_names` / `expected_severity` / `expected_chunks`。
因此任何判定口径都可以在原始数据上重新计算，无需重跑大模型。

---

## 5. 评测口径说明

`merge_results.py` 给出**三层口径**，避免单一口径造成的过度声称：

| 口径 | 含义 |
| --- | --- |
| ① 系统最终判定 | 直接看 `is_compliant`（是否伪判合规） |
| ② 目标规则最终被报出 | 机器语义匹配 + 人工复核确认「仅措辞不同」的案例 |
| ③ 目标规则被大模型识别 | 在 ② 基础上，加上被 `DoubleCheck` 防幻觉层误剔除的案例 |

机器自动匹配同时输出两个**偏保守**的参考值（严格规则名子串互含、核心词元启发式），
并给出人工复核裁定表；`merge_results.py` 会在「裁定表」与「机器未命中清单」不一致时直接报错退出，
防止口径与数据脱节。

详细结论见 [`results/执行报告.md`](./results/执行报告.md)。
