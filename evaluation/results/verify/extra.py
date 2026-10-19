# -*- coding: utf-8 -*-
"""Extra integrity checks: shard field, timestamps (real parallel run?), aggregates."""
import json, os, io, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RES = os.path.join(ROOT, 'evaluation', 'results')
idx = json.load(open(os.path.join(ROOT, 'evaluation', 'negative_cases_index.json'), encoding='utf-8'))
idx_by_id = {c['case_id']: c for c in idx}

raw = []
for i in range(1, 7):
    name = 'shard_%d_6.jsonl' % i
    for ln, line in enumerate(open(os.path.join(RES, name), encoding='utf-8'), 1):
        if line.strip():
            r = json.loads(line)
            r['_shard_file'] = name
            raw.append(r)

buf = io.StringIO()
# shard field vs filename
mismatch = [(r['case_id'], r.get('shard'), r['_shard_file']) for r in raw
            if str(r.get('shard')) not in (r['_shard_file'], r['_shard_file'].replace('shard_', '').replace('_6.jsonl', ''))]
buf.write("shard-field mismatches: %d %s\n" % (len(mismatch), mismatch[:5]))

# timestamps
def parse(t):
    if not t:
        return None
    try:
        return datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
    except Exception:
        return None

buf.write("\nper-shard time windows and elapsed:\n")
shard_windows = {}
for i in range(1, 7):
    name = 'shard_%d_6.jsonl' % i
    rows = [r for r in raw if r['_shard_file'] == name]
    starts = [parse(r.get('started_at')) for r in rows]
    ends = [parse(r.get('finished_at')) for r in rows]
    starts = [x for x in starts if x]
    ends = [x for x in ends if x]
    el = [r.get('elapsed_seconds') or 0 for r in rows]
    shard_windows[name] = (min(starts) if starts else None, max(ends) if ends else None)
    buf.write("  %s n=%d start=%s end=%s span=%.1fs elapsed_sum=%.1fs elapsed_min=%.1f elapsed_max=%.1f missing_ts=%d\n" % (
        name, len(rows),
        min(starts).isoformat() if starts else None, max(ends).isoformat() if ends else None,
        (max(ends) - min(starts)).total_seconds() if starts and ends else -1,
        sum(el), min(el), max(el),
        sum(1 for r in rows if not r.get('started_at') or not r.get('finished_at'))))

# do shard windows overlap? (evidence of parallel execution)
ws = [w for w in shard_windows.values() if w[0]]
buf.write("\nany two shard windows overlap: ")
ov = False
for a in range(len(ws)):
    for b in range(a + 1, len(ws)):
        if ws[a][0] < ws[b][1] and ws[b][0] < ws[a][1]:
            ov = True
buf.write(str(ov) + "\n")
allstart = min(w[0] for w in ws)
allend = max(w[1] for w in ws)
buf.write("global window: %s -> %s (%.1f min); sum(elapsed)=%.1f min\n" % (
    allstart.isoformat(), allend.isoformat(), (allend - allstart).total_seconds() / 60,
    sum(r.get('elapsed_seconds') or 0 for r in raw) / 60))

# elapsed_seconds vs finished-started consistency
bad = []
for r in raw:
    s, e = parse(r.get('started_at')), parse(r.get('finished_at'))
    el = r.get('elapsed_seconds')
    if s and e and el is not None:
        d = (e - s).total_seconds()
        if abs(d - el) > 2.0:
            bad.append((r['case_id'], round(d, 1), el))
buf.write("\nelapsed_seconds vs (finished-started) discrepancies >2s: %d %s\n" % (len(bad), bad[:10]))

# aggregates
vios = [(r['case_id'], v) for r in raw for v in (r.get('violations') or [])]
names = collections.Counter(v.get('rule_name') for _, v in vios)
buf.write("\ntotal violation entries: %d, distinct rule_names: %d, distinct rule_ids: %d\n" % (
    len(vios), len(names), len({v.get('rule_id') for _, v in vios})))
buf.write("top repeated rule_names:\n")
for n, k in names.most_common(8):
    buf.write("   %3d x %s\n" % (k, n))
cases_with_dups = sorted({cid for cid in {c for c, _ in vios}
                          if len({v.get('rule_name') for _, v in vios if _ is not None}) < 0})
# recompute properly
per = collections.defaultdict(list)
for cid, v in vios:
    per[cid].append(v.get('rule_name'))
dup_cases = {cid: len(ns) - len(set(ns)) for cid, ns in per.items() if len(ns) != len(set(ns))}
buf.write("\ncases with >=1 duplicated rule_name inside violations: %d\n" % len(dup_cases))
buf.write("excess entries caused by duplicates: %d\n" % sum(dup_cases.values()))
buf.write("scores distribution: %s\n" % dict(sorted(collections.Counter(r.get('score') for r in raw).items())))

# citations present?
buf.write("\ncases with zero citations: %s\n" % sorted(r['case_id'] for r in raw if not (r.get('citations') or [])))
buf.write("cases with zero citations among negatives: %s\n" % sorted(
    r['case_id'] for r in raw if r.get('kind') == 'negative' and not (r.get('citations') or [])))
buf.write("cases with empty suggested_sql: %d\n" % sum(1 for r in raw if not r.get('suggested_sql')))
buf.write("cases with empty markdown_report: %d\n" % sum(1 for r in raw if not r.get('markdown_report')))

# severity values seen
buf.write("severity values: %s\n" % dict(collections.Counter(v.get('severity') for _, v in vios)))
buf.write("expected_severity per kind: %s\n" % json.dumps(
    {'%s/%s' % k: v for k, v in collections.Counter(
        (c['kind'], c.get('expected_severity')) for c in idx).items()}, ensure_ascii=False))

open(os.path.join(HERE, 'extra_checks.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('ok')
