from pathlib import Path
import json,shlex,sys
import host
R=Path(__file__).parent;run=int(sys.argv[1]);assert run in range(1,10)
code=r'''
from pathlib import Path
import json,re,sys
run=int(sys.argv[1]);r=Path('/var/lib/samurai');p=r/('k265-camera-'+str(run));d=json.loads((p/'summary.json').read_text());assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
s=(p/'stderr-private.txt').read_text(errors='replace');lines=s.splitlines()
near=[l for l in lines if any(k in l for k in ['AssertionError','Traceback','was not recycled','start-capture','image-done','prepare-capture','set format','format changed','configure','reconfigure'])]
pts_targets=[str(x['before_pts']) for x in (d.get('probe_result') or {}).get('held_change_details',[])]
for target in pts_targets:
 for i,l in enumerate(lines):
  if target in l:near+=lines[max(0,i-3):i+4]
q=r/'k264-policy-refresh/wireplumber-private.log';wp=q.read_text(errors='replace')
result=dict(run=run,details=near[-70:],source_pts=[l for l in lines if ' pts ' in l and any(t in l for t in pts_targets)],error_count=s.count('was not recycled'),worker_stderr_tail=lines[-8:],policy_log_tail=wp.splitlines()[-50:])
print(json.dumps(result,indent=2))
'''
q=host.ssh('python3 - '+str(run),input=code.encode(),timeout=20);(host.PRIVATE/('capture-'+str(run)+'-analysis-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
