"""Export the new/changed private native files since the first verified archive."""
from pathlib import Path
import hashlib,json,shlex,tarfile
import host
P=host.PRIVATE;previous=json.loads((P/'native-manifest-private.json').read_text())['files']
code=r'''
from pathlib import Path
import hashlib,json,os,sys,tarfile
os.umask(0o077);r=Path('/var/lib/samurai');previous=json.loads(sys.argv[1])
items=sorted(p for p in r.glob('k262-*') if p.is_dir() and not p.name.startswith('k262-export'))
changed={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for d in items for p in d.rglob('*') if p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()!=previous.get(str(p.relative_to(r)))}
out=r/'k262-export-addendum';assert not out.exists();out.mkdir(mode=0o700);archive=out/'addendum-private.tar.gz'
with tarfile.open(archive,'w:gz') as a:
 for name in changed:a.add(r/name,arcname=name)
result=dict(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=changed)
(out/'manifest-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
'''
code=code.replace('previous=json.loads(sys.argv[1])','previous='+repr(previous))
r=host.ssh('python3 -',input=code.encode(),timeout=30)
(P/'addendum-manifest-private.json').write_bytes(r.stdout);d=json.loads(r.stdout)
target=P/'native-addendum-private.tar.gz';assert not target.exists()
with target.open('xb') as f:
 for offset in range(0,d['bytes'],65536):
  command="python3 -c \"import sys;f=open('/var/lib/samurai/k262-export-addendum/addendum-private.tar.gz','rb');f.seek(int(sys.argv[1]));sys.stdout.buffer.write(f.read(65536))\" "+str(offset)
  q=host.transport.ssh(command,timeout=20);assert len(q.stdout)==min(65536,d['bytes']-offset);f.write(q.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==d['sha256']
with tarfile.open(target,'r:gz') as a:
 for name,digest in d['files'].items():assert hashlib.sha256(a.extractfile(name).read()).hexdigest()==digest,name
report=dict(stage=262,changed_or_new_files_verified=len(d['files']),archive_bytes=d['bytes'],archive_sha256=d['sha256'],archive_and_member_sha256_verified=True,first274_file_archive_preserved=True)
(Path(__file__).parent/'evidence-addendum-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
