"""Verify and label the preserved actual-k294 R2 build, and export the reviewed candidate."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel295');TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
old=json.loads((ROOT.parent/'kernel294/boot-candidate-build-validation.json').read_text())
a=P/'completed-boot294-r1';b=P/'completed-boot294-r2';assert a.is_dir() and not b.exists()
assert a.resolve().parent==P.resolve() and b.resolve().parent==P.resolve()
for name,row in old['artifacts'].items():assert hashlib.sha256((a/Path(name).name).read_bytes()).hexdigest()==row['sha256']
a.rename(b)
p=ROOT/'build-boot-kernel.py';p.write_text(p.read_text().replace('completed-boot294-r1','completed-boot294-r2'))
p=ROOT/'prepare-build-workflows.py';p.write_text(p.read_text().replace(".replace('completed-boot295-r1','completed-boot294-r2')",".replace('completed-boot294-r1','completed-boot294-r2')"))
git=lambda *x:subprocess.check_output(['git','-C',str(TREE),*x])
assert not git('status','--porcelain').strip()
(ROOT/'camss-vfe-175-stats.c').write_bytes((TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-stats.c').read_bytes())
patch=git('diff','1aa1955077c977b611c722eca0bc467c3bf052ed..HEAD','--','drivers/media/platform/qcom/camss')
(ROOT/'combined-stats-from293.patch').write_bytes(patch)
report=dict(stage=295,preserved_actual294_r2_six_artifacts_verified=True,preserved_directory='private kernel295/completed-boot294-r2',misleading_r1_directory_label_corrected=True,
 combined_patch_sha256=hashlib.sha256(patch).hexdigest(),source_clean=True)
(ROOT/'preserved-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
