"""Inspect the first D-Bus verification failure without repeating activation."""
import json
import host
code=r'''
from pathlib import Path
import json,os
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k240-snapshot-dbus-activation-r2'
data={q.name:q.read_text(errors='replace')[-8000:] for q in p.iterdir() if q.is_file()}
apps=[]
for q in Path('/proc').glob('[0-9]*'):
 try:
  if (q/'comm').read_text().strip()=='snapshot':
   env={k.decode():v.decode() for x in (q/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
   apps.append(dict(pid=int(q.name),exe=os.readlink(q/'exe'),flags={k:env.get(k) for k in ['GSK_RENDERER','GDK_DISABLE']}))
 except OSError:pass
print(json.dumps(dict(receipts=data,existing_snapshot=apps)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=15)
(host.PRIVATE/'snapshot-dbus-first-failure-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
