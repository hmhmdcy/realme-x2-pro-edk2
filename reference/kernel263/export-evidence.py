"""Archive native experiments privately and verify every exported file."""
from pathlib import Path
import hashlib,json,tarfile
import host
code=r'''
from pathlib import Path
import hashlib,json,os,tarfile
os.umask(0o077);r=Path('/var/lib/samurai');items=sorted(p for p in r.glob('k263-*') if p.is_dir())
out=r/'k263-export';assert not out.exists();out.mkdir(mode=0o700)
manifest={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for directory in items for p in directory.rglob('*') if p.is_file() and not p.is_symlink()}
archive=out/'native-private.tar.gz'
with tarfile.open(archive,'w:gz') as a:
 for p in items:a.add(p,arcname=p.name)
result=dict(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=manifest)
(out/'manifest-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=40);(host.PRIVATE/'native-manifest-private.json').write_bytes(r.stdout);d=json.loads(r.stdout)
target=host.PRIVATE/'native-evidence-private.tar.gz';assert not target.exists();chunk=1048576
with target.open('xb') as f:
 for offset in range(0,d['bytes'],chunk):
  q=host.transport.ssh("python3 -c \"import sys;f=open('/var/lib/samurai/k263-export/native-private.tar.gz','rb');f.seek(int(sys.argv[1]));sys.stdout.buffer.write(f.read(1048576))\" "+str(offset),timeout=25)
  assert len(q.stdout)==min(chunk,d['bytes']-offset);f.write(q.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==d['sha256']
with tarfile.open(target,'r:gz') as a:
 for name,digest in d['files'].items():assert hashlib.sha256(a.extractfile(name).read()).hexdigest()==digest,name
report=dict(stage=263,private_native_evidence_exported=True,files_verified=len(d['files']),archive_bytes=d['bytes'],archive_sha256=d['sha256'],archive_and_all_member_sha256_verified=True)
(Path(__file__).parent/'evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
