# -*- coding: utf-8 -*-
"""D. Over-claiming audit: classify the lead's 54 lenient hits by evidence quality."""
import json, os, collections, io

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'analysis.json'), encoding='utf-8'))
C = d['C']
generic_cjk = set(C['generic_cjk_grams_gt15pct'])
generic_lat = set(C['generic_ascii_tokens_gt15pct'])
# filler words that carry no discriminative meaning in a rule name
FILLER = {'字段', '使用', '必须', '命名', '段命', '术语', '禁止', '本表', '规范', '表名', '后缀',
          '前缀', '类型', '表', '名', '字段名', '注释', '统一'}

buf = io.StringIO()
rows = []
for cid in C['lead_lenient_list_reproduced']:
    p = C['per_case'][cid]
    lead_vias = [(e['expected'], e['rule_name'], e['via'], e['tier']) for e in p['lead_evidence']]
    my_strong = p['my_strong_hits']
    # which rule_names did MY matcher support strongly?
    my_rules = {h['rule_name']: h['via'] for h in my_strong}
    suspicious = []
    corroborated = []
    for exp, rn, via, tier in lead_vias:
        token = via.split(': ')[-1]
        is_generic = token in generic_cjk or token in generic_lat or token in FILLER
        if rn in my_rules:
            corroborated.append((rn, via, my_rules[rn]))
        elif is_generic:
            suspicious.append((rn, via, tier))
    rows.append({'case_id': cid, 'expected': p['expected'], 'reported': p['reported_rule_names'],
                 'lead_vias': [v[2] for v in lead_vias], 'lead_matched_rules': sorted({v[1] for v in lead_vias}),
                 'my_strong': [(h['rule_name'], h['via']) for h in my_strong],
                 'suspicious_vias': suspicious, 'corroborated_vias': corroborated})

susp_cases = [r for r in rows if r['suspicious_vias']]
buf.write("cases with >=1 lead evidence that is generic AND not independently corroborated: %d\n" % len(susp_cases))
for r in susp_cases:
    buf.write("=" * 90 + "\n")
    buf.write("%s expected=%s\n" % (r['case_id'], json.dumps(r['expected'], ensure_ascii=False)))
    buf.write("  reported rule_names: %s\n" % json.dumps(r['reported'], ensure_ascii=False))
    buf.write("  all lead vias: %s\n" % json.dumps(r['lead_vias'], ensure_ascii=False))
    buf.write("  suspicious: %s\n" % json.dumps(r['suspicious_vias'], ensure_ascii=False))
    buf.write("  my strong: %s\n" % json.dumps(r['my_strong'], ensure_ascii=False))

buf.write("\n\n=== cases whose ONLY lead evidence is generic (no corroboration at all) ===\n")
only_generic = [r for r in rows if not r['my_strong']]
for r in only_generic:
    buf.write("%s expected=%s || lead vias=%s || reported=%s\n" % (
        r['case_id'], json.dumps(r['expected'], ensure_ascii=False),
        json.dumps(r['lead_vias'], ensure_ascii=False), json.dumps(r['reported'], ensure_ascii=False)))

json.dump(rows, open(os.path.join(HERE, 'overclaim.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
open(os.path.join(HERE, 'overclaim.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print("cases=%d susp=%d only_generic=%d" % (len(rows), len(susp_cases), len(only_generic)))
