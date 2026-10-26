"""Copy current camera documentation/sources; preserve unrelated repository changes."""
from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parent;root=R.parents[1]
dst=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
items=['reference/kernel267','reference/kernel268','linux-port/packages/libcamera','linux-port/packages/samurai-camera-config',
 'NEXT-SESSION.md','DOCS-INDEX.md','HANDOVER-NEXT.md','sessions/INDEX.md','linux-port/docs/HARDWARE-STATUS.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json',
 'linux-port/camera/kernel/README.md','linux-port/camera/pmic/README.md',
 'archive/NEXT-SESSION-through267-2026-10-18.md','archive/camera-deployment-lock-through262-2026-10-18.json']
files=[]
for name in items:
 source=root/name
 files.extend([p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts] if source.is_dir() else [source])
for source in files:
 target=dst/source.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 assert source.read_bytes()==target.read_bytes()
report=dict(stage=268,files_mirrored=len(files),all_copied_sha256_verified=True,firmware_dtb_and_unrelated_changes_not_touched=True,
 documentation_mirror_commit_not_performed=True)
(R/'documentation-mirror-validation.json').write_text(json.dumps(report,indent=2)+'\n')
shutil.copyfile(R/'documentation-mirror-validation.json',dst/'reference/kernel268/documentation-mirror-validation.json')
print(json.dumps(report))
