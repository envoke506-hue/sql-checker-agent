# -*- coding: utf-8 -*-
"""Exploratory pass: structure of index + shard records. Writes UTF-8 text output."""
import json, os, collections, io

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.dirname(os.path.abspath(__file__))

def rj(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def rjl(p):
    rows = []
    with open(p, encoding='utf-8') as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rows.append((ln, json.loads(line)))
    return rows

idx = rj(os.path.join(ROOT, 'evaluation', 'negative_cases_index.json'))
buf = io.StringIO()
buf.write(f"index type={type(idx).__name__} len={len(idx)}\n")
buf.write("index[0] keys: %s\n" % list(idx[0].keys()))
kinds = collections.Counter(c.get('kind') for c in idx)
buf.write("kinds: %s\n" % dict(kinds))
mods = collections.Counter(c.get('module') for c in idx)
buf.write("modules: %s\n" % dict(mods))

# duplicates in index
ids = [c['case_id'] for c in idx]
dups = [k for k, v in collections.Counter(ids).items() if v > 1]
buf.write("index duplicate case_ids: %s\n" % dups)

# expected_rule_names shape
buf.write("\n--- expected_rule_names per case ---\n")
for c in idx:
    er = c.get('expected_rule_names')
    buf.write("%s | kind=%s | n_exp=%d | %s\n" % (c['case_id'], c.get('kind'), len(er or []), json.dumps(er, ensure_ascii=False)))

# all shard records
shards = ['shard_%d_6.jsonl' % i for i in range(1, 7)]
allrows = []
for s in shards:
    p = os.path.join(ROOT, 'evaluation', 'results', s)
    rows = rjl(p)
    buf.write("\nshard %s lines=%d\n" % (s, len(rows)))
    for ln, r in rows:
        allrows.append((s, ln, r))

buf.write("\ntotal raw records=%d\n" % len(allrows))
buf.write("record keys sample: %s\n" % list(allrows[0][2].keys()))
st = collections.Counter(r.get('status') for _, _, r in allrows)
buf.write("status counts: %s\n" % dict(st))
rdups = [k for k, v in collections.Counter(r['case_id'] for _, _, r in allrows).items() if v > 1]
buf.write("raw duplicate case_ids: %s\n" % rdups)

buf.write("\n--- per record verdict summary ---\n")
for s, ln, r in allrows:
    vios = r.get('violations') or []
    buf.write("%s|%s|line=%d|kind=%s|compliant=%s|score=%s|n_viol=%d|elapsed=%s\n" % (
        s, r['case_id'], ln, r.get('kind'), r.get('is_compliant'), r.get('score'), len(vios), r.get('elapsed_seconds')))
    for v in vios:
        buf.write("      - id=%s | name=%s | sev=%s | obj=%s\n" % (
            v.get('rule_id'), v.get('rule_name'), v.get('severity'), v.get('target_object')))

with open(os.path.join(OUT, 'explore_01.txt'), 'w', encoding='utf-8') as f:
    f.write(buf.getvalue())
print("written", os.path.join(OUT, 'explore_01.txt'), len(buf.getvalue()))
