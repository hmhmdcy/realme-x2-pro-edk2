from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
target=ROOT/'archive/camera-before292-2026-10-19';assert not target.exists();target.mkdir()
names=['NEXT-SESSION.md','DOCS-INDEX.md','sessions/INDEX.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','reference/kernel276/OEM-TUNING.md','linux-port/docs/HARDWARE-STATUS.md']
rows=[]
for name in names:
 src=ROOT/name;dst=target/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);b=src.read_bytes();assert b==dst.read_bytes();rows.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
(target/'manifest.json').write_text(json.dumps(dict(stage=292,prior_documented_stage=291,files=rows),indent=2)+'\n')
print('Preserved all nine prior entrypoints and deployment/source locks.')
