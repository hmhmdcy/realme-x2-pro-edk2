from pathlib import Path
import hashlib,json,re,shutil,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel108';old=root/'reference/kernel107';out=Path('/mnt/e/edk2-samurai-out/kernel108');prev=out.parent/'kernel107';k=Path('/home/cy122/x2pro-linux/linux');init=k.parent/'initramfs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (out/'preparation.json').exists()
b=(out/'baseline-boot-private.txt').read_text(encoding='utf-8-sig').splitlines()
assert b[0]==(prev/'runtime-boot-id-after-private.txt').read_text().strip() and '#106 SMP PREEMPT' in b[1] and b[3]=='0' and b.count('running')==2
c=json.loads((prev/'candidate-validation.json').read_text());v=json.loads((prev/'kernel-validation.json').read_text())
for n,p,key in [('Image','arch/arm64/boot/Image','image_sha256'),('dtb','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb_sha256'),('cpio','usr/initramfs_data.cpio','cpio_sha256')]:
    assert sha(k/p)==v[key]
    if n!='Image':shutil.copyfile(k/p,out/(n+'-before'))
shutil.copyfile(k/'.config',out/'config-before')
(out/'kernel-source-before.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=k))
(out/'initramfs-before.json').write_text(json.dumps({str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()},indent=2))
(out/'untracked-before.json').write_text(json.dumps({n:sha(k/n) for n in subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=k,text=True).splitlines() if (k/n).is_file()},indent=2))
for n in ['collect-preflash.sh','split-backups.sh','receive-backups.ps1','scp-private.ps1','stop-connectivity.sh','reboot-f1.ps1','read-eud.ps1','haptics-device','collect-audio-runtime.sh','collect-first-radio-trace.sh','test-auto-network.sh','analyse-trace.py','inspect-radio-order.py']:
    assert not (ref/n).exists();s=(old/n).read_text().replace('kernel107','kernel108').replace('k107','k108').replace('K107','K108')
    if n in ['collect-preflash.sh','split-backups.sh']:s=s.replace('#105 SMP PREEMPT','#106 SMP PREEMPT')
    if n=='collect-preflash.sh':
        hs=re.findall(r"grep -q '\^([a-f0-9]{64}) ",s);assert len(hs)==2
        s=s.replace(hs[0],c['boot_sha256']).replace(hs[1],c['logdump_sha256'])
    (ref/n).write_text(s)
for n in ['fastboot-identity.json','wpa-5g-private.conf','wpa-2g-private.conf']:
    assert not (out/n).exists();shutil.copyfile(prev/n,out/n)
(out/'preparation.json').write_text(json.dumps(dict(stage=108,kernel_build=106,new_kernel_built=False,new_partitions_flashed=False,expected_full_boot_sha256=c['full_backup_boot_sha256'],expected_logdump_sha256=c['logdump_sha256'],image_sha256=v['image_sha256'],dtb_sha256=v['dtb_sha256'],cpio_sha256=v['cpio_sha256'],goal_complete=False),indent=2)+'\n')
print('FRESH_SAME_KERNEL_REBOOT_AND_SOURCE_PRESERVATION_TOOLS_PREPARED')
