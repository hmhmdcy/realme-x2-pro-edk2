"""Inspect actual resource state after the completed baseline; no capture."""
from pathlib import Path
import ast, json, sys
import host

name = sys.argv[1]
assert name in ['baseline-settled-r1', 'auto-settled-r1', 'fractional-settled-r1', 'fractional-auto-settled-r1', 'final-r1']
R = Path(__file__).resolve().parent
t = ast.parse((R.parent / 'kernel270/final-health.py').read_text())
n = next(n for n in t.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == 'code' for x in n.targets))
code = ast.literal_eval(n.value)
code = code[:code.index('manifest=')] + code[code.index('report=dict'):]
q = host.ssh('python3 -', input=code.encode(), timeout=25)
(host.PRIVATE / (name + '-private.json')).write_bytes(q.stdout)
d = json.loads(q.stdout)
d.pop('dmesg');d.pop('package_database_sha256')
d['stage'] = 271
d['passed'] = d['taint'] == 0 and not any(d['faults'].values()) and not d['camera_clients'] and all(v == 'suspended' for v in d['runtime'].values()) and len(d['rails']) == 6 and all(v['state'] == 'disabled' and v['num_users'] == '0' for v in d['rails'].values()) and not any(d['mclk_enable_counts'].values())
(R / (name + '-validation.json')).write_text(json.dumps(d, indent=2) + '\n')
print(json.dumps(d, indent=2))
