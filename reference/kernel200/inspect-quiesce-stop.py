from pathlib import Path
import json,subprocess,os

root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-baseline/boot-id-private.txt').read_bytes()
r=dict(amps=(root/'k200-quiesce/amps-before-stop.txt').read_text(),mm_expected=str(Path('/usr/sbin/ModemManager').resolve()),mm_processes=[])
for p in Path('/proc').iterdir():
 if p.name.isdigit():
  try:
   if (p/'comm').read_text().strip()=='ModemManager':r['mm_processes'].append(dict(pid=int(p.name),exe=os.readlink(p/'exe')))
  except OSError:pass
print(json.dumps(r))
