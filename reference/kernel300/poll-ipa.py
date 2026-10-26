"""Inspect exact worker and child identities; never infer completion from timeout."""
from pathlib import Path
import json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r[1-9][0-9]*',run)
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k300-ipa-r1')
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
'''
code=code.replace('k300-ipa-r1','k300-ipa-'+run)
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20)
report=json.loads(q.stdout);(host.PRIVATE/f'ipa-{run}-poll-private.json').write_bytes(q.stdout)
if report['state']['terminal'] and not report['matching_worker_live'] and not report['matching_child_live'] and 'summary' in report:
 (HERE/'ipa-capture-validation.json').write_text(json.dumps(report['summary'],indent=2)+'\n')
 (HERE/f'ipa-capture-{run}-validation.json').write_text(json.dumps(report['summary'],indent=2)+'\n')
summary=report.get('summary',{})
print(json.dumps(dict(state=report['state'],matching_worker_live=report['matching_worker_live'],matching_child_live=report['matching_child_live'],failure=report.get('failure'),
 summary={k:v for k,v in summary.items() if k not in ['before','after','exact_sof_pairs']},exact_sof_pairs=len(summary.get('exact_sof_pairs',[]))),indent=2))
