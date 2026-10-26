"""Preserve the tested299 source and entrypoints before the next IPA candidate."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
old=json.loads((ROOT/'archive/camera-before299-2026-10-19/manifest.json').read_text())
dest=ROOT/'archive/camera-before300-2026-10-19';assert not dest.exists();dest.mkdir()
rows=[]
for row in old['files']:
 p=ROOT/row['path'];q=dest/row['path'];q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 assert q.read_bytes()==p.read_bytes();rows.append(dict(path=row['path'],bytes=q.stat().st_size,sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
(dest/'manifest.json').write_text(json.dumps(dict(stage=300,prior_documented_stage=299,files=rows),indent=2)+'\n')
source=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
build=json.loads((ROOT/'reference/kernel299/inline-build-validation.json').read_text())
assert build['build_exit']==0 and hashlib.sha256((source/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_bytes()).hexdigest()==build['source_sha256']['camss_vfe.cpp']
archive=host.PRIVATE/'tested299-source-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as t:
 for p in sorted(source.rglob('*')):
  rel=p.relative_to(source)
  if rel.parts[0]=='output' or p.is_dir():continue
  t.add(p,arcname=str(rel),recursive=False)
report=dict(stage=300,actual_kernel_build=298,prior_manual_candidate_stage=299,source_archive_bytes=archive.stat().st_size,
 source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),previous_bundle_preserved=True,nine_entrypoints_archived=True,no_phone_operation=True)
(HERE/'baseline-preservation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
