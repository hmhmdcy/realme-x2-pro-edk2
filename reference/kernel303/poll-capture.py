"""Inspect exact worker identity and save a scene-free public summary."""
from pathlib import Path
import json, re, shlex, sys
import host
HERE = Path(__file__).resolve().parent
kind, run = sys.argv[1:3]
assert kind in ['joint', 'ae'] and re.fullmatch(r'r[1-9][0-9]*', run)
code = '''
from pathlib import Path
import json
root=Path(ROOT)
state=json.loads((root/'state-private.json').read_text())
def live(pid,start):
 p=Path('/proc',str(pid),'stat')
 if not p.exists():return False
 f=p.read_text().rsplit(')',1)[1].split()
 return f[0]!='Z' and f[19]==str(start)
report=dict(state=state,matching_worker_live=live(state['pid'],state['start_ticks']),matching_child_live=live(state.get('child_pid',0),state.get('child_start_ticks','')))
if (root/'summary-private.json').exists():report['summary']=json.loads((root/'summary-private.json').read_text())
if (root/'failure-private.txt').exists():report['failure']=(root/'failure-private.txt').read_text()
print(json.dumps(report))
'''.replace('ROOT', repr('/var/lib/samurai/k303-' + kind + '-' + run))
q = host.ssh('python3 -c ' + shlex.quote(code), timeout=20)
(host.PRIVATE / f'{kind}-{run}-poll-private.json').write_bytes(q.stdout)
report = json.loads(q.stdout)
if report['state']['terminal'] and not report['matching_worker_live'] and not report['matching_child_live'] and 'summary' in report:
    public = {k: v for k, v in report['summary'].items() if k != 'exact_sof_pairs'}
    public['exact_sof_pairs_count'] = len(report['summary']['exact_sof_pairs'])
    (HERE / f'{kind}-{run}-capture-validation.json').write_text(json.dumps(public, indent=2) + '\n')
print(json.dumps(dict(state=report['state'], worker_live=report['matching_worker_live'], child_live=report['matching_child_live'],
                     capture_passed=report.get('summary', {}).get('passed'), failure=report.get('failure')), indent=2))
