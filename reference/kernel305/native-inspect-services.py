"""Capture daemon state privately; return only identities and module fingerprints."""
from pathlib import Path
import hashlib,json,os,re
out=Path('/var/lib/samurai/k305-sensor-candidate')
out.mkdir(mode=0o700,exist_ok=True)
services={}
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip();fields=(p/'stat').read_text().rsplit(')',1)[1].split()
  uid=int((p/'status').read_text().split('Uid:',1)[1].split()[0])
  if name in ['pipewire','wireplumber','phoc','phosh'] and fields[0]!='Z' and uid==10000:
   assert name not in services
   env=dict(row.decode().split('=',1) for row in (p/'environ').read_bytes().split(b'\0') if b'=' in row)
   services[name]=dict(name=name,pid=int(p.name),start_ticks=fields[19],env=env,cwd=os.readlink(p/'cwd'),
                       argv=[row.decode() for row in (p/'cmdline').read_bytes().split(b'\0') if row])
 except (FileNotFoundError,ProcessLookupError):
  pass
assert set(services)=={'pipewire','wireplumber','phoc','phosh'}
drivers=[p for p in Path('/sys/bus/i2c/drivers/s5k3m5').iterdir()
         if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
assert len(drivers)==1
target=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/s5k3m5.ko'
record=dict(services=services,device=drivers[0].name,module_path=str(target),
 original_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
 loaded_note_sha256=hashlib.sha256(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id').read_bytes()).hexdigest())
dest=out/'preflight-private.json'
assert not dest.exists()
dest.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(stage=305,device=record['device'],original_sha256=record['original_sha256'],
 loaded_note_sha256=record['loaded_note_sha256'],
 services=[{k:item[k] for k in ['name','pid','start_ticks']} for item in services.values()])))
