from pathlib import Path
import subprocess,json,hashlib
src=Path('/home/cy122/pmos-samurai-kernel115')
dest=Path('/home/cy122/pmos-samurai-kernel116')
out=Path('/mnt/e/edk2-samurai-out/kernel116')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel116')
assert not dest.exists();dest.mkdir()
out.mkdir(exist_ok=False);ref.mkdir(exist_ok=False)
for name in ['kernel','initramfs']:
    subprocess.run(['cp','-a','--reflink=auto',str(src/name),str(dest/name)],check=True)
k=dest/'kernel'
p=k/'.config';p.write_text(p.read_text().replace(str(src/'initramfs'),str(dest/'initramfs')))
patchdir=Path('/mnt/e/edk2-samurai-out/kernel115/camera-reference/aports/device/testing/linux-oneplus-hotdog-mainline616')
p=next(patchdir.glob('0055*'))
check=subprocess.run(['git','apply','--check',str(p)],cwd=k,capture_output=True,text=True)
(out/'first-camss-apply-check.txt').write_text(check.stdout+check.stderr)
report=dict(kernel_candidate=116,copied_from=115,first_camss_patch_applies=check.returncode==0,
 hardware_not_enabled=True,not_deployed=True,goal_complete=False)
if check.returncode==0:
    subprocess.run(['git','apply',str(p)],cwd=k,check=True)
    report['base_sm8150_camss_added']=True
else:
    report['base_sm8150_camss_added']=False
    report['next_step']='adapt 6.16 resource hunks to 7.3 API after reviewing first-camss-apply-check.txt'
for folder in [out,ref]: (folder/'camss-initial-port-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
