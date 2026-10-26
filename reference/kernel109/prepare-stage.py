from pathlib import Path
import hashlib, json, shutil, subprocess

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel109')
out=Path('/mnt/e/edk2-samurai-out/kernel109')
stage=Path('/home/cy122/pmos-samurai-kernel109')
src=Path('/home/cy122/x2pro-linux/linux')
init=src.parent/'initramfs'
prev=out.parent/'kernel108'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not stage.exists() and not (out/'preparation.json').exists()
out.mkdir(exist_ok=True)
b=(out/'baseline-private.txt').read_text(encoding='utf-8-sig').splitlines()
assert b[0]==(prev/'runtime-boot-id-after-private.txt').read_text().strip()
assert '#106 SMP PREEMPT' in b[1] and b[3]=='0'
p=json.loads((prev/'preparation.json').read_text())
for name, rel, key in [('Image','arch/arm64/boot/Image','image_sha256'),('dtb','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb_sha256'),('cpio','usr/initramfs_data.cpio','cpio_sha256')]:
    assert sha(src/rel)==p[key]
    shutil.copyfile(src/rel,out/(name+'-before'))
shutil.copyfile(src/'.config',out/'config-before')
(out/'kernel-source-before.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=src))
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=src,text=True).splitlines()
(out/'untracked-before.json').write_text(json.dumps({n:sha(src/n) for n in untracked if (src/n).is_file()},indent=2))
(out/'initramfs-before.json').write_text(json.dumps({str(f.relative_to(init)):sha(f) for f in init.rglob('*') if f.is_file() and not f.is_symlink()},indent=2))
stage.mkdir()
subprocess.run(['cp','-a','--reflink=auto',str(src),str(stage/'kernel')],check=True)
subprocess.run(['cp','-a',str(init),str(stage/'initramfs')],check=True)
subprocess.run(['cp','-a','/home/cy122/pmos-samurai-rootfs01/work/chroot_rootfs_postmarketos-trailblazer',str(stage/'rootfs')],check=True)
for name in ['scp-private.ps1','collect-preflash.sh','split-backups.sh','receive-backups.ps1','stop-connectivity.sh','reboot-f1.ps1','read-eud.ps1','haptics-device']:
    text=(ref.parent/'kernel108'/name).read_text().replace('kernel108','kernel109').replace('k108','k109').replace('K108','K109')
    assert not (ref/name).exists()
    (ref/name).write_text(text)
for name in ['fastboot-identity.json','wpa-5g-private.conf','wpa-2g-private.conf']:
    shutil.copyfile(prev/name,out/name)
(out/'before-boot-id-private.txt').write_text(b[0]+'\n')
(out/'preparation.json').write_text(json.dumps(dict(stage=109,before_boot_id=b[0],old_kernel_build=106,expected_full_boot_sha256=p['expected_full_boot_sha256'],expected_logdump_sha256=p['expected_logdump_sha256'],userdata_authorized=True,userdata_bytes=119033245696,userdata_partuuid=(out/'userdata-partuuid-private.txt').read_text().strip(),isolated_stage=str(stage)),indent=2)+'\n')
print('STAGE109_CURRENT_SOURCE_INITRAMFS_AND_USERSPACE_COPIED; BASELINE_HASHES_MATCH')
