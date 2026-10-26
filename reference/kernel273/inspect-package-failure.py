from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
out=Path('/var/lib/samurai/k273-main-transaction')
def records(p):
 d={}
 for b in Path(p).read_bytes().split(b'\n\n'):
  if b.strip():d[next(l[2:].decode() for l in b.splitlines() if l.startswith(b'P:'))]=b
 return d
before=records(out/'backup/lib/apk/db/installed');after=records('/lib/apk/db/installed')
state=json.loads((out/'packages-state-private.json').read_text())
new=json.loads((out/'new-manifest-private.json').read_text());selected={x['name'] for x in new['packages']}
changed=[n for n in set(before)&set(after) if before[n]!=after[n]]
payload_errors=[]
for pkg in new['packages']:
 for name,item in pkg['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':valid=p.is_symlink() and os.readlink(p)==item['target']
  else:valid=p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'] and (p.stat().st_mode&0o777)==item['mode']
  if not valid:payload_errors.append(name)
report=dict(state=state,worker_present=Path('/proc',str(state['pid'])).exists(),
 failure=(out/'packages-failure-private.txt').read_text(),changed_records=sorted(changed),
 unexpected_changed_records=sorted(set(changed)-selected),added=sorted(set(after)-set(before)),removed=sorted(set(before)-set(after)),
 before_count=len(before),after_count=len(after),payload_errors=payload_errors,
 native_install=(out/'native-install-private.log').read_text() if (out/'native-install-private.log').exists() else None,
 downgrade_log=(out/'native-rollback-simulate-private.log').read_text() if (out/'native-rollback-simulate-private.log').exists() else None,
 user_processes=subprocess.run(['pgrep','-u','10000'],capture_output=True).stdout.decode())
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'package-failure-inspection-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);print(json.dumps(d,indent=2))
