"""Establish a new boot-specific baseline after the user reconnects USB."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
base=host.previous.previous.base
native=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k298+' and os.uname().version.startswith('#298 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
root=Path('/var/lib/samurai/k305-geometry-r2');assert not root.exists();root.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
(root/'boot-id-private.txt').write_bytes(boot)
services={}
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip();fields=(p/'stat').read_text().rsplit(')',1)[1].split()
  if name not in ['pipewire','wireplumber','phoc','phosh'] or fields[0]=='Z':continue
  uid=int((p/'status').read_text().split('Uid:',1)[1].split()[0]);assert uid==10000 and name not in services
  services[name]=dict(name=name,pid=int(p.name),start_ticks=fields[19],
   env=dict(row.decode().split('=',1) for row in (p/'environ').read_bytes().split(b'\0') if b'=' in row),
   cwd=os.readlink(p/'cwd'),argv=[s.decode() for s in (p/'cmdline').read_bytes().split(b'\0') if s])
 except (FileNotFoundError,ProcessLookupError):pass
assert set(services)=={'pipewire','wireplumber','phoc','phosh'}
devices=[p for p in Path('/sys/bus/i2c/drivers/s5k3m5').iterdir() if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
assert len(devices)==1
tree=Path('/usr/lib/modules')/os.uname().release
target=tree/'kernel/drivers/media/i2c/s5k3m5.ko'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(target)=='9844674d443583cb3f862eafbc1463c41e8818a37bba93a0da27de0801bf9cc8'
assert sha(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id'))=='569f07ba012a7a7a95832ae0ab3a59af2dfda8384973e629f0c9ab4d138a66d0'
inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')};assert len(inventory)==778
(root/'module-inventory-before-private.json').write_text(json.dumps(inventory,indent=2)+'\n')
backup=root/'backup';backup.mkdir(mode=0o700)
for p in [target,Path('/lib/apk/db/installed'),Path('/etc/apk/world')]:
 d=backup/str(p).lstrip('/');d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(p.read_bytes())
record=dict(services=services,device=devices[0].name,module_path=str(target),original_sha256=sha(target),
 loaded_note_sha256=sha(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id')))
(root/'preflight-private.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(stage=305,new_boot_baseline=True,old_298_boot_guard_matches=boot==Path('/var/lib/samurai/k298-work/boot-id-private.txt').read_bytes(),
 kernel_build=298,taint=0,original_module_verified=True,module_count=len(inventory),
 services=[{k:v[k] for k in ['name','pid','start_ticks']} for v in services.values()])))
'''
import subprocess
q=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@169.254.42.1','python3 -'],
 input=native.encode(),capture_output=True,timeout=30)
(host.PRIVATE/'current-boot-preflight-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Inspect preflight; do not blindly recreate root'
report=json.loads(q.stdout)
(HERE/'current-boot-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
