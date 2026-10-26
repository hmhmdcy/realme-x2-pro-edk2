from pathlib import Path
import hashlib, json, shutil, subprocess

root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel100'
out=Path('/mnt/e/edk2-samurai-out/kernel100')
old=out.parent/'kernel99'
kernel=Path('/home/cy122/x2pro-linux/linux')
initramfs=Path('/home/cy122/x2pro-linux/initramfs')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert not out.exists()
assert sha(kernel/'arch/arm64/boot/Image')=='d765d0d7d23c47c2229c63a83094be8656d4cfd8c5cda3d794141f2141e6cc91'
assert (kernel/'.config').read_bytes()==(old/'config-after').read_bytes()
assert (kernel/'usr/initramfs_data.cpio').read_bytes()==(old/'cpio-after').read_bytes()
assert (kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()==(old/'dtb-haptics').read_bytes()
assert (kernel/'drivers/input/misc/aw8697-samurai.c').read_bytes()==(root/'reference/kernel99/aw8697-samurai.c').read_bytes()
actual=initramfs/'usr/sbin/samurai-wifi'
assert actual.read_bytes()==(root/'reference/kernel97/samurai-wifi').read_bytes()
assert json.loads((old/'runtime-validation.json').read_text())['runtime_audit_pass']
out.mkdir()
for source,name in [(kernel/'.config','config-before'),(kernel/'usr/initramfs_data.cpio','cpio-before'),
    (kernel/'arch/arm64/boot/Image','Image-before'),(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-before'),
    (actual,'samurai-wifi-before'),(old/'boot-k99-haptics.img','boot-reused.img'),
    (old/'fastboot-identity.json','fastboot-identity.json')]:
    shutil.copyfile(source,out/name)
(out/'kernel-source-before.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=kernel))
firmware=Path('/home/cy122/edk2-samurai/repo')
dtb=firmware/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'
assert dtb.read_bytes()==(old/'dtb-haptics').read_bytes()
(out/'firmware-dtb-before.sha').write_text(sha(dtb)+'\n')
for name in ('reboot-f1.ps1','read-eud.ps1','stop-connectivity.sh','scp-private.ps1'):
    target=ref/name
    assert not target.exists()
    target.write_text((root/'reference/kernel99'/name).read_text().replace('kernel99','kernel100').replace('K99','K100').replace('k99','k100'))
target=ref/'flash-readiness.ps1'
assert not target.exists()
target.write_text((root/'reference/kernel98/flash-connectivity.ps1').read_text().replace('kernel98','kernel100').replace('K98','K100').replace('k98','k100').replace('$audit.kernel_build -ne 97','$audit.kernel_build -ne 99').replace('logdump-k100-connectivity.img','logdump-k100-readiness.img'))
actual.write_bytes((root/'reference/kernel99/samurai-wifi').read_bytes())
report=dict(prepared=True,logical_stage=100,kernel_build=99,only_initramfs_source_change='usr/sbin/samurai-wifi',
    wifi_before_sha256=sha(out/'samurai-wifi-before'),wifi_after_sha256=sha(actual),
    motor_driver_unchanged=True,dtb_unchanged=True,firmware_boot_reused=True,credentials_embedded=False,goal_complete=False)
(out/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
print('ALL_SOURCE_READINESS_PREPARED')
