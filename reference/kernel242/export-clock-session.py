from pathlib import Path
import hashlib,importlib.util,io,json,tarfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel242')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import hashlib,json,tarfile
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k242-clock-session';state=json.loads((p/'state-private.json').read_text());assert state['terminal'] and state['trace_instance_removed']
target=p/'evidence-private.tar.gz';assert not target.exists()
files=[x for x in p.iterdir() if x.is_file()]
manifest={x.name:dict(bytes=x.stat().st_size,sha256=hashlib.sha256(x.read_bytes()).hexdigest()) for x in files}
with tarfile.open(target,'w:gz') as archive:
 for x in files:archive.add(x,arcname=x.name,recursive=False)
data=target.read_bytes();print(json.dumps(dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),members=manifest)))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=20)
meta=json.loads(result.stdout);(P/'clock-archive-private.json').write_bytes(result.stdout)
data=bytearray()
for start in range(0,meta['bytes'],32*1024):
 count=min(32*1024,meta['bytes']-start)
 code="from pathlib import Path;import sys;f=Path('/var/lib/samurai/k242-clock-session/evidence-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()"%(start,count)
 chunk=host.ssh('python3 -',input=code.encode(),timeout=15).stdout;assert len(chunk)==count;data.extend(chunk)
assert hashlib.sha256(data).hexdigest()==meta['sha256']
(P/'clock-evidence-private.tar.gz').write_bytes(data)
dest=P/'clock-evidence';assert not dest.exists();dest.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
 members=archive.getmembers();assert {m.name for m in members}==set(meta['members'])
 for m in members:
  assert m.isfile() and Path(m.name).name==m.name
  payload=archive.extractfile(m).read();item=meta['members'][m.name]
  assert len(payload)==item['bytes'] and hashlib.sha256(payload).hexdigest()==item['sha256']
  (dest/m.name).write_bytes(payload)
report=dict(stage=242,members=len(members),all_members_verified=True,raw_packets_and_hardware_snapshots_private=True)
(R/'clock-export-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
