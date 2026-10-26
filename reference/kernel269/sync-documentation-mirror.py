"""Mirror only reviewed closeout files and preserve the firmware and other work."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;root=R.parents[1]
dst=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
items=json.loads((R/'documentation-update-validation.json').read_text())['updated_documents']+[
 'reference/kernel269','linux-port/packages/samurai-platform','linux-port/packages/samurai-desktop',
 'archive/NEXT-SESSION-through268-2026-10-18.md','archive/camera-deployment-lock-through268-2026-10-18.json']
G=['git','-c','safe.directory=/home/cy122/edk2-samurai/repo','-C',str(dst)]
head=subprocess.check_output(G+['rev-parse','HEAD'],text=True).strip()
protected={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [dst/'FdtBlob_compat/samurai.dtb',dst/'FdtBlob/samurai.dtb'] if p.is_file()}
files=[]
for name in items:
 source=root/name
 files.extend([p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts] if source.is_dir() else [source])
files=sorted(set(files))
for source in files:
 target=dst/source.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
assert subprocess.check_output(G+['rev-parse','HEAD'],text=True).strip()==head
assert all(hashlib.sha256(p.read_bytes()).hexdigest()==digest for p,digest in protected.items())
report=dict(stage=269,files_mirrored=len(files),all_copied_sha256_verified=True,
 firmware_dtb_and_unrelated_changes_not_touched=True,documentation_mirror_commit_not_performed=True,
 previous_checkpoint_and_deployment_lock_archives_included=True)
(R/'documentation-mirror-validation.json').write_text(json.dumps(report,indent=2)+'\n')
shutil.copyfile(R/'documentation-mirror-validation.json',dst/'reference/kernel269/documentation-mirror-validation.json')
print(json.dumps(report,indent=2))
