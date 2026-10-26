"""Bounded follow-up after the user confirmed a lit, unobstructed rear scene.

Uses fresh capture contexts; never replays deployment or previous captures.
Scene illumination and distance are user reported, not measured.
"""
from pathlib import Path
import ast, hashlib, json
import host

R = Path(__file__).resolve().parent

def embedded(name):
    tree = ast.parse((R / name).read_text())
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'code' for t in n.targets))
    return ast.literal_eval(assignment.value)

proof = json.loads((R / 'paired-probe-build-validation.json').read_text())
assert proof['binary_sha256'] == 'e4a5692584d9eba83a01610da63875d447a7f39281a955df297ca61a519e29fa'
preflight = '''from pathlib import Path
import hashlib,json
p=Path('/run/samurai-camera270-probes/telephoto-paired-probe270')
assert hashlib.sha256(p.read_bytes()).hexdigest()==%r
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/bus/i2c/devices/8-002d/power/runtime_status').read_text().strip()=='suspended'
for p in Path('/proc').glob('[0-9]*'):
 try: name=(p/'comm').read_text().strip()
 except OSError: continue
 assert name not in ['snapshot','cam','gst-launch-1.0','telephoto-paire'], 'Camera client active'
print(json.dumps({'preflight':True}))
''' % proof['binary_sha256']
host.ssh('python3 -', input=preflight.encode(), timeout=20)

jobs = [
    ('paired-scene-r2', 'run-telephoto-paired-probe.py',
     [('k270-telephoto-paired-r1', 'k270-telephoto-paired-scene-r2'),
      ('scene_or_lighting_not_controlled=True',
       'scene_user_confirmed_lit_unobstructed=True,scene_illumination_not_measured=True')], 80),
    ('rear-jpeg-scene-r2', 'capture-two-rear-jpegs.py',
     [('k270-two-rear-jpeg-r1', 'k270-two-rear-jpeg-scene-r2')], 90),
]
for label, source, replacements, timeout in jobs:
    private = host.PRIVATE / (label + '-response-private.log')
    public = R / (label + '-validation.json')
    assert not private.exists() and not public.exists(), 'Inspect existing outcome before any repeat'
    code = embedded(source)
    for old, new in replacements:
        assert old in code
        code = code.replace(old, new)
    # A local intent record prevents replay after an ambiguous transport outcome.
    private.write_bytes(b'SUBMISSION INTENT: inspect the device context if no response follows.\n')
    q = host.ssh('python3 -', input=code.encode(), timeout=timeout, check=False)
    private.write_bytes(q.stdout + q.stderr)
    assert q.returncode == 0 and q.stdout, 'Inspect submitted context; do not repeat'
    report = json.loads(q.stdout)
    report['scene_user_confirmed_lit_unobstructed'] = True
    report['scene_illumination_not_measured'] = True
    for row in report.get('runs', []):
        row.pop('path', None)
        frames = row.pop('pts', None)
        if frames:
            row['first_pts'] = frames[0]['pts']
            row['last_pts'] = frames[-1]['pts']
    public.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'job': label, 'report': report}), flush=True)
    if label.startswith('paired'):
        assert report['exit'] == 0 and report['taint'] == 0
        assert not any(report['fault_delta'].values())
        assert report['runtime_after'] == 'suspended'
    else:
        assert report['passed']
