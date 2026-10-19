# -*- coding: utf-8 -*-
"""Build a compact manual-adjudication sheet for all 54 lead lenient hits,
plus the full violation detail for the cases, so each match can be judged by hand."""
import json, os, io

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

d = json.load(open(os.path.join(HERE, 'analysis.json'), encoding='utf-8'))
C = d['C']

buf = io.StringIO()
buf.write("COMPACT SHEET: lead lenient hits (54) -- expected concept vs every reported rule_name\n")
buf.write("mark:  [S] lead strict, [L] lead lenient-only, [.] no lead hit\n\n")
for cid in sorted(C['per_case'], key=lambda x: (x[0], x[1:])):
    p = C['per_case'][cid]
    c = idx_by_id[cid]
    r = rec[cid]
    tag = 'S' if p['lead_strict'] else ('L' if p['lead_lenient'] else '.')
    buf.write("%-5s [%s] exp=%s\n" % (cid, tag, ' | '.join(p['expected'])))
    buf.write("       title=%s\n" % c.get('title'))
    buf.write("       clause=%s\n" % c.get('clause'))
    for i, v in enumerate(r.get('violations') or [], 1):
        buf.write("       v%d: %s || desc=%s || obj=%s || sev=%s\n" % (
            i, v.get('rule_name'), v.get('description'), v.get('target_object'), v.get('severity')))
    if not (r.get('violations') or []):
        buf.write("       (no violations) summary=%s\n" % (r.get('summary') or '')[:400])
    buf.write("\n")

open(os.path.join(HERE, 'sheet.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('cases', len(C['per_case']))
