# -*- coding: utf-8 -*-
"""Final adjudication: encodes my per-case judgement (HIT / PARTIAL / MISS) for all 76
negative cases with reasons, cross-checks it against the raw artifacts, and emits
independent_review.md + adjudication.json."""
import json, os, io, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RES = os.path.join(ROOT, 'evaluation', 'results')

idx = json.load(open(os.path.join(ROOT, 'evaluation', 'negative_cases_index.json'), encoding='utf-8'))
idx_by_id = {c['case_id']: c for c in idx}
rec = {}
for i in range(1, 7):
    for line in open(os.path.join(RES, 'shard_%d_6.jsonl' % i), encoding='utf-8'):
        if line.strip():
            r = json.loads(line)
            rec[r['case_id']] = r
A = json.load(open(os.path.join(HERE, 'analysis.json'), encoding='utf-8'))
C = A['C']

# ---------------------------------------------------------------- adjudication
# HIT   = a reported violation identifies the same defect as the expected rule
#         (rule_name may be worded differently when description/target_object pin it down)
# PARTIAL = the defect family is identified but the reported rule names a different
#         requirement / does not prescribe the expected standard term
# MISS  = the expected defect is not reported at all (or a different defect is reported)
HIT = {
 'N-01': 'v1/v2 rule_name 与期望规则几乎逐字一致（lower_snake_case 驼峰）',
 'N-02': 'v1「表名使用规范术语」desc: organization→organ；v2/v3「字段使用规范术语」desc: administrator→admin、organization→organ，正是命名规范2 的原文反例',
 'N-04': '「单价字段命名后缀必须为 price」= 期望规则',
 'N-05': '「金额字段统一命名后缀 _money」= 期望规则',
 'N-06': '「数量类字段命名与类型规范」desc 明确「未用 _amount 后缀」',
 'N-07': '「时间字段命名规范」obj=receive_date/send_ts，desc 明确 _time 后缀',
 'N-08': '「业务类字段需用 biz_ 前缀」= 期望规则',
 'N-09': '「入口类字段需使用 in_ 前缀」= 期望规则',
 'N-10': '「出口类字段必须使用 out_ 前缀」= 期望规则',
 'N-11': 'v2「编号编码字段统一使用 code 后缀」= 期望规则',
 'N-12': '「数量含单位字段命名规范」obj=goods_unit，desc 明确 amount_unit 后缀',
 'N-13': 'v2「排序字段统一命名 sort」= 期望规则',
 'N-14': 'v2/v3「备注字段统一命名为 remark」= 期望规则',
 'N-15': '「本表字段禁止拼接本表表名」obj=order_id/order_code/order_name = 本表字段不加表名前缀',
 'N-16': 'v1「禁止使用 double 类型」+ v3「数量金额统一使用 decimal(20, 6)」覆盖两条期望规则',
 'T-01': '「主键字段命名必须为 id」= 期望规则',
 'T-05': '「状态字段应使用 status」= 期望规则',
 'T-07': '「命名未使用标准名词术语」desc 逐条给出 link→url、href→download_url、origin→source、src→source，正是期望规则（链接 url / 来源 source）',
 'T-08': 'v1「基类字段必须命名为 version」desc「版本字段被命名为缩写 ver，不符合…version 的强制要求」= 期望规则（版本→version）',
 'T-11': '「字段命名必须使用标准名词术语」8 条 desc 逐字给出 username/password/nick/email/gender/birthday/role/duty = 期望规则',
 'T-12': '「字段命名未使用标准术语」8 条 desc 逐字给出 dept/organ/company/goods/address/zip/phone/contact = 期望规则',
}
for cid in ['M-%02d' % i for i in range(1, 21)]:
    HIT[cid] = 'violations 与期望基类字段/主键/引擎/注释规则一致（obj 字段核对通过）'
HIT.update({
 'D-03': '「禁止外键设计」obj=CONSTRAINT fk_order_user FOREIGN KEY = 期望规则',
 'D-04': '「表内禁止外键设计」obj=CONSTRAINT fk_detail_order FOREIGN KEY = 期望规则',
 'D-09': '「表名禁止使用保留关键字」obj=表名 order = 期望规则',
 'D-10': 'v1/v3/v4/v7「禁止使用保留关键字」obj=desc/group/index/value = 期望规则（字段名禁止关键字）',
 'D-11': '「DDL 增加字段必须标注 AFTER 指定位置」= 期望规则',
 'D-12': '「数字类型需加 UNSIGNED」= 期望规则',
 'D-13': '「避免 NULL 字段」= 期望规则',
 'D-14': 'v2「禁止使用 double 类型」obj=pay_money/fee_rate DOUBLE = 期望规则',
 'D-15': '「TINYINT 统一使用 TINYINT(4)」= 期望规则',
 'D-16': '「关联表必须以 r_ 开头」obj=db_user_role = 期望规则',
 'F-01': 'v3「三方对接表必须包含系统来源与数据来源」desc 缺 system_source = 期望规则',
 'F-02': 'v2「三方对接表需包含系统来源和数据来源」desc 缺 data_source = 期望规则',
 'F-03': '「普通索引必须以 idx_ 开头」= 期望规则',
 'F-05': 'v1「布尔类型必须使用 TINYINT(4)」= 期望规则',
 'F-08': '「单字符字段必须带默认值」obj=is_split CHAR(1) NOT NULL = 期望规则',
 'F-09': 'v2「字符串应使用 varchar(30)」obj=vehicle_number TEXT = 期望规则（大于1字符用 varchar）',
 'F-10': 'v1「整数字段类型选择规范」desc「1 个整数的状态字段应使用 TINYINT(4)，不得用 INT」= 期望规则',
})

PARTIAL = {
 'T-03': 'v2「命名须使用术语字典标准词」desc「category、kind 非术语字典标准词」触及类型术语缺陷，但未给出期望标准词 type（v1 只把 class 当关键字）',
 'T-09': '「缺少基础字段 deleted / disabled」desc 明确「违规用 del_flag 和 is_delete 替代」「用 enable_flag 替代且语义相反」，识别了同一字段的术语缺陷，但归到建表模板缺字段规则',
 'F-06': '「基础字段删除标记命名违规 / 停用标记命名违规」desc「is_delete 命名不规范」「not_enabled 反向命名不规范」，命中同一批布尔字段的命名缺陷，但未表述为「布尔列名用名词」',
}

MISS = {
 'N-03': '唯一违规是「关联表命名必须以 r_ 开头」obj=db_order_relation（关联表 r_ 前缀，属 D-16 的规则）；本例期望的是关联字段命名（uid/dept 应为 表名_字段），报告完全未提 uid/dept。lead 仅凭 2-gram「关联」判为命中，属过度判定',
 'T-02': '仅报「本表字段禁止加表名前缀」(goods_title)，未触及期望的 名称→name（title 未提及）',
 'T-04': '仅报「命名需采用 lower_snake_case」(parentCode)，未触及期望的 上级→parent（superior_id/parentCode）',
 'T-06': '仅报「编号编码命名后缀必须为 _code」(mark_no)，未触及期望的 审核→audit / 标识→tag（review/check_flag）',
 'T-10': 'violations 为空；缺陷只出现在 summary 里（rel_id 未用标准术语 relation）。报告层面=漏检',
 'D-01': 'violations 为空；表名 order_info 缺 db_ 前缀未被报告，summary 反而描述了另一条（code 字段长度 varchar(30)）',
 'D-02': 'violations 为空；summary 明确写了 MyISAM 违反 InnoDB 要求（被 DoubleCheck 过滤）',
 'D-05': 'violations 为空；summary 明确写了脚本含触发器违反禁触发器（被过滤）',
 'D-06': 'violations 为空；summary 明确写了存储过程/自定义函数违规（被过滤）',
 'D-07': '仅报「非负数字类型必须加 UNSIGNED」，未触及期望的 DEFAULT CHARSET=utf8（应为 utf8mb4）',
 'D-08': 'violations 为空；summary 明确写了 latin1 与手写 CHARACTER SET（两条期望规则均被过滤）',
 'F-04': '仅报「非负数字类型必须加 UNSIGNED」，未触及期望的 UNIQUE KEY uk_channel_code / channel_code_unique 缺 uniq_ 前缀',
 'F-07': 'violations 为空；summary 明确写了 is_split VARCHAR(1) 应为 char(1)（被过滤）',
 'F-11': '仅报「数量类字段必须使用 decimal」(total_amount)，未触及期望的「大于1整数用 int」（valuation_mode VARCHAR(20) 未提及且建议类型不同）',
 'F-12': 'violations 为空；summary 明确写了 code/remark 手写字符集违反规范第10条（被过滤）',
}

negatives = [c['case_id'] for c in idx if c['kind'] == 'negative']
assert set(HIT) | set(PARTIAL) | set(MISS) == set(negatives), (
    set(negatives) ^ (set(HIT) | set(PARTIAL) | set(MISS)))
assert not (set(HIT) & set(PARTIAL)) and not (set(HIT) & set(MISS)) and not (set(PARTIAL) & set(MISS))

lead_hits = set(C['lead_lenient_list_reproduced'])
lead_miss = set(negatives) - lead_hits
my_hits = set(HIT)
my_miss = set(MISS)
over_claim = sorted(lead_hits & my_miss)             # lead counted, I reject
under_claim = sorted(lead_miss & (my_hits | set(PARTIAL)))  # lead missed, I accept

adjud = {
 'hit': sorted(HIT), 'partial': sorted(PARTIAL), 'miss': sorted(MISS),
 'counts': {'hit': len(HIT), 'partial': len(PARTIAL), 'miss': len(MISS), 'total': len(negatives)},
 'lead_over_claim': over_claim,
 'lead_under_claim': under_claim,
 'lead_under_claim_clear_hits': sorted(lead_miss & my_hits),
 'lead_under_claim_partial': sorted(lead_miss & set(PARTIAL)),
 'lead_hit_agreed_by_me': sorted(lead_hits & my_hits),
 'lead_miss_agreed_by_me': sorted(lead_miss & my_miss),
 'doublecheck_stripped_expected_rule': ['D-02', 'D-05', 'D-06', 'D-08', 'F-07', 'F-12', 'T-10'],
}
json.dump(adjud, open(os.path.join(HERE, 'adjudication.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- report
E = A['E']
F = A['F']
EC = open(os.path.join(HERE, 'extra_checks.txt'), encoding='utf-8').read()

def tbl(ids, reasons):
    out = ['| case | 期望规则 | 上报的 rule_name | 判定依据 |', '|---|---|---|---|']
    for cid in ids:
        exp = ' / '.join(idx_by_id[cid]['expected_rule_names'])
        rn = ' ; '.join(sorted({v.get('rule_name') for v in (rec[cid].get('violations') or [])})) or '(无违规)'
        out.append('| %s | %s | %s | %s |' % (cid, exp, rn, reasons[cid]))
    return '\n'.join(out)

b = io.StringIO()
w = b.write
w('# 独立复核报告 — SQL DDL 合规检查批量评测（81 例）\n\n')
w('复核人：独立验证子代理（独立 verifier）　角色：**试图证伪**，而非复述结论。\n\n')
w('## 0. 复核范围与方法\n\n')
w('- 仅使用原始工件：`evaluation/negative_cases_index.json`（81 例索引）+ `evaluation/results/shard_{1..6}_6.jsonl`（原始逐例结果，共 81 行）。\n')
w('- **未读取、未使用**任何派生结论：`merged_results.json`、`summary.json`、`执行报告.md`、`merged_results.jsonl` 均未作为输入。\n')
w('- 未运行任何 LLM/审计流水线（未调用 `run_shard.py`），全部为静态分析。\n')
w('- 所有复核脚本与本报告均写在 `evaluation/results/verify/` 下，未修改任何其他文件。\n')
w('- 命中判定由我自行设计：先做**语料级判别性检验**（把出现在全部 147 条上报 rule_name 中占比 >15% 的词元/2-gram 视为通用词，自动剔除），再用**逐例人工裁决**（同时看 `rule_name`、`description`、`target_object`，必要时回读索引 `clause` 与原始 SQL）。**没有复用 lead 的匹配器**；lead 的匹配器仅被独立重实现一次，用于核对它的算术（claim 4 的数字）。\n\n')

w('## 1. 结论速览（逐条 CONFIRM / REFUTE）\n\n')
w('| # | Lead 的声明 | 复核结论 |\n|---|---|---|\n')
w('| 1 | 81/81 收齐、status 全 ok、零错误、零重复 id、sql 与索引完全一致 | **CONFIRM** |\n')
w('| 2 | 76 反例中 68 例判为不合规（89.5%） | **CONFIRM**（数字精确一致） |\n')
w('| 3 | 5 个对照正例中 P-01/P-02/P-04 被误判为不合规 | **数字 CONFIRM / 定性部分 REFUTE**：P-01、P-04 的 DDL 确实违反「本表字段不加表名前缀」，属**对照用例自身标注错误**，检查器判错为对；只有 P-02 是可辩护的误报 |\n')
w('| 4a | 严格命中 7/76（9.2%） | **CONFIRM**（独立重实现其算法，命中集合逐例一致） |\n')
w('| 4b | 宽松/语义命中 54/76（71.1%） | **算术 CONFIRM / 指标有效性 REFUTE**：其 54 例中 N-03 属**过度判定**应剔除，同时又**漏计**了 5 例（N-02、T-07、T-08、T-11、T-12）实质命中（另有 T-03、T-09、F-06 为部分命中）。按同一「缺陷是否被检出」口径，我的独立结果为 **58/76 = 76.3%**（含部分命中 61/76 = 80.3%） |\n\n')

w('## A. 完整性与一致性 —— CONFIRM claim 1\n\n')
w('| 检查项 | 结果 |\n|---|---|\n')
w('| 各分片原始行数 | shard_1=14, shard_2=14, shard_3=14, shard_4=13, shard_5=13, shard_6=13，合计 **81** |\n')
w('| JSON 解析失败行 | 0 |\n')
w('| 唯一 case_id | **81**（索引亦 81 且无重复） |\n')
w('| 索引中缺失 | 无 |\n')
w('| 结果中多出 | 无 |\n')
w('| 重复 case_id | 无 |\n')
w('| `status != "ok"` | **0**（全部 81 条为 ok） |\n')
w('| `error` 字段非空 | **0** |\n')
w('| `sql` 与索引逐字符相等 | **81/81 相等**，0 处不一致 |\n')
w('| `kind` / `expected_rule_names` 与索引一致 | 81/81 一致（附加核对） |\n')
w('| `shard` 字段与文件名一致 | 81/81 一致（如 `1/6`） |\n')
w('| `citations` / `suggested_sql` / `markdown_report` 缺项 | 0 / 0 / 0 |\n')
w('| `violation_count` 与 `len(violations)` 一致 | 81/81 一致 |\n')
w('| `is_compliant` 与「violations 是否为空」自洽 | 81/81 自洽（无矛盾记录） |\n')
w('| `elapsed_seconds` 与 finished−started 偏差 ≤2s | 81/81 一致 |\n\n')
w('**运行真实性旁证**（额外独立检查）：6 个分片的时间窗全部相互重叠，全局窗口 '
  '2026-10-16 15:12:12 → 15:21:17（9.1 分钟），而各例耗时之和为 44.7 分钟 —— 与「6 路并行真实执行」相符；'
  '机器当前时间 2026-10-16 15:38，即本次评测在复核前约 17 分钟完成。未发现伪造/占位痕迹。\n\n')

w('## B. 判定计数 —— CONFIRM claim 2，拆解 claim 3\n\n')
w('**反例（76）**：判为不合规 **68** 例 → 68/76 = 89.47% ≈ **89.5%（CONFIRM）**。\n\n')
w('漏检（false negative，`is_compliant == true`）共 8 例，且这 8 例的 `violations` 均为空、`score` 均为 100：\n\n')
w('`T-10`、`D-01`、`D-02`、`D-05`、`D-06`、`D-08`、`F-07`、`F-12`\n\n')
w('我逐例回读了这 8 例的原始 SQL，**确认缺陷真实存在**（触发器、存储过程/函数、MyISAM、latin1、手写 CHARACTER SET、VARCHAR(1)、rel_id、表名缺 db_ 前缀），因此这 8 例是有效的反例，属真漏检，不是标注问题。\n\n')
w('**对照正例（5）**：判为不合规 **P-01、P-02、P-04**（与 lead 一致），P-03、P-05 通过。但「误判」的定性需要拆开：\n\n')
w('| 用例 | lead 的定性 | 我的复核 |\n|---|---|---|\n')
w('| P-01 | 误判 | **REFUTE**。其 DDL 是 `CREATE TABLE db_order`，其中 `order_money DECIMAL(20,6)`、`order_amount_unit VARCHAR(10)` 携带本表表名前缀 `order`，正是反例 **N-15** 所考察的「命名规范16 本表字段不加表名前缀」。检查器报「本表字段名禁止携带本表表名前缀」是**正确**的；该对照用例标注自相矛盾（title 声称「本模块全部规范要求均未违反」）。属**对照组构造缺陷**，不是检查器缺陷 |\n')
w('| P-02 | 误判 | **部分 CONFIRM（可辩护的误报）**。被报的是 `sort INT`、`version INT` 缺 UNSIGNED。但建库规范9 的原文是「已知不存在负数的情况下**可以**加 UNSIGNED」（许可而非强制），且建表模板本身规定 `version INT NOT NULL DEFAULT 0`（不带 UNSIGNED）。更关键的是**同一模式在不同用例中被区别对待**：P-03 的对照 DDL 同样含 `version INT NOT NULL DEFAULT 0`，却判为合规。这是检查器的不一致，而非纯粹的规则争议 |\n')
w('| P-04 | 误判 | **REFUTE**。`CREATE TABLE db_order` 含 `order_money DECIMAL(20,6)`，同样违反命名规范16（与 N-15 同规则）。检查器报错正确，对照组标注有误 |\n\n')
w('补充：P-01 中 `sort INT NOT NULL DEFAULT 0`、`version INT NOT NULL DEFAULT 0` 与 P-02 中被判违规的写法**完全相同**，但 P-01 未被报出 UNSIGNED 问题 —— 这是同批数据内部的判定不一致（对规则命中不稳定），建议 lead 在报告中显式披露，而不是只把它当作「误判」。\n\n')

w('## C. 命中率（我自己的方法）\n\n')
w('**Lead 算术的独立核对（CONFIRM）**：我按 `merge_results.py` 中记录的算法独立重实现了一次匹配器，得到严格命中 **7** 例（`N-01, M-17, M-18, D-03, D-04, D-11, D-13`），宽松命中 **54** 例，且 `76 − 54 = 22` 例未命中集合与 lead 给出的 22 例「语义未命中」名单**逐例完全一致**。即 claim 4 的两个数字在其自身口径下是**可复现、无算术错误**的。\n\n')
w('**方法说明（我的口径）**：lead 的匹配只看 `violations[].rule_name` 字符串；这会把「缺陷已识别但换了规则名/表述更泛」的命中判成漏检。我的口径是「上报的违规是否指向与期望规则**同一个缺陷**」，证据可来自 `rule_name`、`description`、`target_object` 三者，并逐例回读索引 `clause` 与原 SQL 核对。\n\n')
w('**我的逐例裁决结果（76 例）**：\n\n')
w('| 分类 | 数量 | 占比 |\n|---|---|---|\n')
w('| 命中 HIT（缺陷被明确检出） | **58** | **76.3%** |\n')
w('| 部分命中 PARTIAL（缺陷族被识别，规则名/标准词不到位） | 3 | 3.9% |\n')
w('| 漏检 MISS（未检出，或报的是另一条规则） | 15 | 19.7% |\n\n')
w('含部分命中则 **61/76 = 80.3%**；仅计入明确命中为 **58/76 = 76.3%**。两种口径都高于 lead 的 54/76（71.1%）。\n\n')
w('**与 lead 名单的具体分歧**：\n\n')
w('1. **过度判定 1 例**（lead 计命中，我判漏检）：`%s`\n' % '`, `'.join(over_claim))
w('2. **漏计明确命中 5 例**（lead 计漏检，我判命中）：`%s`\n' % '`, `'.join(adjud['lead_under_claim_clear_hits']))
w('3. **漏计部分命中 3 例**：`%s`\n' % '`, `'.join(adjud['lead_under_claim_partial']))
w('4. 双方一致：同为命中 %d 例，同为漏检 %d 例（`%s`）。\n\n' % (
    len(adjud['lead_hit_agreed_by_me']), len(adjud['lead_miss_agreed_by_me']),
    '`, `'.join(adjud['lead_miss_agreed_by_me'])))
w('净效应：lead 的 22 例「语义未命中」名单应收缩为 **15 例**（去掉 N-02、T-07、T-08、T-11、T-12，以及可选的 T-03、T-09、F-06 三例部分命中），同时把 **N-03** 补进漏检名单。\n\n')
w('### 明确命中（58 例）逐例依据\n\n')
w(tbl(sorted(HIT), HIT) + '\n\n')
w('### 部分命中（3 例）\n\n')
w(tbl(sorted(PARTIAL), PARTIAL) + '\n\n')
w('### 漏检（15 例）—— 我的漏检名单\n\n')
w(tbl(sorted(MISS), MISS) + '\n\n')

w('## D. 过度判定审计（over-claiming）\n\n')
w('对 lead 计入命中的 **54** 例逐例审查（而不是只做关键词过滤）。先用数据驱动的方式找出「通用词元」：在全部 147 条上报 rule_name 中，占比 >15% 的 2-gram 只有 8 个 —— '
  '`字段`(57.8%)、`使用`(38.8%)、`必须`(36.1%)、`命名`(33.3%)、`段命`(18.4%)、`术语`(17.7%)、`禁止`(17.7%)、`本表`(16.3%)；没有任何 ASCII 词元超过 15%。\n\n')
w('自动过滤只标出 2 例「唯一证据是通用词」的用例（N-15 靠 2-gram「本表」、M-20 靠 2-gram「注释」），但**逐例人工审查后判定这两例都是实质命中**（N-15 的 rule_name「本表字段禁止拼接本表表名」就是期望规则本身；M-20 的「主键必须包含注释 / 基类字段必须包含中文注释」正是「字段缺少注释」）。也就是说，自动的通用词启发式在这批数据上**既漏杀也误留**。\n\n')
w('**判定为过度判定的（1 例）**：\n\n')
w('| case | 期望规则 | lead 采信的匹配 | 为什么是虚假命中 |\n|---|---|---|---|\n')
w('| **N-03** | 命名规范 · 关联字段命名（外键字段用 `表名_字段`） | 「关联表命名必须以 r_ 开头」（2-gram「关联」） | 本例 SQL 为 `db_order_relation(uid, dept)`，期望缺陷是**关联字段**命名（uid/dept 未用 `user_id`/`dept_id`）。上报的却是**关联表名**必须 `r_` 开头的规则（该规则对应反例 D-16），对象是表名而非字段，报告只字未提 uid/dept。二者共享的只有「关联」这个领域词 |\n\n')
w('结论：lead 的 54 例里 **53 例实质成立、1 例（N-03，约 1.9%）虚假**。这说明其「语义命中」的**假阳性率低但非零**，且失败模式是*领域邻接词*（关联表 vs 关联字段），不是「命名/字段/规范」这类万能词 —— 后者在被 2-gram 停用词剥离后基本不会单独造成误判。\n\n')

w('## E. 重复违规 / 计数膨胀\n\n')
w('`violations` 内出现**同名 rule_name 重复**的用例共 **22** 例，重复造成的多余条目 **41** 条（原始违规条目 147 条、去重后按名称计 97 个、rule_id 100 个）。最严重的几例：\n\n')
w('| case | 违规条数 | 重复的 rule_name | 次数 |\n|---|---|---|---|\n')
for cid, v in sorted(E.items(), key=lambda kv: -max(kv[1]['name_counts'].values()))[:8]:
    nm = max(v['name_counts'], key=lambda k: v['name_counts'][k])
    w('| %s | %d | %s | %d |\n' % (cid, v['n_violations'], nm, v['name_counts'][nm]))
w('\n')
w('- 这类重复多数是**逐字段实例**（`target_object` 不同，如 T-11/T-12 各 8 个字段、T-07 4 个字段），语义上并非重复计数；但它们以**完全相同的 rule_name** 呈现，任何按 rule_name 聚合、或直接把 `len(violations)` 当「检出问题数」的指标都会被**系统性放大**：147 条上报条目中有 **41 条是同名重复**，占 27.9%（去重后 106 条）。\n')
w('- 另有 3 例（`D-10`、`N-02`、`T-12`）同名 rule_name 对应**不同的 rule_id**（D-10 的 4 条关键字违规分别是 desc/group/index/value 四个 rule_id），说明「同名不同规则」确实存在，进一步说明按名称聚合不可靠。\n')
w('- **附带发现（规则名规范化 bug）**：severity 字段取值不统一 —— `ERROR` 134 条、`WARN` 8 条、`WARNING` 5 条。同一语义两种拼写，会让任何按 severity 分组的统计出错（例如「WARN 级违规数」到底是 8 还是 13）。\n\n')

w('## F. 内部矛盾（summary 描述了违规，却判为合规 / violations 为空）\n\n')
w('命中 8 例反例，全部满足 `is_compliant == true` **且** `violations == []` **且** `score == 100`，而 `summary` 明文描述了违规：\n\n')
w('| case | is_compliant | violations | summary 摘录 | 是否描述了*期望规则* |\n|---|---|---|---|---|\n')
for cid in ['D-02', 'D-05', 'D-06', 'D-08', 'F-07', 'F-12', 'T-10', 'D-01']:
    s = (rec[cid].get('summary') or '').replace('\n', ' ')
    expected = cid in adjud['doublecheck_stripped_expected_rule']
    w('| %s | true | 0 | 「%s」 | %s |\n' % (cid, s if len(s) <= 150 else s[:150] + '…', '**是**' if expected else '否（描述的是另一条）'))
w('\n')
w('判定：**7 例（D-02、D-05、D-06、D-08、F-07、F-12、T-10）summary 里描述的正是该例的期望规则** —— 模型已正确识别缺陷、写进 summary，但 `violations` 被清空。这与 lead 报告中所称的 anti-hallucination「DoubleCheck」过滤行为一致：**双检过滤器在这 7 例上把真阳性当成幻觉删掉了**，直接造成 7/76 = 9.2% 的假阴性。这是本次评测中最有价值的机制性发现。\n\n')
w('`D-01` 是另一种矛盾：summary 声称的问题是「code 字段长度不符合字符串默认长度规范，需调整为 varchar(30)」，而期望规则是「表名未以 db_ 开头」。即模型**自己编造了一条与用例无关的规则**（且该 SQL 的表名 `order_info` 同时缺 `db_` 前缀、又使用了疑似关键字 `order`，两条真缺陷一条都没报），属于「合规结论 + 描述违规 + 张冠李戴」的复合自相矛盾。\n\n')
w('反向检查（判不合规但 summary 声称完全合规）：仅 `M-17` 一例命中我的宽松措辞正则，人工核对后认为**不构成矛盾** —— 其 summary 为「DDL 整体符合规范，但缺少 ENGINE=InnoDB 引擎声明，不满足建表模板要求」，转折后明确承认了违规。\n\n')
w('另有 2 例被我的人工检查排除：`P-03`、`P-05` 是无违规的正例，summary 为「…未发现违规项」，与判定一致，只是被我最初的正则（含「未」「应」）误捞。\n\n')

w('另有一类**规则方向矛盾**（不是 summary/violations 矛盾，而是规则被反着用），在扫描前缀类规则时发现 1 例：\n\n')
w('- `M-19` 的第 2 条违规：「表名使用库前缀 | 表名 db_order 使用了库前缀 db_，违反库前缀使用规范」。这与同一批数据里的 `D-09`「生产表名必须以 db_ 开头（表名 order 缺少 db_ 前缀）」**完全相反**，也与索引中 `D-01`（建库规范 · 生产库表名 db_ 前缀）和命名规范15「库前缀…统一使用 db_」相反。即检查器对 `db_` 前缀在 `order`（缺前缀=违规）与 `db_order`（有前缀=违规）两个方向**同时判违规**，逻辑上不可同时成立。这属于规则极性错误，会污染违规计数与规则命中统计。\n\n')
w('（对照：`D-16`、`N-03` 对 `r_` 前缀方向一致，均判「未以 r_ 开头」为违规，无方向冲突。）\n\n')

w('## 与 lead 结论的分歧清单（汇总）\n\n')
w('| 位置 | lead 的说法 | 我的复核 | 性质 |\n|---|---|---|---|\n')
w('| claim 3 / P-01 | 对照例被误判为不合规 | DDL 确实违反命名规范16（同 N-15），判错为对；对照组标注有误 | CONTROVERSIAL → REFUTE |\n')
w('| claim 3 / P-04 | 对照例被误判为不合规 | 同上（db_order.order_money） | CONTROVERSIAL → REFUTE |\n')
w('| claim 3 / P-02 | 对照例被误判为不合规 | 可辩护的误报，且与 P-03 的相同写法判定不一致 | CONFIRM（并补充不一致证据） |\n')
w('| claim 4 | 语义命中 54/76（71.1%） | 算术可复现；但 N-03 应剔除、5 例应计入，按同一口径为 58/76（76.3%） | 算术 CONFIRM / 指标 REFUTE |\n')
w('| 22 例「语义未命中」名单 | 含 N-02、T-07、T-08、T-11、T-12 | 这 5 例的 description 逐字给出了期望标准词，实为命中 | REFUTE |\n')
w('| 22 例名单（可选） | 含 T-03、T-09、F-06 | 部分命中（缺陷族识别、标准词/规则名不到位） | 部分分歧 |\n')
w('| 命中名单 | 含 N-03 | 虚假命中（关联表 vs 关联字段） | REFUTE |\n')
w('| 漏检名单 | 8 例漏检 | 一致（并经 SQL 回读确认 8 例缺陷真实存在） | CONFIRM |\n')
w('| 未提及 | — | 额外发现：`M-19` 存在 `db_` 前缀规则极性反转；severity 词汇 `WARN`/`WARNING` 混用；22 例 violations 内同名重复 | 补充 |\n\n')

w('## 残余不确定性\n\n')
w('1. **命中口径本身是价值判断**。「rule_name 是否命中」与「缺陷是否被检出」是两个不同的指标：本报告给出的 58/76 采用后者（更宽松但更贴近 RAG 检索/检出能力），lead 的 54/76 混合了两者。若 lead 的原意是「模型是否引用了正确规则名」，则 54 甚至偏高（应为 53，剔除 N-03），而**规则名保真度只有 7/76（严格命中）**才是该口径下更应强调的数字。请 lead 明确指标定义后再引用。\n')
w('2. 我的 3 例 PARTIAL（T-03、T-09、F-06）是灰区裁决：模型识别了同一批字段的术语缺陷，但没有给出期望的标准词/规则名。把 58 与 61 视为区间下/上界更稳妥。\n')
w('3. 我没有逐条核对 76 例反例 SQL 是否都真实含有期望缺陷（只完整核对了 8 例漏检 + 13 例争议例的 SQL，共 21 例）。剩余用例的「反例有效性」未经独立验证；若某些反例本身标注有误，双方的分母都需要修正。\n')
w('4. 「DoubleCheck 过滤掉了真阳性」是从 `summary` 与 `violations` 的差异**推断**出的机制，我没有阅读也不允许运行 `app/` 下的流水线代码来证实过滤器实现。它严格来说是一个**强相关证据**（7 例 summary 与期望规则逐条吻合），而非直接观测。\n')
w('5. citations 我只核对了非空性（81/81 非空），未核对引用切块是否真的对应该规则（`expected_chunks` 的命中率不在本次任务范围）。\n')
w('6. 分片并行性与时间戳一致性仅能证明「确实发生过一次真实的、耗时与并行度自洽的运行」；它不能排除结果被人工改写后再落盘（但 sql 与索引逐字符一致、violation_count 自洽、elapsed 与时间戳自洽这三点都降低了这种可能）。\n\n')

w('## 附：复核产物\n\n')
w('- `evaluation/results/verify/verify.py` / `analysis.json` / `analysis.txt` —— A、B、C、E、F 的可复现计算\n')
w('- `evaluation/results/verify/overclaim.py` / `overclaim.json` / `overclaim.txt` —— D 的自动过滤\n')
w('- `evaluation/results/verify/sheet.py` / `sheet.txt` —— 76 例逐例人工裁决底稿（期望规则、clause、全部 rule_name/description/target_object）\n')
w('- `evaluation/results/verify/controls.py` / `control_and_F.txt` —— 5 个对照例 SQL 与 F 类 summary 原文\n')
w('- `evaluation/results/verify/extra.py` / `extra_checks.txt` —— 时间戳、字段一致性、聚合统计\n')
w('- `evaluation/results/verify/adjudicate.py` / `adjudication.json` —— 76 例最终裁决（HIT/PARTIAL/MISS）与分歧名单\n')
w('- `evaluation/results/verify/artifact_hashes.txt` —— 复核所用 7 个原始工件的 SHA256（复核结束时重算核对，未见变化；`shard_*.jsonl` 与索引的 mtime 均早于本次复核开始时间）\n')

open(os.path.join(HERE, 'independent_review.md'), 'w', encoding='utf-8').write(b.getvalue())
print('report bytes', len(b.getvalue()))
print('counts', adjud['counts'])
print('over_claim', over_claim)
print('under_claim', under_claim)
print('agree_hits', len(adjud['lead_hit_agreed_by_me']), 'agree_miss', len(adjud['lead_miss_agreed_by_me']))
