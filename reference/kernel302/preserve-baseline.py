"""Archive current301 entrypoints; verify the already preserved tested300 source."""
from pathlib import Path
import hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=json.loads((ROOT/'reference/kernel301/checkpoint-validation.json').read_text())
dest=ROOT/'archive/camera-before302-2026-10-19';assert not dest.exists();dest.mkdir()
rows=[]
for name,info in previous['files'].items():
 p=ROOT/name;assert sha(p)==info['sha256'];q=dest/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);assert q.read_bytes()==p.read_bytes()
 rows.append(dict(path=name,bytes=q.stat().st_size,sha256=sha(q)))
(dest/'manifest.json').write_text(json.dumps(dict(stage=302,prior_documented_stage=301,files=rows),indent=2)+'\n')
tree=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline');build=json.loads((ROOT/'reference/kernel300/build-validation.json').read_text())
for name,digest in build['source_sha256'].items():assert sha(tree/name)==digest
archive=host.PRIVATE.parent/'kernel301/tested300-source-private.tar.gz';old=json.loads((ROOT/'reference/kernel301/baseline-preservation-validation.json').read_text())
assert sha(archive)==old['source_archive_sha256']
bundle=host.PRIVATE.parent/'kernel300/ipa-bundle-r4-private.tar.gz';assert sha(bundle)=='84fcad6db75979b2f88f0350118aec83025f8536d2206aadd2e77efbdeec5206'
out=dict(stage=302,actual_kernel_build=298,nine_current301_entrypoints_archived=True,tested300_candidate_preserved=True,tested300_source_archive_sha256=sha(archive),no_phone_operation=True)
(HERE/'baseline-preservation-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
