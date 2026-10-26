"""Snapshot private evidence once; transfer resumably and verify every regular member."""
from pathlib import Path
import hashlib,json,shlex,tarfile
import host
R=Path(__file__).parent;assert json.loads((R/'final-health-validation.json').read_text())['common_fix_deployed']
code=r'''
from pathlib import Path
import hashlib,io,json,os,stat,tarfile
os.umask(0o077);r=Path('/var/lib/samurai');out=r/'k265-export'
if out.exists():
 saved=json.loads((out/'manifest-private.json').read_text());assert hashlib.sha256((out/'native-private.tar.gz').read_bytes()).hexdigest()==saved['sha256'];print(json.dumps(saved));raise SystemExit(0)
items=sorted(p for p in r.glob('k265-*') if p.is_dir() and not p.is_symlink());current=r/'k265-services-current-private.json';assert current.is_file();out.mkdir()
paths=sorted({p for directory in items for p in [directory,*directory.rglob('*')]},key=lambda p:str(p));paths.append(current)
photos=json.loads((r/'k265-snapshot-gui/gui-control-summary-private.json').read_text())['new_jpegs'];manifest={};archive=out/'native-private.tar.gz'
with tarfile.open(archive,'w:gz') as a:
 for p in paths:
  name=str(p.relative_to(r));info=a.gettarinfo(str(p),arcname=name)
  if info.isreg():
   data=p.read_bytes();info.size=len(data);a.addfile(info,io.BytesIO(data));manifest[name]=hashlib.sha256(data).hexdigest()
  elif info.isdir() or info.issym() or info.islnk():a.addfile(info)
 for i,photo in enumerate(photos):
  p=Path(photo['path']);data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==photo['sha256'];name='scene-private/snapshot-gui-'+str(i)+'.jpeg';info=a.gettarinfo(str(p),arcname=name);info.size=len(data);a.addfile(info,io.BytesIO(data));manifest[name]=photo['sha256']
result=dict(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=manifest,gui_photos=len(photos),snapshot_reads_added_exactly_to_archive=True)
(out/'manifest-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=60);(host.PRIVATE/'native-manifest-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
target=host.PRIVATE/'native-evidence-private.tar.gz';chunk=1024*1024
def read(offset,size):
 query="import sys;f=open('/var/lib/samurai/k265-export/native-private.tar.gz','rb');f.seek(int(sys.argv[1]));sys.stdout.buffer.write(f.read(int(sys.argv[2])))"
 q=host.ssh('python3 -c '+shlex.quote(query)+' '+str(offset)+' '+str(size),timeout=30);assert len(q.stdout)==min(size,d['bytes']-offset);return q.stdout
existing=target.stat().st_size if target.exists() else 0;assert existing<=d['bytes']
if existing:
 with target.open('rb') as f:
  for offset in range(0,existing,chunk):
   size=min(chunk,existing-offset);assert f.read(size)==read(offset,size)
with target.open('ab') as f:
 for offset in range(existing,d['bytes'],chunk):f.write(read(offset,chunk))
assert target.stat().st_size==d['bytes'] and hashlib.sha256(target.read_bytes()).hexdigest()==d['sha256']
with tarfile.open(target,'r:gz') as a:
 for name,digest in d['files'].items():assert hashlib.sha256(a.extractfile(name).read()).hexdigest()==digest,name
report=dict(stage=265,private_native_evidence_exported=True,files_verified=len(d['files']),archive_bytes=d['bytes'],archive_sha256=d['sha256'],archive_and_all_member_sha256_verified=True,private_gui_photos_included=d['gui_photos'],consistent_file_snapshot_verified=d['snapshot_reads_added_exactly_to_archive'],verified_existing_prefix_bytes=existing)
(R/'evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

