from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
out=Path('/var/lib/samurai/k233-pmic-cycles');s=json.loads((out/'state-private.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(out/'boot-id-private.txt').read_bytes()
if s['state']=='running':
 p=Path('/proc')/str(s['pid']);assert p.exists() and (p/'stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
 print(json.dumps(dict(state='running',worker_live=True,phase=s['phase'])))
else:print(json.dumps(dict(state='terminal',exit_code=s['exit_code'],summary=json.loads((out/'summary.json').read_text()) if s['exit_code']==0 else None)))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'pmic-cycles-poll-host-private.json').write_bytes(r.stdout)
report=json.loads(r.stdout)
if report['state']=='terminal':
 assert report['exit_code']==0,'Inspect terminal native cycle evidence; do not repeat'
 (Path(__file__).resolve().parent/'pmic-cycles-validation.json').write_text(json.dumps(report['summary'],indent=2)+'\n')
 state=json.loads((host.PRIVATE/'current-work-private.json').read_text());state.update(state='native warm Q and cold provider managed-link cycles passed; front/WP restored',active_native_context=None,active_native_session=None,next='Front RAM-only RAW/RGB regression then final health and source integration');(host.PRIVATE/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(report))
