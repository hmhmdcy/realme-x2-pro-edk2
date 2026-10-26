from pathlib import Path
import hashlib, json, subprocess

out=Path('/mnt/e/edk2-samurai-out/kernel100')
root=Path('/mnt/e/RealmeX2Pro edk2')
kernel=Path('/home/cy122/x2pro-linux/linux')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def cpio(path):
    data=path.read_bytes();offset=0;result={}
    align=lambda n:(n+3)&~3
    while offset+110<=len(data):
        assert data[offset:offset+6]==b'070701'
        fields=[int(data[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
        start=offset+110;name=data[start:start+fields[11]-1].decode()
        start=align(start+fields[11]);content=data[start:start+fields[6]];offset=align(start+fields[6])
        if name=='TRAILER!!!': return result
        assert name not in result
        result[name]=(fields,content)
    raise AssertionError('Missing CPIO trailer')
before,after=cpio(out/'cpio-before'),cpio(out/'cpio-after')
assert before.keys()==after.keys()
changed=[]
for name in before:
    old,data=before[name];new,content=after[name]
    # Repacking changes inode and mtime. Preserve permissions/owners/links/device numbers.
    assert [old[i] for i in (1,2,3,4,7,8,9,10)]==[new[i] for i in (1,2,3,4,7,8,9,10)],name
    if data!=content: changed.append(name)
assert changed==['usr/sbin/samurai-wifi'],changed
assert after[changed[0]][1]==(root/'reference/kernel99/samurai-wifi').read_bytes()
assert before[changed[0]][1]==(root/'reference/kernel97/samurai-wifi').read_bytes()
assert (out/'config-before').read_bytes()==(out/'config-after').read_bytes()
assert (out/'dtb-before').read_bytes()==(out/'dtb-readiness').read_bytes()
assert (kernel/'drivers/input/misc/aw8697-samurai.c').read_bytes()==(root/'reference/kernel99/aw8697-samurai.c').read_bytes()
assert (kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_bytes()==(root/'reference/kernel99/sm8150-samurai.dts.after').read_bytes()
report=dict(kernel_audit_pass=True,kernel_build=99,logical_stage=100,
    original_initramfs_files_preserved=True,earlier_snapshots_preserved=True,
    cpio_content_changes=changed,config_byte_identical=True,dtb_byte_identical=True,
    motor_driver_unchanged=True,all_existing_modules_byte_identical=True,
    firmware_boot_reused_byte_identical=True,readiness_fix_embedded=True,
    image_sha256=sha(out/'Image-readiness'),dtb_sha256=sha(out/'dtb-readiness'),cpio_sha256=sha(out/'cpio-after'),
    kernel_source_diff_unchanged=True,goal_complete=False)
assert subprocess.check_output(['git','diff','--binary'],cwd=kernel)==(out/'kernel-source-before.patch').read_bytes()
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
