# -*- coding: utf-8 -*-
"""Control-case deep dive + F-candidate summaries + reverse contradictions."""
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

buf = io.StringIO()
buf.write("############ CONTROL (positive) CASES ############\n")
for cid in ['P-01', 'P-02', 'P-03', 'P-04', 'P-05']:
    c, r = idx_by_id[cid], rec[cid]
    buf.write("=" * 90 + "\n%s  title=%s\nclause=%s\nexpected_rule_names=%s\nis_compliant=%s score=%s\n" % (
        cid, c.get('title'), c.get('clause'), json.dumps(c.get('expected_rule_names'), ensure_ascii=False),
        r.get('is_compliant'), r.get('score')))
    buf.write("-- violations --\n")
    for v in r.get('violations') or []:
        buf.write("   * %s | %s | obj=%s | sev=%s\n" % (v.get('rule_name'), v.get('description'), v.get('target_object'), v.get('severity')))
    buf.write("-- summary --\n%s\n" % (r.get('summary') or ''))
    buf.write("-- SQL --\n%s\n\n" % (c.get('sql') or ''))

buf.write("\n############ F-CANDIDATE SUMMARIES (is_compliant=true or empty violations) ############\n")
d = json.load(open(os.path.join(HERE, 'analysis.json'), encoding='utf-8'))
for cid in d['F']:
    r = rec[cid]
    buf.write("--- %s kind=%s compliant=%s nviol=%d\n    %s\n" % (
        cid, r.get('kind'), r.get('is_compliant'), len(r.get('violations') or []), r.get('summary') or ''))

buf.write("\n############ REVERSE: is_compliant=false but summary claims compliance ############\n")
for cid in sorted(rec):
    r = rec[cid]
    s = r.get('summary') or ''
    vios = r.get('violations') or []
    if r.get('is_compliant') is False and vios and any(k in s for k in ['完全符合', '整体符合规范', '未发现任何', '无违规', '符合全部']):
        buf.write("--- %s : %s\n" % (cid, s))
open(os.path.join(HERE, 'control_and_F.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('ok')
