"""Read session bus service search configuration; do not reactivate the app."""
import json
import host
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
items=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip()!='dbus-daemon' or int((p/'status').read_text().split('Uid:',1)[1].split()[0])!=10000:continue
  env={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
  items.append(dict(pid=int(p.name),cmdline=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(),paths={k:env.get(k) for k in ['HOME','XDG_DATA_HOME','XDG_DATA_DIRS']}))
 except OSError:pass
configs={}
for name in ['/usr/share/dbus-1/session.conf','/etc/dbus-1/session.conf','/etc/dbus-1/session-local.conf']:
 p=Path(name)
 if p.is_file():configs[name]=[x.strip() for x in p.read_text().splitlines() if any(k in x for k in ['servicedir','includedir','include '])]
report=dict(daemon=items,config_service_directives=configs)
(r/'k240-snapshot-launcher-transaction/dbus-search-audit-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=15)
(host.PRIVATE/'session-dbus-search-private.json').write_bytes(p.stdout);print(p.stdout.decode())
