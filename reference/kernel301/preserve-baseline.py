"""Preserve the tested300 candidate and current entrypoints before further control work."""
from pathlib import Path
import hashlib,json,shutil,tarfile
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
old=json.loads((ROOT/'archive/camera-before300-2026-10-19/manifest.json').read_text())
dest=ROOT/'archive/camera-before301-2026-10-19';assert not dest.exists();dest.mkdir()
rows=[]
for row in old['files']:
 p=ROOT/row['path'];q=dest/row['path'];q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 assert q.read_bytes()==p.read_bytes();rows.append(dict(path=row['path'],bytes=q.stat().st_size,sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
(dest/'manifest.json').write_text(json.dumps(dict(stage=301,prior_documented_stage=300,files=rows),indent=2)+'\n')
source=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
build=json.loads((ROOT/'reference/kernel300/build-validation.json').read_text());assert build['build_exit']==0
for name,sha in build['source_sha256'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==sha
archive=host.PRIVATE/'tested300-source-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for p in sorted(source.rglob('*')):
  rel=p.relative_to(source)
  if rel.parts[0]=='output' or p.is_dir():continue
  tar.add(p,arcname=str(rel),recursive=False)
bundle=host.PRIVATE.parent/'kernel300/ipa-bundle-r4-private.tar.gz'
assert hashlib.sha256(bundle.read_bytes()).hexdigest()=='84fcad6db75979b2f88f0350118aec83025f8536d2206aadd2e77efbdeec5206'
out=dict(stage=301,actual_kernel_build=298,nine_current300_entrypoints_archived=True,tested300_candidate_preserved=True,
 source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),no_phone_operation=True)
(HERE/'baseline-preservation-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
