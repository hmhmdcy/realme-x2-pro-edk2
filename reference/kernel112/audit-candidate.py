from pathlib import Path
import hashlib, json, shutil, subprocess

out=Path('/mnt/e/edk2-samurai-out/kernel112')
oldout=Path('/mnt/e/edk2-samurai-out/kernel111')
baseline=Path('/home/cy122/pmos-samurai-kernel111')
stage=Path('/home/cy122/pmos-samurai-kernel112')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prepared=json.loads((out/'preparation.json').read_text())
old=json.loads((oldout/'candidate-validation.json').read_text())
device=json.loads((oldout/'firstboot-validation.json').read_text())
assert device['flashed_boot_and_logdump_verified']
before=(out/'config-before').read_text()
assert before==(baseline/'kernel/.config').read_text()
after=(out/'config-after').read_text()
normalize=lambda s:s.replace('/home/cy122/pmos-samurai-kernel112/initramfs',
    '/home/cy122/pmos-samurai-kernel111/initramfs').replace('CONFIG_LOG_BUF_SHIFT=20\n','CONFIG_LOG_BUF_SHIFT=17\n')
assert normalize(after)==before
for name in json.loads((oldout/'source-change-manifest.json').read_text()):
    assert sha(stage/'kernel'/name)==sha(baseline/'kernel'/name)
helper='usr/sbin/samurai-rootfs'
for path in (baseline/'initramfs').rglob('*'):
    relative=path.relative_to(baseline/'initramfs')
    dest=stage/'initramfs'/relative
    if path.is_symlink(): assert dest.is_symlink() and path.readlink()==dest.readlink()
    elif path.is_file() and str(relative)!=helper: assert path.read_bytes()==dest.read_bytes()
assert sha(stage/'initramfs'/helper)==prepared['rootfs_helper_after_sha256']
assert sha(baseline/'initramfs'/helper)==prepared['rootfs_helper_before_sha256']
assert 'while [ "$count" -lt 300 ]; do' in (stage/'initramfs'/helper).read_text()
assert b'#112 SMP PREEMPT' in (out/'Image-startup').read_bytes()
assert sha(out/'dtb-startup')==sha(oldout/'dtb-sensors')==old['dtb_sha256']
assert sha(baseline/'kernel/arch/arm64/boot/Image')==old['image_sha256']
# Check the actual embedded newc archive, including the modified handoff helper.
data=(out/'cpio-startup').read_bytes(); offset=0; files={}
while offset+110<=len(data):
    header=data[offset:offset+110]; assert header[:6] in [b'070701',b'070702']
    size=int(header[54:62],16); namesize=int(header[94:102],16)
    start=offset+110; name=data[start:start+namesize-1].decode()
    payload=(start+namesize+3)&~3
    files[name]=data[payload:payload+size]
    offset=(payload+size+3)&~3
    if name=='TRAILER!!!':break
assert files[helper]==(stage/'initramfs'/helper).read_bytes()
assert files['init']==(baseline/'initramfs/init').read_bytes()
source=oldout/'logdump-k111-sensors.img'
assert sha(source)==old['logdump_sha256']
candidate=out/'logdump-k112-startup.img'
assert not candidate.exists()
shutil.copyfile(source,out/'logdump-before.img')
shutil.copyfile(source,candidate)
subprocess.run(['mcopy','-o','-i',str(candidate),str(out/'Image-startup'),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(candidate),'::/Image','-'])==(out/'Image-startup').read_bytes()
assert subprocess.check_output(['mcopy','-i',str(candidate),'::/samurai.dtb','-'])==(out/'dtb-startup').read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(candidate),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
assert candidate.stat().st_size==64*1024*1024
report=dict(candidate_audit_pass=True,kernel_build=112,baseline=111,
    config_delta=prepared['config_delta'],log_buffer_bytes=1048576,
    userdata_discovery_wait_seconds=300,slpi_auto_boot=False,
    initramfs_other_files_preserved=True,dtb_byte_identical=True,boot_firmware_unchanged=True,
    flash_partitions=['logdump'],userdata_reformatted=False,
    boot_sha256=old['boot_sha256'],before_logdump_sha256=old['logdump_sha256'],
    logdump_sha256=sha(candidate),image_sha256=sha(out/'Image-startup'),
    dtb_sha256=sha(out/'dtb-startup'),physical_hardware_tested=False,goal_complete=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('KERNEL112_CONFIG_CPIO_UNCHANGED_SOURCE_DTB_AND_FAT_AUDIT_PASS')
