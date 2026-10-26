from pathlib import Path
import json,hashlib,subprocess,shutil
out=Path('/mnt/e/edk2-samurai-out/kernel118')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel118')
old=out.parent/'kernel115'
subprocess.run(['python3',str(ref/'ensure-build-volume.py')],check=True)
k=Path('/home/cy122/pmos-samurai-kernel118/kernel')
build=json.loads((out/'kernel-build-validation.json').read_text())
assert build['full_image_modules_dtb_build_pass'] and build['exported_module_abi_identical'] and build['dtb_byte_identical']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=old/'logdump-k115-ipa-zram.img'
assert baseline.stat().st_size==67108864
dtb=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
assert subprocess.check_output(['mcopy','-i',str(baseline),'::/samurai.dtb','-'])==dtb.read_bytes()
target=out/'logdump-k118-ctl-final-read.img'
image=k/'arch/arm64/boot/Image'
assert sha(image)==build['artifact_sha256']['arch/arm64/boot/Image']
if not target.exists():
    shutil.copyfile(baseline,target)
    subprocess.run(['mcopy','-o','-i',str(target),str(image),'::/Image'],check=True)
assert target.stat().st_size==67108864
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==dtb.read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
check=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True)
(out/'logdump-fat-check-private.txt').write_bytes(check.stdout+check.stderr)
assert check.returncode==0
report=dict(candidate=118,logdump_size=target.stat().st_size,logdump_sha256=sha(target),fat_readback_exact=True,fat_check_pass=True,image_sha256=sha(image),dtb_115_identical=True,boot_115_reused=True,boot_115_sha256=sha(old/'boot-partition-k115.img'),rollback_logdump_115_sha256=sha(baseline),module_115_export_abi_compatible=True,flash_partitions=['logdump'],fresh_preflash_audit_still_required=True,not_deployed=True,goal_complete=False)
for folder in [out,ref]:(folder/'candidate-package-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
