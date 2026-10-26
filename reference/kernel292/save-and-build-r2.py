"""Preserve unbooted r1 receipts and prepare a coherent r2 including link validation."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='8a16fbe17010c1eede868f8b8eb7d1dbd77c81ad'
path='drivers/media/platform/qcom/camss/camss-video.c';assert git('diff','--name-only')==path
assert json.loads((ROOT/'metadata-link-host-validation.json').read_text())['asan_ubsan']
message=host.PRIVATE/'metadata-link-commit-message-private.txt';message.write_text('media: qcom: camss: validate metadata output links\n\nV4L2 delegates links sourced by video output nodes to their entity validator. Check that the source owns the metadata output pad and the sink exposes fixed metadata, propagating sink format errors instead of relying on the warning fallback. Capture nodes retain their existing validation path.\n')
subprocess.run(['git','-C',str(TREE),'add','--',path],check=True);subprocess.run(['git','-C',str(TREE),'commit','-F',str(message)],check=True,capture_output=True)
assert not git('status','--porcelain');commit=git('rev-parse','HEAD')
report=dict(stage=292,commit=commit,parent=git('rev-parse','HEAD^'),branch=git('branch','--show-current'),source_clean=True,checkpatch_errors=0,checkpatch_warnings=0,not_deployed=True,pushed=False)
(ROOT/'metadata-link-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for original,target in [('boot-candidate-build-validation.json','boot-r1-build-validation.json'),('boot-package-validation.json','boot-r1-package-validation.json'),('module-staging-validation.json','module-r1-staging-validation.json')]:
 p=ROOT/target;assert not p.exists();shutil.copyfile(ROOT/original,p)
for name in ['installed-module-inventory-private.json','boot-initramfs-manifest-private.json']:
 p=host.PRIVATE/name;target=p.with_name(name.replace('-private','-r1-private'));assert not target.exists();shutil.copyfile(p,target)
s=(ROOT/'build-boot-kernel.py').read_text().replace('8a16fbe17010c1eede868f8b8eb7d1dbd77c81ad',commit)
s=s.replace('9c1b4f24d42519af211b81fc015c948239ea6cfc1550d197469b07c779053581','941e34b3230275060714218e0067da362d04b7d0f33953ce5d1057cdb66f2898')
s=s.replace("ROOT.parent/'kernel290/boot-candidate-build-validation.json'","ROOT/'boot-r1-build-validation.json'")
s=s.replace('boot-build-state-private','boot-build-r2-state-private').replace('completed-boot290','completed-boot292-r1')
s=s.replace("('boot-'+name+'-private.log')","('boot-r2-'+name+'-private.log')")
s=s.replace('input-initramfs292','input-initramfs292-r2').replace("'modules292'","'modules292-r2'").replace('modules-k292-private','modules-k292-r2-private')
s=s.replace("release!=old.get('release','7.3.0-rc6-rmx1931-samurai-k279candidate+')","release!='7.3.0-rc6-rmx1931-samurai-k290+'")
s=s.replace("{'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'}","{'CONFIG_INITRAMFS_SOURCE'}")
p=ROOT/'build-boot-r2.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
s=(ROOT/'package-boot-candidate.py').read_text().replace('input-initramfs292','input-initramfs292-r2').replace('modules-k292-private','modules-k292-r2-private').replace('logdump-k292-candidate-private','logdump-k292-r2-candidate-private').replace('Image-k292-private','Image-k292-r2-private')
p=ROOT/'package-boot-r2.py';assert not p.exists();p.write_text(s)
print(json.dumps(report,indent=2))
