"""Export bounded chunks of the private native evidence, including photographs."""
from pathlib import Path
import hashlib,json,tarfile
import host
code=r'''
from pathlib import Path
import hashlib,json,os,tarfile
os.umask(0o077);r=Path('/var/lib/samurai')
items=sorted(p for p in r.glob('k262-*') if p.is_dir())
out=r/'k262-export';assert not out.exists();out.mkdir(mode=0o700)
manifest={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for directory in items for p in directory.rglob('*') if p.is_file() and not p.is_symlink()}
archive=out/'native-private.tar.gz'
with tarfile.open(archive,'w:gz') as a:
 for p in items:a.add(p,arcname=p.name)
result=dict(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=manifest)
(out/'manifest-private.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'native-manifest-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);target=host.PRIVATE/'native-evidence-private.tar.gz';assert not target.exists()
with target.open('xb') as f:
 for offset in range(0,d['bytes'],65536):
  command="python3 -c \"import sys;f=open('/var/lib/samurai/k262-export/native-private.tar.gz','rb');f.seek(int(sys.argv[1]));sys.stdout.buffer.write(f.read(65536))\" "+str(offset)
  q=host.transport.ssh(command,timeout=20)
  assert len(q.stdout)==min(65536,d['bytes']-offset)
  f.write(q.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==d['sha256']
with tarfile.open(target,'r:gz') as a:
 for name,digest in d['files'].items():assert hashlib.sha256(a.extractfile(name).read()).hexdigest()==digest,name
report=dict(stage=262,private_native_evidence_exported=True,archive_sha256=d['sha256'],archive_bytes=d['bytes'],files_verified=len(d['files']),archive_and_all_member_sha256_verified=True,photographs_kept_private=True)
(Path(__file__).parent/'evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
