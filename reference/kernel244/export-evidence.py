"""Archive both boots' stage-244 evidence with member hashes, privately."""
from pathlib import Path
import hashlib,importlib.util,io,json,tarfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel244');spec=importlib.util.spec_from_file_location('host',R/'host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import hashlib,json,tarfile
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes()
state=json.loads((r/'k244-nextboot/capture/state-private.json').read_text());assert state['terminal'] and state['exit_code']==0
names=['k244-power-diag','k244-online-version','k244-reconnect','k244-quiesce','k244-tools','k244-nextboot','k244-runtime'];files=[p for name in names for p in (r/name).rglob('*') if p.is_file() and not p.is_symlink() and p.suffix not in ['.gz','.pyc']]
assert len(files)<250 and all(p.stat().st_size<8*1024*1024 for p in files) and sum(p.stat().st_size for p in files)<24*1024*1024
target=r/'k244-evidence-private.tar.gz';assert not target.exists();manifest={str(p.relative_to(r)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files}
with tarfile.open(target,'w:gz') as archive:
 for p in files:archive.add(p,arcname=str(p.relative_to(r)),recursive=False)
b=target.read_bytes();print(json.dumps(dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),members=manifest)))
'''
x=host.ssh('python3 -',input=code.encode(),timeout=20);meta=json.loads(x.stdout);(P/'archive-meta-private.json').write_bytes(x.stdout);data=bytearray()
for start in range(0,meta['bytes'],32*1024):
 count=min(32*1024,meta['bytes']-start);s="from pathlib import Path;import sys;f=Path('/var/lib/samurai/k244-evidence-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()"%(start,count)
 b=host.ssh('python3 -',input=s.encode(),timeout=15).stdout;assert len(b)==count;data.extend(b)
assert hashlib.sha256(data).hexdigest()==meta['sha256'];(P/'evidence-private.tar.gz').write_bytes(data);dest=P/'evidence';assert not dest.exists();dest.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
 members=archive.getmembers();assert {m.name for m in members}==set(meta['members'])
 for m in members:
  assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
  b=archive.extractfile(m).read();v=meta['members'][m.name];assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'];p=dest/m.name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_bytes(b)
report=dict(stage=244,members=len(members),all_members_verified=True,raw_diag_nmea_and_boot_ids_private=True);(R/'evidence-export-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
