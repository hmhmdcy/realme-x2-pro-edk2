"""Immutable prefix snapshot while the first-startup diagnostic sockets stay open."""
from pathlib import Path
import hashlib,importlib.util,io,json,sys,tarfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel246');label=sys.argv[1];assert label in ['baseline-off','comparison-online'];spec=importlib.util.spec_from_file_location('host',R/'host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import hashlib,io,json,os,tarfile
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k246-runtime/boot-id-private.txt').read_bytes();o=r/'k246-nextboot/capture';s=json.loads((o/'state-private.json').read_text());assert LABEL in s.get('phases_completed',[]) and s['state']=='ready' and not s['terminal'];p=Path('/proc',str(s['pid']));assert p.joinpath('stat').read_text().split()[21]==s['start_ticks']
target=r/('k246-'+LABEL+'-snapshot-private.tar.gz');assert not target.exists();data={}
for p in o.iterdir():
 if p.is_file() and (p.name in ['diag-events-private.jsonl','state-private.json','boot-id-private.txt'] or p.name.startswith(LABEL+'-')):
  b=p.read_bytes()
  if p.name=='diag-events-private.jsonl':b=b[:b.rfind(b'\n')+1]
  assert len(b)<16*1024*1024;data[p.name]=b
assert sum(len(b) for b in data.values())<24*1024*1024
manifest={name:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for name,b in data.items()}
with tarfile.open(target,'w:gz') as archive:
 for name,b in data.items():
  info=tarfile.TarInfo(name);info.size=len(b);info.mode=0o600;archive.addfile(info,io.BytesIO(b))
b=target.read_bytes();print(json.dumps(dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),members=manifest)))
'''.replace('LABEL',repr(label))
x=host.ssh('python3 -',input=code.encode(),timeout=20);meta=json.loads(x.stdout);(P/(label+'-snapshot-meta-private.json')).write_bytes(x.stdout);data=bytearray()
for start in range(0,meta['bytes'],32768):
 count=min(32768,meta['bytes']-start);s="from pathlib import Path;import sys;f=Path('/var/lib/samurai/k246-%s-snapshot-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()"%(label,start,count);b=host.ssh('python3 -',input=s.encode(),timeout=15).stdout;assert len(b)==count;data.extend(b)
assert hashlib.sha256(data).hexdigest()==meta['sha256'];(P/(label+'-snapshot-private.tar.gz')).write_bytes(data);dest=P/(label+'-snapshot');assert not dest.exists();dest.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
 members=archive.getmembers();assert {m.name for m in members}==set(meta['members'])
 for m in members:
  assert m.isfile() and Path(m.name).name==m.name;b=archive.extractfile(m).read();v=meta['members'][m.name];assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'];(dest/m.name).write_bytes(b)
report=dict(stage=246,phase=label,members=len(members),all_members_verified=True,diag_sockets_remain_open=True,raw_private=True);(R/(label+'-snapshot-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
