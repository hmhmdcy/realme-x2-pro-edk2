"""Preserve the nine #297 entrypoints before a later #298 promotion."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
old=json.loads((ROOT/'archive/camera-before297-2026-10-19/manifest.json').read_text())
dest=ROOT/'archive/camera-before298-2026-10-19';assert not dest.exists();dest.mkdir()
rows=[]
for row in old['files']:
 p=ROOT/row['path'];q=dest/row['path'];q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 b=q.read_bytes();assert b==p.read_bytes();rows.append(dict(path=row['path'],bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
(dest/'manifest.json').write_text(json.dumps(dict(stage=298,prior_documented_stage=297,files=rows),indent=2)+'\n')
print('Nine original #297 entrypoints archived and byte-verified.')
