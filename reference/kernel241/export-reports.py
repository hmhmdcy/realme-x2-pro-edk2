from pathlib import Path
import hashlib,importlib.util,io,json,sys,tarfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel241')
spec=importlib.util.spec_from_file_location('host241',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
kind=sys.argv[1];assert kind in ['differential','ordered','afw','combined']
code=r'''
from pathlib import Path
import hashlib,json,tarfile
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/CONTEXT;assert json.loads((p/'state-private.json').read_text())['terminal']
target=p/'evidence-private.tar.gz'
files=[x for x in p.iterdir() if x.is_file() and x.name!='evidence-private.tar.gz']
manifest={x.name:dict(bytes=x.stat().st_size,sha256=hashlib.sha256(x.read_bytes()).hexdigest()) for x in files}
assert not target.exists()
with tarfile.open(target,'w:gz') as archive:
 for x in files:archive.add(x,arcname=x.name,recursive=False)
data=target.read_bytes();print(json.dumps(dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),members=manifest)))
'''.replace('CONTEXT',repr('k241-loc-'+kind))
result=host.ssh('python3 -',input=code.encode(),timeout=20)
meta=json.loads(result.stdout);(P/(kind+'-archive-private.json')).write_bytes(result.stdout)
data=bytearray()
for start in range(0,meta['bytes'],32*1024):
    count=min(32*1024,meta['bytes']-start)
    code="from pathlib import Path;import sys;f=Path(%r).open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()"%('/var/lib/samurai/k241-loc-'+kind+'/evidence-private.tar.gz',start,count)
    chunk=host.ssh('python3 -',input=code.encode(),timeout=15).stdout;assert len(chunk)==count;data.extend(chunk)
assert hashlib.sha256(data).hexdigest()==meta['sha256']
(P/(kind+'-evidence-private.tar.gz')).write_bytes(data)
dest=P/'evidence'/kind;assert not dest.exists();dest.mkdir(mode=0o700,parents=True)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
    members=archive.getmembers();assert {m.name for m in members}==set(meta['members'])
    for m in members:
        assert m.isfile() and Path(m.name).name==m.name
        payload=archive.extractfile(m).read();item=meta['members'][m.name]
        assert len(payload)==item['bytes'] and hashlib.sha256(payload).hexdigest()==item['sha256']
        (dest/m.name).write_bytes(payload)
report=dict(stage=241,case=kind,members=len(members),all_members_verified=True,raw_packets_private=True)
(R/(kind+'-export-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
