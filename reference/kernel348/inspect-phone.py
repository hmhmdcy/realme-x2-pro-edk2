import json,shlex
from pathlib import Path
import host
code='''
from pathlib import Path
import hashlib,json
services={}
for name in ['pipewire','wireplumber']:
 rows=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':rows.append(dict(pid=int(p.name),uid=p.stat().st_uid))
  except (FileNotFoundError,ProcessLookupError):pass
 services[name]=rows
print(json.dumps(dict(boot_guard_matches=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes(),
 module_note_sha256=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest(),
 services=services,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']})))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);d=json.loads(q.stdout)
(host.PRIVATE/'phone-preflight-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
assert d['boot_guard_matches'] and not d['taint']
