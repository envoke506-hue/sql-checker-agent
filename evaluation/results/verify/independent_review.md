# 独立复核报告 — SQL DDL 合规检查批量评测（81 例）

复核人：独立验证子代理（独立 verifier）　角色：**试图证伪**，而非复述结论。

## 0. 复核范围与方法

- 仅使用原始工件：`evaluation/negative_cases_index.json`（81 例索引）+ `evaluation/results/shard_{1..6}_6.jsonl`（原始逐例结果，共 81 行）。
- **未读取、未使用**任何派生结论：`merged_results.json`、`summary.json`、`执行报告.md`、`merged_results.jsonl` 均未作为输入。
- 未运行任何 LLM/审计流水线（未调用 `run_shard.py`），全部为静态分析。
- 所有复核脚本与本报告均写在 `evaluation/results/verify/` 下，未修改任何其他文件。
- 命中判定由我自行设计：先做**语料级判别性检验**（把出现在全部 147 条上报 rule_name 中占比 >15% 的词元/2-gram 视为通用词，自动剔除），再用**逐例人工裁决**（同时看 `rule_name`、`description`、`target_object`，必要时回读索引 `clause` 与原始 SQL）。**没有复用 lead 的匹配器**；lead 的匹配器仅被独立重实现一次，用于核对它的算术（claim 4 的数字）。

## 1. 结论速览（逐条 CONFIRM / REFUTE）

| # | Lead 的声明 | 复核结论 |
|---|---|---|
| 1 | 81/81 收齐、status 全 ok、零错误、零重复 id、sql 与索引完全一致 | **CONFIRM** |
| 2 | 76 反例中 68 例判为不合规（89.5%） | **CONFIRM**（数字精确一致） |
| 3 | 5 个对照正例中 P-01/P-02/P-04 被误判为不合规 | **数字 CONFIRM / 定性部分 REFUTE**：P-01、P-04 的 DDL 确实违反「本表字段不加表名前缀」，属**对照用例自身标注错误**，检查器判错为对；只有 P-02 是可辩护的误报 |
| 4a | 严格命中 7/76（9.2%） | **CONFIRM**（独立重实现其算法，命中集合逐例一致） |
| 4b | 宽松/语义命中 54/76（71.1%） | **算术 CONFIRM / 指标有效性 REFUTE**：其 54 例中 N-03 属**过度判定**应剔除，同时又**漏计**了 5 例（N-02、T-07、T-08、T-11、T-12）实质命中（另有 T-03、T-09、F-06 为部分命中）。按同一「缺陷是否被检出」口径，我的独立结果为 **58/76 = 76.3%**（含部分命中 61/76 = 80.3%） |

## A. 完整性与一致性 —— CONFIRM claim 1

| 检查项 | 结果 |
|---|---|
| 各分片原始行数 | shard_1=14, shard_2=14, shard_3=14, shard_4=13, shard_5=13, shard_6=13，合计 **81** |
| JSON 解析失败行 | 0 |
| 唯一 case_id | **81**（索引亦 81 且无重复） |
| 索引中缺失 | 无 |
| 结果中多出 | 无 |
| 重复 case_id | 无 |
| `status != "ok"` | **0**（全部 81 条为 ok） |
| `error` 字段非空 | **0** |
| `sql` 与索引逐字符相等 | **81/81 相等**，0 处不一致 |
| `kind` / `expected_rule_names` 与索引一致 | 81/81 一致（附加核对） |
| `shard` 字段与文件名一致 | 81/81 一致（如 `1/6`） |
| `citations` / `suggested_sql` / `markdown_report` 缺项 | 0 / 0 / 0 |
| `violation_count` 与 `len(violations)` 一致 | 81/81 一致 |
| `is_compliant` 与「violations 是否为空」自洽 | 81/81 自洽（无矛盾记录） |
| `elapsed_seconds` 与 finished−started 偏差 ≤2s | 81/81 一致 |

**运行真实性旁证**（额外独立检查）：6 个分片的时间窗全部相互重叠，全局窗口 2026-10-16 15:12:12 → 15:21:17（9.1 分钟），而各例耗时之和为 44.7 分钟 —— 与「6 路并行真实执行」相符；机器当前时间 2026-10-16 15:38，即本次评测在复核前约 17 分钟完成。未发现伪造/占位痕迹。

## B. 判定计数 —— CONFIRM claim 2，拆解 claim 3

**反例（76）**：判为不合规 **68** 例 → 68/76 = 89.47% ≈ **89.5%（CONFIRM）**。

漏检（false negative，`is_compliant == true`）共 8 例，且这 8 例的 `violations` 均为空、`score` 均为 100：

`T-10`、`D-01`、`D-02`、`D-05`、`D-06`、`D-08`、`F-07`、`F-12`

我逐例回读了这 8 例的原始 SQL，**确认缺陷真实存在**（触发器、存储过程/函数、MyISAM、latin1、手写 CHARACTER SET、VARCHAR(1)、rel_id、表名缺 db_ 前缀），因此这 8 例是有效的反例，属真漏检，不是标注问题。

**对照正例（5）**：判为不合规 **P-01、P-02、P-04**（与 lead 一致），P-03、P-05 通过。但「误判」的定性需要拆开：

| 用例 | lead 的定性 | 我的复核 |
|---|---|---|
| P-01 | 误判 | **REFUTE**。其 DDL 是 `CREATE TABLE db_order`，其中 `order_money DECIMAL(20,6)`、`order_amount_unit VARCHAR(10)` 携带本表表名前缀 `order`，正是反例 **N-15** 所考察的「命名规范16 本表字段不加表名前缀」。检查器报「本表字段名禁止携带本表表名前缀」是**正确**的；该对照用例标注自相矛盾（title 声称「本模块全部规范要求均未违反」）。属**对照组构造缺陷**，不是检查器缺陷 |
| P-02 | 误判 | **部分 CONFIRM（可辩护的误报）**。被报的是 `sort INT`、`version INT` 缺 UNSIGNED。但建库规范9 的原文是「已知不存在负数的情况下**可以**加 UNSIGNED」（许可而非强制），且建表模板本身规定 `version INT NOT NULL DEFAULT 0`（不带 UNSIGNED）。更关键的是**同一模式在不同用例中被区别对待**：P-03 的对照 DDL 同样含 `version INT NOT NULL DEFAULT 0`，却判为合规。这是检查器的不一致，而非纯粹的规则争议 |
| P-04 | 误判 | **REFUTE**。`CREATE TABLE db_order` 含 `order_money DECIMAL(20,6)`，同样违反命名规范16（与 N-15 同规则）。检查器报错正确，对照组标注有误 |

补充：P-01 中 `sort INT NOT NULL DEFAULT 0`、`version INT NOT NULL DEFAULT 0` 与 P-02 中被判违规的写法**完全相同**，但 P-01 未被报出 UNSIGNED 问题 —— 这是同批数据内部的判定不一致（对规则命中不稳定），建议 lead 在报告中显式披露，而不是只把它当作「误判」。

## C. 命中率（我自己的方法）

**Lead 算术的独立核对（CONFIRM）**：我按 `merge_results.py` 中记录的算法独立重实现了一次匹配器，得到严格命中 **7** 例（`N-01, M-17, M-18, D-03, D-04, D-11, D-13`），宽松命中 **54** 例，且 `76 − 54 = 22` 例未命中集合与 lead 给出的 22 例「语义未命中」名单**逐例完全一致**。即 claim 4 的两个数字在其自身口径下是**可复现、无算术错误**的。

**方法说明（我的口径）**：lead 的匹配只看 `violations[].rule_name` 字符串；这会把「缺陷已识别但换了规则名/表述更泛」的命中判成漏检。我的口径是「上报的违规是否指向与期望规则**同一个缺陷**」，证据可来自 `rule_name`、`description`、`target_object` 三者，并逐例回读索引 `clause` 与原 SQL 核对。

**我的逐例裁决结果（76 例）**：

| 分类 | 数量 | 占比 |
|---|---|---|
| 命中 HIT（缺陷被明确检出） | **58** | **76.3%** |
| 部分命中 PARTIAL（缺陷族被识别，规则名/标准词不到位） | 3 | 3.9% |
| 漏检 MISS（未检出，或报的是另一条规则） | 15 | 19.7% |

含部分命中则 **61/76 = 80.3%**；仅计入明确命中为 **58/76 = 76.3%**。两种口径都高于 lead 的 54/76（71.1%）。

**与 lead 名单的具体分歧**：

1. **过度判定 1 例**（lead 计命中，我判漏检）：`N-03`
2. **漏计明确命中 5 例**（lead 计漏检，我判命中）：`N-02`, `T-07`, `T-08`, `T-11`, `T-12`
3. **漏计部分命中 3 例**：`F-06`, `T-03`, `T-09`
4. 双方一致：同为命中 53 例，同为漏检 14 例（`D-01`, `D-02`, `D-05`, `D-06`, `D-07`, `D-08`, `F-04`, `F-07`, `F-11`, `F-12`, `T-02`, `T-04`, `T-06`, `T-10`）。

净效应：lead 的 22 例「语义未命中」名单应收缩为 **15 例**（去掉 N-02、T-07、T-08、T-11、T-12，以及可选的 T-03、T-09、F-06 三例部分命中），同时把 **N-03** 补进漏检名单。

### 明确命中（58 例）逐例依据

| case | 期望规则 | 上报的 rule_name | 判定依据 |
|---|---|---|---|
| D-03 | 建库规范 · 表内禁止外键设计 | 禁止外键设计 | 「禁止外键设计」obj=CONSTRAINT fk_order_user FOREIGN KEY = 期望规则 |
| D-04 | 建库规范 · 表内禁止外键设计 | 表内禁止外键设计 | 「表内禁止外键设计」obj=CONSTRAINT fk_detail_order FOREIGN KEY = 期望规则 |
| D-09 | 建库规范 · 表名禁止关键字 | 生产表名必须以 db_ 开头 ; 表名禁止使用保留关键字 | 「表名禁止使用保留关键字」obj=表名 order = 期望规则 |
| D-10 | 建库规范 · 字段名禁止关键字 | 备注统一命名 remark ; 排序统一命名 sort ; 数字类型非负必须加 UNSIGNED ; 禁止使用保留关键字 | v1/v3/v4/v7「禁止使用保留关键字」obj=desc/group/index/value = 期望规则（字段名禁止关键字） |
| D-11 | 建库规范 · 加字段必须标注 AFTER | DDL 增加字段必须标注 AFTER 指定位置 | 「DDL 增加字段必须标注 AFTER 指定位置」= 期望规则 |
| D-12 | 建库规范 · 数字类型加 UNSIGNED | 数字类型需加 UNSIGNED | 「数字类型需加 UNSIGNED」= 期望规则 |
| D-13 | 建库规范 · 避免 NULL | 避免 NULL 字段 | 「避免 NULL 字段」= 期望规则 |
| D-14 | 建库规范 · 禁用 double | 禁止使用 double 类型 ; 金额字段必须使用 decimal(20,6) | v2「禁止使用 double 类型」obj=pay_money/fee_rate DOUBLE = 期望规则 |
| D-15 | 建库规范 · TINYINT 统一 TINYINT(4) | TINYINT 统一使用 TINYINT(4) | 「TINYINT 统一使用 TINYINT(4)」= 期望规则 |
| D-16 | 建库规范 · 关联表 r_ 前缀 | 关联表必须以 r_ 开头 | 「关联表必须以 r_ 开头」obj=db_user_role = 期望规则 |
| F-01 | 建表规范 · 三方对接表缺 system_source | 三方对接表必须包含系统来源与数据来源 ; 本表字段禁止拼接本表表名 ; 编号编码字段命名后缀为 code | v3「三方对接表必须包含系统来源与数据来源」desc 缺 system_source = 期望规则 |
| F-02 | 建表规范 · 三方对接表缺 data_source | 三方对接表需包含系统来源和数据来源 ; 本表字段禁止加表名前缀且编号应使用 code | v2「三方对接表需包含系统来源和数据来源」desc 缺 data_source = 期望规则 |
| F-03 | 建表规范 · 普通索引 idx_ 前缀 | 普通索引必须以 idx_ 开头 | 「普通索引必须以 idx_ 开头」= 期望规则 |
| F-05 | 建表规范 · 布尔类型 TINYINT(4) | 单字符标记必须使用 char(1) ; 布尔类型必须使用 TINYINT(4) | v1「布尔类型必须使用 TINYINT(4)」= 期望规则 |
| F-08 | 建表规范 · 单字符字段默认值 | 单字符字段必须带默认值 | 「单字符字段必须带默认值」obj=is_split CHAR(1) NOT NULL = 期望规则 |
| F-09 | 建表规范 · 大于1字符用 varchar | 大于1个字符应默认空串 ; 字符串应使用 varchar(30) ; 本表字段禁止加表名前缀 | v2「字符串应使用 varchar(30)」obj=vehicle_number TEXT = 期望规则（大于1字符用 varchar） |
| F-10 | 建表规范 · 单整数用 TINYINT(4) | 整数字段类型选择规范 ; 无负数数字类型必须加 UNSIGNED | v1「整数字段类型选择规范」desc「1 个整数的状态字段应使用 TINYINT(4)，不得用 INT」= 期望规则 |
| M-01 | 建表模板 · 缺少基类字段 version | 缺少实体基类必须字段 version | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-02 | 建表模板 · 缺少基类字段 deleted | 缺少删除标记基类字段 deleted | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-03 | 建表模板 · 缺少基类字段 disabled | 缺少实体基类必填字段 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-04 | 建表模板 · 缺少基类字段 create_id | 实体基类必须字段缺失 ; 数字类型缺少 UNSIGNED | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-05 | 建表模板 · 缺少基类字段 create_time | 缺少实体基类必须字段 create_time | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-06 | 建表模板 · 缺少基类字段 modify_id | 缺少修改人标识字段 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-07 | 建表模板 · 缺少基类字段 modify_time | 实体基类必须字段缺失 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-08 | 建表模板 · 必须包含通用基类审计字段 | 本表字段禁止拼接本表表名 ; 缺少实体基类必须字段 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-09 | 建表模板 · 主键必须为 id | 主键必须命名为 id ; 本表字段禁止加表名 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-10 | 建表模板 · 主键类型必须为 BIGINT UNSIGNED | 主键必须为 BIGINT UNSIGNED | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-11 | 建表模板 · 主键必须 NOT NULL | 主键必须为 BIGINT UNSIGNED NOT NULL | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-12 | 建表模板 · 主键雪花算法 | 主键须为雪花算法无自增 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-13 | 建表模板 · 基类字段类型不符 create_id/modify_id | 基类字段类型必须符合建表模板 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-14 | 建表模板 · 基类字段类型不符 create_time/modify_time | create_time 必须为 DATETIME 并默认 CURRENT_TIMESTAMP ; modify_time 必须为 DATETIME | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-15 | 建库规范 · TINYINT 统一 TINYINT(4) | TINYINT 统一使用 TINYINT(4) 且非负数字加 UNSIGNED | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-16 | 建表模板 · 基类字段类型不符 version | 基础字段 version 类型错误 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-17 | 建表模板 · 必须使用 InnoDB 引擎 | 必须使用 InnoDB 引擎 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-18 | 建表模板 · 必须包含表级注释 | 必须包含表级注释 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-19 | 建表模板 · 缺少表级主键约束 | 缺少主键定义 ; 表名使用库前缀 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| M-20 | 建表模板 · 字段缺少注释 | 主键必须包含注释 ; 基类字段必须包含中文注释 ; 本表字段禁止加表名前缀 | violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过） |
| N-01 | 命名规范 · lower_snake_case | 本表字段不加表名前缀 ; 采用 lower_snake_case 命名法 | v1/v2 rule_name 与期望规则几乎逐字一致（lower_snake_case 驼峰） |
| N-02 | 命名规范 · 语义尽量简短 | 字段使用规范术语 ; 表名使用规范术语 | v1「表名使用规范术语」desc: organization→organ；v2/v3「字段使用规范术语」desc: administrator→admin、organization→organ，正是命名规范2 的原文反例 |
| N-04 | 命名规范 · 单价后缀 price | 单价字段命名后缀必须为 price | 「单价字段命名后缀必须为 price」= 期望规则 |
| N-05 | 命名规范 · 金额后缀 money | 金额字段统一命名后缀 _money | 「金额字段统一命名后缀 _money」= 期望规则 |
| N-06 | 命名规范 · 数量后缀 amount | 数量类字段命名与类型规范 | 「数量类字段命名与类型规范」desc 明确「未用 _amount 后缀」 |
| N-07 | 命名规范 · 时间后缀 time | 时间字段命名规范 | 「时间字段命名规范」obj=receive_date/send_ts，desc 明确 _time 后缀 |
| N-08 | 命名规范 · 业务类前缀 biz_ | 业务类字段需用 biz_ 前缀 ; 非负数字类型必须加 UNSIGNED | 「业务类字段需用 biz_ 前缀」= 期望规则 |
| N-09 | 命名规范 · 入口类前缀 in_ | 入口类字段需使用 in_ 前缀 | 「入口类字段需使用 in_ 前缀」= 期望规则 |
| N-10 | 命名规范 · 出口类前缀 out_ | 出口类字段必须使用 out_ 前缀 | 「出口类字段必须使用 out_ 前缀」= 期望规则 |
| N-11 | 命名规范 · 编号后缀 code | 本表字段禁止加本表名前缀 ; 编号编码字段统一使用 code 后缀 | v2「编号编码字段统一使用 code 后缀」= 期望规则 |
| N-12 | 命名规范 · 单位字段后缀 amount_unit | 名词术语规范 ; 数量含单位字段命名规范 | 「数量含单位字段命名规范」obj=goods_unit，desc 明确 amount_unit 后缀 |
| N-13 | 命名规范 · 排序字段命名 | 字段命名必须使用 lower_snake_case ; 排序字段统一命名 sort | v2「排序字段统一命名 sort」= 期望规则 |
| N-14 | 命名规范 · 备注字段命名 | 备注字段统一命名为 remark ; 禁止使用保留关键字或类似关键字字段 | v2/v3「备注字段统一命名为 remark」= 期望规则 |
| N-15 | 命名规范 · 本表字段不加表名前缀 | 本表字段禁止拼接本表表名 | 「本表字段禁止拼接本表表名」obj=order_id/order_code/order_name = 本表字段不加表名前缀 |
| N-16 | 命名规范 · 金额数量精度 / 建库规范 · 禁用 double | 数量金额统一使用 decimal(20, 6) ; 禁止使用 double 类型 ; 禁止使用 float 浮点类型 | v1「禁止使用 double 类型」+ v3「数量金额统一使用 decimal(20, 6)」覆盖两条期望规则 |
| T-01 | 名词术语 · 主键命名 | 业务字段必须使用 biz_ 前缀 ; 主键字段命名必须为 id ; 非负数字必须加 UNSIGNED | 「主键字段命名必须为 id」= 期望规则 |
| T-05 | 名词术语 · 状态命名 | 状态字段应使用 status ; 状态字段注释需说明枚举值 | 「状态字段应使用 status」= 期望规则 |
| T-07 | 名词术语 · 链接/来源命名 | 命名未使用标准名词术语 | 「命名未使用标准名词术语」desc 逐条给出 link→url、href→download_url、origin→source、src→source，正是期望规则（链接 url / 来源 source） |
| T-08 | 名词术语 · 版本命名 | 基类字段必须命名为 version ; 字段命名须使用标准术语单词 | v1「基类字段必须命名为 version」desc「版本字段被命名为缩写 ver，不符合…version 的强制要求」= 期望规则（版本→version） |
| T-11 | 名词术语 · 用户字段命名 | 字段命名必须使用标准名词术语 | 「字段命名必须使用标准名词术语」8 条 desc 逐字给出 username/password/nick/email/gender/birthday/role/duty = 期望规则 |
| T-12 | 名词术语 · 业务/地址字段命名 | 字段命名未使用标准术语 | 「字段命名未使用标准术语」8 条 desc 逐字给出 dept/organ/company/goods/address/zip/phone/contact = 期望规则 |

### 部分命中（3 例）

| case | 期望规则 | 上报的 rule_name | 判定依据 |
|---|---|---|---|
| F-06 | 建表规范 · 布尔字段名用名词 | 基础字段停用标记命名违规 ; 基础字段删除标记命名违规 | 「基础字段删除标记命名违规 / 停用标记命名违规」desc「is_delete 命名不规范」「not_enabled 反向命名不规范」，命中同一批布尔字段的命名缺陷，但未表述为「布尔列名用名词」 |
| T-03 | 名词术语 · 类型命名 | 命名须使用术语字典标准词 ; 禁止使用保留关键字或疑似关键字命名 | v2「命名须使用术语字典标准词」desc「category、kind 非术语字典标准词」触及类型术语缺陷，但未给出期望标准词 type（v1 只把 class 当关键字） |
| T-09 | 名词术语 · 删除/禁用命名 | 缺少基础字段 deleted ; 缺少基础字段 disabled | 「缺少基础字段 deleted / disabled」desc 明确「违规用 del_flag 和 is_delete 替代」「用 enable_flag 替代且语义相反」，识别了同一字段的术语缺陷，但归到建表模板缺字段规则 |

### 漏检（15 例）—— 我的漏检名单

| case | 期望规则 | 上报的 rule_name | 判定依据 |
|---|---|---|---|
| D-01 | 建库规范 · 生产库表名 db_ 前缀 | (无违规) | violations 为空；表名 order_info 缺 db_ 前缀未被报告，summary 反而描述了另一条（code 字段长度 varchar(30)） |
| D-02 | 建库规范 · 必须使用 InnoDB | (无违规) | violations 为空；summary 明确写了 MyISAM 违反 InnoDB 要求（被 DoubleCheck 过滤） |
| D-05 | 建库规范 · 禁止触发器 | (无违规) | violations 为空；summary 明确写了脚本含触发器违反禁触发器（被过滤） |
| D-06 | 建库规范 · 禁止存储过程/自定义函数 | (无违规) | violations 为空；summary 明确写了存储过程/自定义函数违规（被过滤） |
| D-07 | 建库规范 · 字符集必须 utf8mb4 | 非负数字类型必须加 UNSIGNED | 仅报「非负数字类型必须加 UNSIGNED」，未触及期望的 DEFAULT CHARSET=utf8（应为 utf8mb4） |
| D-08 | 建库规范 · 字符集必须 utf8mb4 / 建表规范 · 字段不手写字符集 | (无违规) | violations 为空；summary 明确写了 latin1 与手写 CHARACTER SET（两条期望规则均被过滤） |
| F-04 | 建表规范 · 唯一索引 uniq_ 前缀 | 非负数字类型必须加 UNSIGNED | 仅报「非负数字类型必须加 UNSIGNED」，未触及期望的 UNIQUE KEY uk_channel_code / channel_code_unique 缺 uniq_ 前缀 |
| F-07 | 建表规范 · 单字符字段用 char(1) | (无违规) | violations 为空；summary 明确写了 is_split VARCHAR(1) 应为 char(1)（被过滤） |
| F-11 | 建表规范 · 大于1整数用 int | 数量类字段必须使用 decimal | 仅报「数量类字段必须使用 decimal」(total_amount)，未触及期望的「大于1整数用 int」（valuation_mode VARCHAR(20) 未提及且建议类型不同） |
| F-12 | 建表规范 · 字段不手写字符集 | (无违规) | violations 为空；summary 明确写了 code/remark 手写字符集违反规范第10条（被过滤） |
| N-03 | 命名规范 · 关联字段命名 | 关联表命名必须以 r_ 开头 | 唯一违规是「关联表命名必须以 r_ 开头」obj=db_order_relation（关联表 r_ 前缀，属 D-16 的规则）；本例期望的是关联字段命名（uid/dept 应为 表名_字段），报告完全未提 uid/dept。lead 仅凭 2-gram「关联」判为命中，属过度判定 |
| T-02 | 名词术语 · 名称命名 | 本表字段禁止加表名前缀 | 仅报「本表字段禁止加表名前缀」(goods_title)，未触及期望的 名称→name（title 未提及） |
| T-04 | 名词术语 · 上级命名 | 命名需采用 lower_snake_case | 仅报「命名需采用 lower_snake_case」(parentCode)，未触及期望的 上级→parent（superior_id/parentCode） |
| T-06 | 名词术语 · 审核/标识命名 | 编号编码命名后缀必须为 _code | 仅报「编号编码命名后缀必须为 _code」(mark_no)，未触及期望的 审核→audit / 标识→tag（review/check_flag） |
| T-10 | 名词术语 · 关联/路径命名 | (无违规) | violations 为空；缺陷只出现在 summary 里（rel_id 未用标准术语 relation）。报告层面=漏检 |

## D. 过度判定审计（over-claiming）

对 lead 计入命中的 **54** 例逐例审查（而不是只做关键词过滤）。先用数据驱动的方式找出「通用词元」：在全部 147 条上报 rule_name 中，占比 >15% 的 2-gram 只有 8 个 —— `字段`(57.8%)、`使用`(38.8%)、`必须`(36.1%)、`命名`(33.3%)、`段命`(18.4%)、`术语`(17.7%)、`禁止`(17.7%)、`本表`(16.3%)；没有任何 ASCII 词元超过 15%。

自动过滤只标出 2 例「唯一证据是通用词」的用例（N-15 靠 2-gram「本表」、M-20 靠 2-gram「注释」），但**逐例人工审查后判定这两例都是实质命中**（N-15 的 rule_name「本表字段禁止拼接本表表名」就是期望规则本身；M-20 的「主键必须包含注释 / 基类字段必须包含中文注释」正是「字段缺少注释」）。也就是说，自动的通用词启发式在这批数据上**既漏杀也误留**。

**判定为过度判定的（1 例）**：

| case | 期望规则 | lead 采信的匹配 | 为什么是虚假命中 |
|---|---|---|---|
| **N-03** | 命名规范 · 关联字段命名（外键字段用 `表名_字段`） | 「关联表命名必须以 r_ 开头」（2-gram「关联」） | 本例 SQL 为 `db_order_relation(uid, dept)`，期望缺陷是**关联字段**命名（uid/dept 未用 `user_id`/`dept_id`）。上报的却是**关联表名**必须 `r_` 开头的规则（该规则对应反例 D-16），对象是表名而非字段，报告只字未提 uid/dept。二者共享的只有「关联」这个领域词 |

结论：lead 的 54 例里 **53 例实质成立、1 例（N-03，约 1.9%）虚假**。这说明其「语义命中」的**假阳性率低但非零**，且失败模式是*领域邻接词*（关联表 vs 关联字段），不是「命名/字段/规范」这类万能词 —— 后者在被 2-gram 停用词剥离后基本不会单独造成误判。

## E. 重复违规 / 计数膨胀

`violations` 内出现**同名 rule_name 重复**的用例共 **22** 例，重复造成的多余条目 **41** 条（原始违规条目 147 条、去重后按名称计 97 个、rule_id 100 个）。最严重的几例：

| case | 违规条数 | 重复的 rule_name | 次数 |
|---|---|---|---|
| T-11 | 8 | 字段命名必须使用标准名词术语 | 8 |
| T-12 | 8 | 字段命名未使用标准术语 | 8 |
| D-10 | 7 | 禁止使用保留关键字 | 4 |
| T-07 | 4 | 命名未使用标准名词术语 | 4 |
| D-15 | 3 | TINYINT 统一使用 TINYINT(4) | 3 |
| N-15 | 3 | 本表字段禁止拼接本表表名 | 3 |
| D-12 | 2 | 数字类型需加 UNSIGNED | 2 |
| F-03 | 2 | 普通索引必须以 idx_ 开头 | 2 |

- 这类重复多数是**逐字段实例**（`target_object` 不同，如 T-11/T-12 各 8 个字段、T-07 4 个字段），语义上并非重复计数；但它们以**完全相同的 rule_name** 呈现，任何按 rule_name 聚合、或直接把 `len(violations)` 当「检出问题数」的指标都会被**系统性放大**：147 条上报条目中有 **41 条是同名重复**，占 27.9%（去重后 106 条）。
- 另有 3 例（`D-10`、`N-02`、`T-12`）同名 rule_name 对应**不同的 rule_id**（D-10 的 4 条关键字违规分别是 desc/group/index/value 四个 rule_id），说明「同名不同规则」确实存在，进一步说明按名称聚合不可靠。
- **附带发现（规则名规范化 bug）**：severity 字段取值不统一 —— `ERROR` 134 条、`WARN` 8 条、`WARNING` 5 条。同一语义两种拼写，会让任何按 severity 分组的统计出错（例如「WARN 级违规数」到底是 8 还是 13）。

## F. 内部矛盾（summary 描述了违规，却判为合规 / violations 为空）

命中 8 例反例，全部满足 `is_compliant == true` **且** `violations == []` **且** `score == 100`，而 `summary` 明文描述了违规：

| case | is_compliant | violations | summary 摘录 | 是否描述了*期望规则* |
|---|---|---|---|---|
| D-02 | true | 0 | 「表结构整体符合规范，唯一问题是使用 MyISAM 引擎，违反必须使用 InnoDB 的强制要求，需改为 InnoDB。」 | **是** |
| D-05 | true | 0 | 「db_order 表结构基本合规，但脚本包含触发器，违反建库规范中禁止触发器的要求，需移除触发器并由业务应用逻辑实现。」 | **是** |
| D-06 | true | 0 | 「输入为存储过程和自定义函数，违反规范禁止使用存储过程与自定义函数的规定，需移除并改为应用层实现。」 | **是** |
| D-08 | true | 0 | 「表结构主体符合基类字段要求，但字符集使用 latin1，不符合统一 utf8mb4 规范；code 字段手写 CHARACTER SET/COLLATE，需移除。」 | **是** |
| F-07 | true | 0 | 「DDL 整体基本合规：7 个基类字段齐全，主键、引擎、字符集和注释均符合规范；仅 is_split 字段类型不符合 1 字符字段应使用 char(1) 的要求。」 | **是** |
| F-12 | true | 0 | 「字段 code 和 remark 手写了字符集和排序规则，违反规范[2]第10条；其余表定义符合规范。」 | **是** |
| T-10 | true | 0 | 「表整体符合建表模板与引擎、字符集、注释要求，7 个基类字段齐备，无外键、无浮点金额字段。唯一问题是关联字段命名 rel_id 未使用标准术语 relation，与同表 relation_code 命名不一致，建议统一为 relation_id。」 | **是** |
| D-01 | true | 0 | 「整体符合基类字段与引擎规范，但 code 字段长度不符合字符串默认长度规范，需调整为 varchar(30)。」 | 否（描述的是另一条） |

判定：**7 例（D-02、D-05、D-06、D-08、F-07、F-12、T-10）summary 里描述的正是该例的期望规则** —— 模型已正确识别缺陷、写进 summary，但 `violations` 被清空。这与 lead 报告中所称的 anti-hallucination「DoubleCheck」过滤行为一致：**双检过滤器在这 7 例上把真阳性当成幻觉删掉了**，直接造成 7/76 = 9.2% 的假阴性。这是本次评测中最有价值的机制性发现。

`D-01` 是另一种矛盾：summary 声称的问题是「code 字段长度不符合字符串默认长度规范，需调整为 varchar(30)」，而期望规则是「表名未以 db_ 开头」。即模型**自己编造了一条与用例无关的规则**（且该 SQL 的表名 `order_info` 同时缺 `db_` 前缀、又使用了疑似关键字 `order`，两条真缺陷一条都没报），属于「合规结论 + 描述违规 + 张冠李戴」的复合自相矛盾。

反向检查（判不合规但 summary 声称完全合规）：仅 `M-17` 一例命中我的宽松措辞正则，人工核对后认为**不构成矛盾** —— 其 summary 为「DDL 整体符合规范，但缺少 ENGINE=InnoDB 引擎声明，不满足建表模板要求」，转折后明确承认了违规。

另有 2 例被我的人工检查排除：`P-03`、`P-05` 是无违规的正例，summary 为「…未发现违规项」，与判定一致，只是被我最初的正则（含「未」「应」）误捞。

另有一类**规则方向矛盾**（不是 summary/violations 矛盾，而是规则被反着用），在扫描前缀类规则时发现 1 例：

- `M-19` 的第 2 条违规：「表名使用库前缀 | 表名 db_order 使用了库前缀 db_，违反库前缀使用规范」。这与同一批数据里的 `D-09`「生产表名必须以 db_ 开头（表名 order 缺少 db_ 前缀）」**完全相反**，也与索引中 `D-01`（建库规范 · 生产库表名 db_ 前缀）和命名规范15「库前缀…统一使用 db_」相反。即检查器对 `db_` 前缀在 `order`（缺前缀=违规）与 `db_order`（有前缀=违规）两个方向**同时判违规**，逻辑上不可同时成立。这属于规则极性错误，会污染违规计数与规则命中统计。

（对照：`D-16`、`N-03` 对 `r_` 前缀方向一致，均判「未以 r_ 开头」为违规，无方向冲突。）

## 与 lead 结论的分歧清单（汇总）

| 位置 | lead 的说法 | 我的复核 | 性质 |
|---|---|---|---|
| claim 3 / P-01 | 对照例被误判为不合规 | DDL 确实违反命名规范16（同 N-15），判错为对；对照组标注有误 | CONTROVERSIAL → REFUTE |
| claim 3 / P-04 | 对照例被误判为不合规 | 同上（db_order.order_money） | CONTROVERSIAL → REFUTE |
| claim 3 / P-02 | 对照例被误判为不合规 | 可辩护的误报，且与 P-03 的相同写法判定不一致 | CONFIRM（并补充不一致证据） |
| claim 4 | 语义命中 54/76（71.1%） | 算术可复现；但 N-03 应剔除、5 例应计入，按同一口径为 58/76（76.3%） | 算术 CONFIRM / 指标 REFUTE |
| 22 例「语义未命中」名单 | 含 N-02、T-07、T-08、T-11、T-12 | 这 5 例的 description 逐字给出了期望标准词，实为命中 | REFUTE |
| 22 例名单（可选） | 含 T-03、T-09、F-06 | 部分命中（缺陷族识别、标准词/规则名不到位） | 部分分歧 |
| 命中名单 | 含 N-03 | 虚假命中（关联表 vs 关联字段） | REFUTE |
| 漏检名单 | 8 例漏检 | 一致（并经 SQL 回读确认 8 例缺陷真实存在） | CONFIRM |
| 未提及 | — | 额外发现：`M-19` 存在 `db_` 前缀规则极性反转；severity 词汇 `WARN`/`WARNING` 混用；22 例 violations 内同名重复 | 补充 |

## 残余不确定性

1. **命中口径本身是价值判断**。「rule_name 是否命中」与「缺陷是否被检出」是两个不同的指标：本报告给出的 58/76 采用后者（更宽松但更贴近 RAG 检索/检出能力），lead 的 54/76 混合了两者。若 lead 的原意是「模型是否引用了正确规则名」，则 54 甚至偏高（应为 53，剔除 N-03），而**规则名保真度只有 7/76（严格命中）**才是该口径下更应强调的数字。请 lead 明确指标定义后再引用。
2. 我的 3 例 PARTIAL（T-03、T-09、F-06）是灰区裁决：模型识别了同一批字段的术语缺陷，但没有给出期望的标准词/规则名。把 58 与 61 视为区间下/上界更稳妥。
3. 我没有逐条核对 76 例反例 SQL 是否都真实含有期望缺陷（只完整核对了 8 例漏检 + 13 例争议例的 SQL，共 21 例）。剩余用例的「反例有效性」未经独立验证；若某些反例本身标注有误，双方的分母都需要修正。
4. 「DoubleCheck 过滤掉了真阳性」是从 `summary` 与 `violations` 的差异**推断**出的机制，我没有阅读也不允许运行 `app/` 下的流水线代码来证实过滤器实现。它严格来说是一个**强相关证据**（7 例 summary 与期望规则逐条吻合），而非直接观测。
5. citations 我只核对了非空性（81/81 非空），未核对引用切块是否真的对应该规则（`expected_chunks` 的命中率不在本次任务范围）。
6. 分片并行性与时间戳一致性仅能证明「确实发生过一次真实的、耗时与并行度自洽的运行」；它不能排除结果被人工改写后再落盘（但 sql 与索引逐字符一致、violation_count 自洽、elapsed 与时间戳自洽这三点都降低了这种可能）。

## 附：复核产物

- `evaluation/results/verify/verify.py` / `analysis.json` / `analysis.txt` —— A、B、C、E、F 的可复现计算
- `evaluation/results/verify/overclaim.py` / `overclaim.json` / `overclaim.txt` —— D 的自动过滤
- `evaluation/results/verify/sheet.py` / `sheet.txt` —— 76 例逐例人工裁决底稿（期望规则、clause、全部 rule_name/description/target_object）
- `evaluation/results/verify/controls.py` / `control_and_F.txt` —— 5 个对照例 SQL 与 F 类 summary 原文
- `evaluation/results/verify/extra.py` / `extra_checks.txt` —— 时间戳、字段一致性、聚合统计
- `evaluation/results/verify/adjudicate.py` / `adjudication.json` —— 76 例最终裁决（HIT/PARTIAL/MISS）与分歧名单
- `evaluation/results/verify/artifact_hashes.txt` —— 复核所用 7 个原始工件的 SHA256（复核结束时重算核对，未见变化；`shard_*.jsonl` 与索引的 mtime 均早于本次复核开始时间）
