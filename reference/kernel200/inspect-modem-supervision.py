from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-baseline/boot-id-private.txt').read_bytes()
services={p.name:p.read_text() for p in Path('/etc/init.d').iterdir() if p.is_file() and 'ModemManager' in p.read_text(errors='replace')}
parents=[]
for p in Path('/proc').iterdir():
 if p.name.isdigit():
  try:
   if (p/'comm').read_text().strip()=='ModemManager':
    parent=next(l.split()[1] for l in (p/'status').read_text().splitlines() if l.startswith('PPid:'));parents.append(dict(parent=Path('/proc/'+parent+'/comm').read_text().strip()))
  except OSError:pass
print(json.dumps(dict(service_sources=services,parent_names=parents)))
