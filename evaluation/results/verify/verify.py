# -*- coding: utf-8 -*-
"""
Independent verification of the 81-case SQL-DDL compliance evaluation.

Inputs (authoritative, raw only):
  evaluation/negative_cases_index.json
  evaluation/results/shard_{1..6}_6.jsonl
Everything is recomputed here; the lead's merged_results.json / summary.json /
执行报告.md are never read.

Outputs (all under evaluation/results/verify/):
  analysis.json        machine-readable findings
  analysis.txt         human-readable dump used for manual adjudication
"""
import json, os, re, collections, io, math

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RES = os.path.join(ROOT, 'evaluation', 'results')

def rj(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

# ---------------------------------------------------------------- load raw
index = rj(os.path.join(ROOT, 'evaluation', 'negative_cases_index.json'))
idx_by_id = {c['case_id']: c for c in index}

shards = ['shard_%d_6.jsonl' % i for i in range(1, 7)]
raw = []          # (shard, lineno, record)
per_shard_lines = {}
parse_errors = []
for s in shards:
    p = os.path.join(RES, s)
    n = 0
    with open(p, encoding='utf-8') as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            n += 1
            try:
                raw.append((s, ln, json.loads(line)))
            except json.JSONDecodeError as e:
                parse_errors.append((s, ln, str(e)))
    per_shard_lines[s] = n

out = {}
A = {}

# ------------------------------------------------- A. completeness
A['shard_line_counts'] = per_shard_lines
A['total_raw_records'] = len(raw)
A['parse_errors'] = parse_errors

id_counts = collections.Counter(r['case_id'] for _, _, r in raw)
A['duplicate_case_ids_in_results'] = sorted(k for k, v in id_counts.items() if v > 1)
A['unique_case_ids_in_results'] = len(id_counts)

idx_ids = set(idx_by_id)
res_ids = set(id_counts)
A['missing_from_results'] = sorted(idx_ids - res_ids)
A['extra_in_results_not_in_index'] = sorted(res_ids - idx_ids)

A['status_counts'] = dict(collections.Counter(r.get('status') for _, _, r in raw))
A['non_ok_records'] = [{'case_id': r['case_id'], 'status': r.get('status'), 'error': r.get('error')}
                       for _, _, r in raw if r.get('status') != 'ok']
A['records_with_error_field'] = [{'case_id': r['case_id'], 'error': r.get('error')}
                                 for _, _, r in raw if r.get('error')]

# sql text equality + metadata consistency
sql_mismatch, kind_mismatch, exp_mismatch = [], [], []
for s, ln, r in raw:
    c = idx_by_id.get(r['case_id'])
    if not c:
        continue
    if r.get('sql') != c.get('sql'):
        sql_mismatch.append({'case_id': r['case_id'], 'shard': s,
                             'len_result': len(r.get('sql') or ''), 'len_index': len(c.get('sql') or ''),
                             'same_after_norm_ws': (r.get('sql') or '').replace('\r\n', '\n').strip()
                                                   == (c.get('sql') or '').replace('\r\n', '\n').strip()})
    if r.get('kind') != c.get('kind'):
        kind_mismatch.append({'case_id': r['case_id'], 'result': r.get('kind'), 'index': c.get('kind')})
    if (r.get('expected_rule_names') or []) != (c.get('expected_rule_names') or []):
        exp_mismatch.append({'case_id': r['case_id'],
                             'result': r.get('expected_rule_names'), 'index': c.get('expected_rule_names')})
A['sql_exact_mismatch'] = sql_mismatch
A['kind_mismatch'] = kind_mismatch
A['expected_rule_names_mismatch'] = exp_mismatch
out['A'] = A

# per-case record lookup
rec_by_id = {r['case_id']: r for _, _, r in raw}

negatives = [c['case_id'] for c in index if c['kind'] == 'negative']
positives = [c['case_id'] for c in index if c['kind'] == 'positive']

# ------------------------------------------------- B. verdicts
B = {'n_negative_expected': len(negatives), 'n_positive_expected': len(positives)}
neg_compliant = [cid for cid in negatives if rec_by_id[cid].get('is_compliant') is True]
neg_noncompliant = [cid for cid in negatives if rec_by_id[cid].get('is_compliant') is False]
neg_other = [cid for cid in negatives if rec_by_id[cid].get('is_compliant') not in (True, False)]
B['negative_judged_compliant_FALSE_NEGATIVE'] = neg_compliant
B['negative_judged_noncompliant'] = len(neg_noncompliant)
B['negative_verdict_not_boolean'] = neg_other
B['negative_detection_rate_pct'] = round(100.0 * len(neg_noncompliant) / len(negatives), 1)

pos_noncompliant = [cid for cid in positives if rec_by_id[cid].get('is_compliant') is False]
pos_compliant = [cid for cid in positives if rec_by_id[cid].get('is_compliant') is True]
B['positive_judged_noncompliant_FALSE_ALARM'] = pos_noncompliant
B['positive_judged_compliant'] = pos_compliant
B['negative_with_empty_violations'] = [cid for cid in negatives if not (rec_by_id[cid].get('violations') or [])]
B['positive_with_nonempty_violations'] = [cid for cid in positives if (rec_by_id[cid].get('violations') or [])]
# consistency between is_compliant and violations emptiness
B['verdict_violation_inconsistency'] = [
    {'case_id': cid, 'is_compliant': rec_by_id[cid].get('is_compliant'),
     'n_violations': len(rec_by_id[cid].get('violations') or [])}
    for cid in sorted(idx_ids)
    if (rec_by_id[cid].get('is_compliant') is True) != (len(rec_by_id[cid].get('violations') or []) == 0)
]
out['B'] = B

# ------------------------------------------------- C. hit-rate, own matcher
# --- corpus statistics on reported rule names (for data-driven "generic token" detection)
LAT = re.compile(r'[a-z0-9_]{2,}')
CJK = re.compile(r'[\u4e00-\u9fff]+')
# keep '_' : `lower_snake_case`, `in_`, `r_`, `idx_` are meaningful atoms
PUNCT = re.compile(r"[^0-9a-z_\u4e00-\u9fff]+")

all_rule_names = []
for cid in idx_ids:
    r = rec_by_id.get(cid) or {}
    for v in (r.get('violations') or []):
        all_rule_names.append(v.get('rule_name') or '')
n_rules_total = len(all_rule_names)

def norm_text(t):
    return PUNCT.sub('', (t or '').lower())

norm_rule_names = [norm_text(x) for x in all_rule_names]
lat_df = collections.Counter()
cjk_df = collections.Counter()
for nr in norm_rule_names:
    for tk in set(LAT.findall(nr)):
        lat_df[tk] += 1
    for run in CJK.findall(nr):
        for i in range(len(run) - 1):
            cjk_df[run[i:i + 2]] += 1
        if len(run) == 1:
            cjk_df[run] += 1

# a token is "generic" when it occurs in > 15% of all reported rule names
GEN_THRESH = 0.15
generic_lat = {t for t, n in lat_df.items() if n / max(n_rules_total, 1) > GEN_THRESH}
generic_cjk = {g for g, n in cjk_df.items() if n / max(n_rules_total, 1) > GEN_THRESH}

# stopwords for the expected-rule concept (my own list, independent of the lead's)
STOP = ['必须', '禁止', '不得', '统一', '使用', '命名', '规范', '字段', '表名', '不允许', '尽量',
        '要求', '需要', '不要', '可以', '建议', '标准', '应该', '应在', '都要', '中文', '注释',
        '包含', '正确', '一致', '一致。', '设计']
STOP_RE = re.compile('|'.join(STOP))

def my_evidence(expected_rule):
    """Return (discriminative_tokens, weak_tokens) for one expected rule string."""
    concept = expected_rule.split('·')[-1].strip() if '·' in expected_rule else expected_rule
    stripped = STOP_RE.sub('', concept)
    lat = set(LAT.findall(concept.lower()))
    cjk = set()
    for run in CJK.findall(stripped):
        for i in range(len(run) - 1):
            cjk.add(run[i:i + 2])
        if len(run) == 1:
            cjk.add(run)
    strong = ({t for t in lat if t not in generic_lat} |
              {g for g in cjk if g not in generic_cjk})
    weak = (lat - strong) | (cjk - strong)
    return strong, weak

def my_match(expected_rule_names, violations):
    """Own matcher: discriminative token/gram overlap with reported rule name."""
    det = [{'rule_id': v.get('rule_id') or '', 'rule_name': v.get('rule_name') or '',
            'norm': norm_text(v.get('rule_name') or ''), 'desc': v.get('description') or '',
            'obj': v.get('target_object') or '', 'sev': v.get('severity')} for v in violations]
    hits, weak_hits = [], []
    for exp in expected_rule_names:
        strong, weak = my_evidence(exp)
        for i, d in enumerate(det, 1):
            s_hit = sorted(t for t in strong if t in d['norm'])
            w_hit = sorted(t for t in weak if t in d['norm'])
            if s_hit:
                hits.append({'expected': exp, 'idx': i, 'rule_name': d['rule_name'],
                             'via': s_hit, 'kind': 'strong'})
            elif w_hit:
                weak_hits.append({'expected': exp, 'idx': i, 'rule_name': d['rule_name'],
                                  'via': w_hit, 'kind': 'weak/generic'})
    return hits, weak_hits

# --- reproduce the lead's algorithm (for numeric cross-check of claim 4 only)
LEAD_STOP = ("必须", "禁止", "不得", "统一", "使用", "命名", "规范", "字段", "表名", "不允许",
             "尽量", "要求", "需要", "不要", "可以", "建议", "标准", "都要", "应在", "应该")
LEAD_STOP_RE = re.compile("|".join(LEAD_STOP))
LEAD_PUNCT = re.compile(r"[\s·、，,。.：:;；/\\|()（）\[\]【】\-*`'\"“”‘’!！?？]+")
LEAD_ASCII = re.compile(r"[a-z0-9_]{2,}")
LEAD_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")

def lead_norm(t):
    return LEAD_PUNCT.sub("", (t or "").lower())

def lead_match_case(expected_rule_names, violations):
    det = [{'rule_name': v.get('rule_name') or '', 'norm': lead_norm(v.get('rule_name') or '')}
           for v in violations]
    strict = lenient = False
    ev = []
    for exp in expected_rule_names:
        concept = exp.split('·')[-1] if '·' in exp else exp
        concept_norm = lead_norm(concept)
        for i, d in enumerate(det, 1):
            if d['norm'] and concept_norm and (concept_norm in d['norm'] or d['norm'] in concept_norm):
                strict = lenient = True
                ev.append(('strict', exp, d['rule_name'], '子串: ' + concept_norm))
        lowered = exp.lower()
        ascii_tokens = set(LEAD_ASCII.findall(lowered))
        stripped = LEAD_STOP_RE.sub('', concept)
        grams = set()
        for run in LEAD_CJK_RUN.findall(stripped):
            if len(run) < 2:
                if run:
                    grams.add(run)
            else:
                grams |= {run[i:i + 2] for i in range(len(run) - 1)}
        for tk in sorted(ascii_tokens):
            for i, d in enumerate(det, 1):
                if tk in d['norm']:
                    lenient = True
                    ev.append(('semantic', exp, d['rule_name'], 'ASCII: ' + tk))
        for g in sorted(grams):
            for i, d in enumerate(det, 1):
                if g in d['norm']:
                    lenient = True
                    ev.append(('semantic', exp, d['rule_name'], '2-gram: ' + g))
    uniq, seen = [], set()
    for e in ev:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    return bool([e for e in uniq if e[0] == 'strict']), lenient, uniq

C = {'n_rules_total_in_corpus': n_rules_total,
     'generic_ascii_tokens_gt15pct': {t: round(lat_df[t] / n_rules_total, 3) for t in sorted(generic_lat)},
     'generic_cjk_grams_gt15pct_count': len(generic_cjk),
     'generic_cjk_grams_gt15pct': {g: round(cjk_df[g] / n_rules_total, 3)
                                   for g in sorted(generic_cjk, key=lambda x: -cjk_df[x])[:60]},
     'per_case': {}}

for cid in negatives:
    c = idx_by_id[cid]
    r = rec_by_id[cid]
    vios = r.get('violations') or []
    hits, weak = my_match(c['expected_rule_names'] or [], vios)
    ls, ll, lev = lead_match_case(c['expected_rule_names'] or [], vios)
    C['per_case'][cid] = {
        'expected': c['expected_rule_names'],
        'module': c['module'],
        'is_compliant': r.get('is_compliant'),
        'reported_rule_names': [v.get('rule_name') for v in vios],
        'my_strong_hits': hits,
        'my_weak_only_matches': weak,
        'my_hit': bool(hits),
        'my_weak_hit': bool(hits) or bool(weak),
        'lead_strict': ls,
        'lead_lenient': ll,
        'lead_evidence': [{'tier': t, 'expected': e, 'rule_name': rn, 'via': v} for t, e, rn, v in lev],
    }

my_hits = [cid for cid in negatives if C['per_case'][cid]['my_hit']]
my_weak_hits = [cid for cid in negatives if C['per_case'][cid]['my_weak_hit']]
lead_strict = [cid for cid in negatives if C['per_case'][cid]['lead_strict']]
lead_lenient = [cid for cid in negatives if C['per_case'][cid]['lead_lenient']]

C['my_hit_count'] = len(my_hits)
C['my_hit_list'] = my_hits
C['my_weak_hit_count'] = len(my_weak_hits)
C['lead_strict_count_reproduced'] = len(lead_strict)
C['lead_strict_list_reproduced'] = lead_strict
C['lead_lenient_count_reproduced'] = len(lead_lenient)
C['lead_lenient_list_reproduced'] = lead_lenient

# disagreements
LEAD_SEMANTIC_MISS = ["D-01","D-02","D-05","D-06","D-07","D-08","F-04","F-06","F-07","F-11","F-12",
                      "N-02","T-02","T-03","T-04","T-06","T-07","T-08","T-09","T-10","T-11","T-12"]
C['lead_semantic_miss_given'] = LEAD_SEMANTIC_MISS
C['lead_semantic_miss_matches_reproduction'] = sorted(set(LEAD_SEMANTIC_MISS)) == sorted(
    set(negatives) - set(lead_lenient))
C['reproduced_lead_miss'] = sorted(set(negatives) - set(lead_lenient))
C['i_hit_but_lead_missed'] = sorted(set(my_hits) & set(LEAD_SEMANTIC_MISS))
C['lead_hit_but_i_missed'] = sorted(set(lead_lenient) - set(my_weak_hits))
C['i_hit_lead_hit'] = sorted(set(my_hits) & set(lead_lenient))
C['weak_only_cases'] = sorted(set(my_weak_hits) - set(my_hits))
out['C'] = C

# ------------------------------------------------- E. duplicate rule names in violations
E = {}
for cid in sorted(idx_ids):
    vios = rec_by_id[cid].get('violations') or []
    names = [v.get('rule_name') for v in vios]
    ids = [v.get('rule_id') for v in vios]
    dup_names = sorted({n for n, k in collections.Counter(names).items() if k > 1})
    dup_ids = sorted({n for n, k in collections.Counter(ids).items() if k > 1})
    if dup_names or dup_ids:
        E[cid] = {'n_violations': len(vios), 'duplicate_rule_names': dup_names,
                  'duplicate_rule_ids': dup_ids,
                  'name_counts': {n: k for n, k in collections.Counter(names).items() if k > 1},
                  'reported_violation_count_field': rec_by_id[cid].get('violation_count')}
out['E'] = E
# also: violation_count field vs actual len(violations)
out['E_violation_count_field_mismatch'] = [
    {'case_id': cid, 'field': rec_by_id[cid].get('violation_count'),
     'actual': len(rec_by_id[cid].get('violations') or [])}
    for cid in sorted(idx_ids)
    if rec_by_id[cid].get('violation_count') != len(rec_by_id[cid].get('violations') or [])]

# ------------------------------------------------- F. internal contradictions
VIOL_WORDS = ['违规', '违反', '不符合', '未', '缺少', '缺失', '禁止', '应', '错误', '不规范',
              '不满足', '存在问题', '违反规定', '问题']
F = {}
for cid in sorted(idx_ids):
    r = rec_by_id[cid]
    vios = r.get('violations') or []
    summ = r.get('summary') or ''
    suspicious = (r.get('is_compliant') is True) or (len(vios) == 0)
    if not suspicious:
        continue
    # does the summary assert a violation?
    flags = [w for w in VIOL_WORDS if w in summ]
    if flags:
        F[cid] = {'kind': r.get('kind'), 'is_compliant': r.get('is_compliant'),
                  'n_violations': len(vios), 'summary': summ, 'flags': flags,
                  'score': r.get('score')}
out['F'] = F

with open(os.path.join(HERE, 'analysis.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# ------------------------------------------------- text dump for manual review
buf = io.StringIO()
buf.write("A. COMPLETENESS\n")
buf.write(json.dumps(A, ensure_ascii=False, indent=2) + "\n\n")
buf.write("B. VERDICTS\n")
buf.write(json.dumps(B, ensure_ascii=False, indent=2) + "\n\n")
buf.write("C. HIT RATE (own matcher vs reproduced lead matcher)\n")
buf.write("my_hit=%d weak=%d | lead strict repro=%d lead lenient repro=%d\n" % (
    C['my_hit_count'], C['my_weak_hit_count'], C['lead_strict_count_reproduced'],
    C['lead_lenient_count_reproduced']))
buf.write("lead lenient list == expected miss list: %s\n" % C['lead_semantic_miss_matches_reproduction'])
buf.write("i_hit_but_lead_missed: %s\n" % C['i_hit_but_lead_missed'])
buf.write("lead_hit_but_i_missed: %s\n" % C['lead_hit_but_i_missed'])
buf.write("weak-only cases: %s\n\n" % C['weak_only_cases'])
buf.write("PER-CASE DETAIL\n")
for cid in negatives:
    d = C['per_case'][cid]
    buf.write("=" * 100 + "\n")
    buf.write("%s [%s] expected=%s | compliant=%s\n" % (cid, d['module'], json.dumps(d['expected'], ensure_ascii=False), d['is_compliant']))
    buf.write("  reported: %s\n" % json.dumps(d['reported_rule_names'], ensure_ascii=False))
    buf.write("  MY strong=%s  weak=%s  hit=%s\n" % (json.dumps(d['my_strong_hits'], ensure_ascii=False),
                                                     json.dumps(d['my_weak_only_matches'], ensure_ascii=False), d['my_hit']))
    buf.write("  LEAD strict=%s lenient=%s\n" % (d['lead_strict'], d['lead_lenient']))
    for e in d['lead_evidence']:
        buf.write("      [%s] exp=%s -> %s   (%s)\n" % (e['tier'], e['expected'], e['rule_name'], e['via']))
buf.write("\nE. DUPLICATE RULE NAMES\n")
buf.write(json.dumps(E, ensure_ascii=False, indent=2) + "\n")
buf.write("\nF. CONTRADICTIONS\n")
for cid, d in F.items():
    buf.write("--- %s kind=%s compliant=%s nviol=%d score=%s flags=%s\n" % (
        cid, d['kind'], d['is_compliant'], d['n_violations'], d['score'], d['flags']))
    buf.write("    summary: %s\n" % d['summary'])
with open(os.path.join(HERE, 'analysis.txt'), 'w', encoding='utf-8') as f:
    f.write(buf.getvalue())

print("OK A=%s B_neg_detected=%s lead_lenient=%d my_hit=%d" % (
    len(raw), B['negative_judged_noncompliant'], C['lead_lenient_count_reproduced'], C['my_hit_count']))
