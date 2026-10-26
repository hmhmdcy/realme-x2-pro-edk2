"""Archive current native evidence privately, including the actual GUI photograph."""
from pathlib import Path
import hashlib,json,tarfile
import host
R=Path(__file__).parent;assert json.loads((R/'final-health-validation.json').read_text())['common_fix_deployed']
code=r'''
from pathlib import Path
import hashlib,json,os,tarfile
os.umask(0o077);r=Path('/var/lib/samurai');items=sorted(p for p in r.glob('k264-*') if p.is_dir());current=r/'k264-services-current-private.json';assert current.is_file()
out=r/'k264-export';assert not out.exists();out.mkdir()
manifest={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for directory in items for p in directory.rglob('*') if p.is_file() and not p.is_symlink()}
manifest[current.name]=hashlib.sha256(current.read_bytes()).hexdigest()
photos=json.loads((r/'k264-snapshot-gui/gui-control-summary-private.json').read_text())['new_jpegs'];assert len(photos)==1
photo=Path(photos[0]['path']);assert hashlib.sha256(photo.read_bytes()).hexdigest()==photos[0]['sha256'];manifest['scene-private/snapshot-gui.jpeg']=photos[0]['sha256']
archive=out/'native-private.tar.gz'
with tarfile.open(archive,'w:gz') as a:
 for p in items:a.add(p,arcname=p.name)
 a.add(current,arcname=current.name);a.add(photo,arcname='scene-private/snapshot-gui.jpeg')
result=dict(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=manifest)
(out/'manifest-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=50);(host.PRIVATE/'native-manifest-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
target=host.PRIVATE/'native-evidence-private.tar.gz';assert not target.exists();chunk=1048576
with target.open('xb') as f:
 for offset in range(0,d['bytes'],chunk):
  q=host.ssh("python3 -c \"import sys;f=open('/var/lib/samurai/k264-export/native-private.tar.gz','rb');f.seek(int(sys.argv[1]));sys.stdout.buffer.write(f.read(1048576))\" "+str(offset),timeout=25)
  assert len(q.stdout)==min(chunk,d['bytes']-offset);f.write(q.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==d['sha256']
with tarfile.open(target,'r:gz') as a:
 for name,digest in d['files'].items():assert hashlib.sha256(a.extractfile(name).read()).hexdigest()==digest,name
report=dict(stage=264,private_native_evidence_exported=True,files_verified=len(d['files']),archive_bytes=d['bytes'],archive_sha256=d['sha256'],archive_and_all_member_sha256_verified=True,private_gui_photo_included=True)
(R/'evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
