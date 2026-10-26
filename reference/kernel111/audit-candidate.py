from pathlib import Path
import hashlib,json,re,shutil,subprocess,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel111')
baseline_out=Path('/mnt/e/edk2-samurai-out/kernel109')
stage=Path('/home/cy122/pmos-samurai-kernel111')
baseline=Path('/home/cy122/pmos-samurai-kernel109')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fw=json.loads((out/'canonical-firmware/firmware-validation.json').read_text())
restore=json.loads((out/'original-firmware-restore-validation.json').read_text())
assert fw['firmware_audit_pass'] and fw['only_embedded_dtb_changed'] and restore['original_source_preserved']
changes=json.loads((out/'source-change-manifest.json').read_text())
assert set(changes)=={'drivers/misc/fastrpc.c','drivers/remoteproc/qcom_q6v5_pas.c',
    'drivers/soc/qcom/qcom_pd_mapper.c','arch/arm64/boot/dts/qcom/sm8150-samurai.dts'}
for name,h in changes.items():
    assert sha(baseline/'kernel'/name)==h['before'] and sha(stage/'kernel'/name)==h['after']
before=(out/'config-before').read_text();after=(out/'config-after').read_text()
assert before==(baseline/'kernel/.config').read_text()
normalize=lambda s:s.replace('/home/cy122/pmos-samurai-kernel111/initramfs','/home/cy122/pmos-samurai-kernel109/initramfs')
assert normalize(after)==before, 'Unexpected kernel configuration change'
for path in (baseline/'initramfs').rglob('*'):
    target=stage/'initramfs'/path.relative_to(baseline/'initramfs')
    if path.is_symlink():assert target.is_symlink() and target.readlink()==path.readlink()
    elif path.is_file() and path.name!='init':assert path.read_bytes()==target.read_bytes()
init=(stage/'initramfs/init').read_text()
assert '. /usr/sbin/samurai-rootfs' in init
assert '/usr/sbin/samurai-wifi start' not in init and '/usr/sbin/samurai-bluetooth boot' not in init
assert sha(baseline/'kernel/arch/arm64/boot/Image')==sha(baseline_out/'Image-pmos')
assert sha(out/'firmware-after.dtb')==fw['dtb_sha256']==sha(out/'dtb-sensors')
assert b'#111 SMP PREEMPT' in (out/'Image-sensors').read_bytes()
pas=(stage/'kernel/drivers/remoteproc/qcom_q6v5_pas.c').read_text()
resource=re.search(r'static const struct qcom_pas_data sm8150_slpi_resource_init = \{.*?\n\};',pas,re.S)
assert resource and '.auto_boot = false' in resource.group()
# Make the full partition writes deterministic, including unused trailing bytes.
boot_old=baseline_out/'boot-partition-before.img'
logdump_old=baseline_out/'logdump-k109-pmos.img'
assert sha(boot_old)=='d1f81ebc4dc9687b705cffe38ecde93b8c4cd60a4c37463901b7cf7b900e1278'
assert sha(logdump_old)=='f2d073047a3b719ff8dd5ef0fa2adae13a92478f13bf23031f88f91cbf496707'
boot_candidate=out/'boot-partition-k111.img';logdump_candidate=out/'logdump-k111-sensors.img'
assert not boot_candidate.exists() and not logdump_candidate.exists()
for source,name in [(boot_old,'boot-partition-before.img'),(logdump_old,'logdump-before.img')]:
    assert not (out/name).exists();shutil.copyfile(source,out/name)
buffer=bytearray(boot_old.read_bytes())
payload=(out/'canonical-firmware/boot-k111-sensors.img').read_bytes()
assert len(buffer)==96*1024*1024 and len(payload)==fw['boot_bytes'] and hashlib.sha256(payload).hexdigest()==fw['boot_sha256']
buffer[:len(payload)]=payload
boot_candidate.write_bytes(buffer)
shutil.copyfile(logdump_old,logdump_candidate)
names=set(subprocess.check_output(['mdir','-b','-s','-i',str(logdump_candidate),'::'],text=True).splitlines())
assert names=={'::/Image','::/samurai.dtb'}
for filename,target in [('Image-sensors','::/Image'),('dtb-sensors','::/samurai.dtb')]:
    subprocess.run(['mcopy','-o','-i',str(logdump_candidate),str(out/filename),target],check=True)
    assert subprocess.check_output(['mcopy','-i',str(logdump_candidate),target,'-'])==(out/filename).read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(logdump_candidate),'::'],text=True).splitlines())==names
assert logdump_candidate.stat().st_size==64*1024*1024
# Only two currently absent modules are needed for the explicit sensor experiment.
package=out/'module-package';assert not package.exists();package.mkdir()
for name in ['drivers/misc/fastrpc.ko','drivers/soc/qcom/socinfo.ko']:
    p=package/Path(name).name;shutil.copy2(stage/'kernel'/name,p)
    subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(p)],check=True)
    depends=subprocess.check_output(['modinfo','-F','depends',str(p)],text=True).strip()
    assert not depends
    vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(p)],text=True).strip()
    assert vermagic=='7.3.0-rc6-rmx1931-samurai+ SMP preempt mod_unload aarch64'
(package/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(package.glob('*.ko'))))
with tarfile.open(out/'sensor-modules.tar','w') as t:
    for p in sorted(package.iterdir()):t.add(p,arcname=p.name)
report=dict(candidate_audit_pass=True,kernel_build=111,slpi_auto_boot=False,
    firmware_only_dtb_change=True,baseline_source_and_artifacts_preserved=True,
    config_delta=['CONFIG_INITRAMFS_SOURCE'],rootfs_handoff_preserved=True,
    flash_partitions=['boot','logdump'],userdata_reformatted=False,
    nv_partition_writes=False,persist_partition_writes=False,gpt_writes=False,
    before_boot_sha256=sha(boot_old),before_logdump_sha256=sha(logdump_old),
    boot_sha256=sha(boot_candidate),logdump_sha256=sha(logdump_candidate),
    image_sha256=sha(out/'Image-sensors'),dtb_sha256=sha(out/'dtb-sensors'),
    module_package_sha256=sha(out/'sensor-modules.tar'),physical_hardware_tested=False,goal_complete=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('KERNEL111_IMAGE_CPIO_CONFIG_MODULES_FAT_FIRMWARE_BACKUPS_AUDIT_PASS')
