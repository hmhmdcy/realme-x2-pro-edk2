"""Identify selected init entrypoints and local script dependencies, without secrets."""
from pathlib import Path
import json,re
import host

ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json
allowed=['rdinit','init','rootfstype','rootflags','rw','ro']
args=[]
for arg in Path('/proc/cmdline').read_text().split():
 if arg.split('=',1)[0] in allowed:args.append(arg)
print(json.dumps(args))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=12)
args=json.loads(q.stdout)
assert not any('PRIVATE KEY' in v for v in args)
init=Path('/home/cy122/pmos-samurai-kernel136/initramfs')
scripts=[]
for p in init.rglob('*'):
 if p.is_file() and not p.is_symlink() and p.stat().st_size<256*1024:
  b=p.read_bytes()
  if b.startswith(b'#!'):
   text=b.decode(errors='replace')
   scripts.append(dict(path=str(p.relative_to(init)),root_switch='switch_root' in text,
                       module_load='insmod' in text or 'modprobe' in text,
                       samurai_modules_path='/lib/modules/samurai/' in text))
report=dict(stage=288,kernel_init_arguments=args,initramfs_scripts=scripts,read_only=True)
(ROOT/'boot-entry-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
