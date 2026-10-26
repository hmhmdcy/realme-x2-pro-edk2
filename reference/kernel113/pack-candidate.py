from pathlib import Path
import hashlib, json, shutil, subprocess, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel113')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
stage = Path('/home/cy122/pmos-samurai-kernel113')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
k = json.loads((out / 'kernel-validation.json').read_text())
fw = json.loads((out / 'canonical-firmware/firmware-validation.json').read_text())
restore = json.loads((out / 'original-firmware-restore-validation.json').read_text())
pre = json.loads((out / 'preflash-validation.json').read_text())
assert k['kernel_audit_pass'] and k['kernel_build'] == 113 and not k['slpi_auto_boot']
assert fw['firmware_audit_pass'] and fw['only_embedded_dtb_changed']
assert restore['original_source_preserved'] and pre['preflash_audit_pass']
for filename,key in [('Image-sensor-power','image_sha256'),('dtb-sensor-power','dtb_sha256'),('cpio-sensor-power','cpio_sha256')]:
    assert sha(out / filename) == k[key]
assert sha(out / 'dtb-sensor-power') == fw['dtb_sha256']
boot_old = out.parent / 'kernel111/boot-partition-k111.img'
log_old = out.parent / 'kernel112/logdump-k112-startup.img'
assert sha(boot_old) == pre['before_boot_sha256'] and sha(log_old) == pre['before_logdump_sha256']
assert boot_old.stat().st_size == 96*1024*1024 and log_old.stat().st_size == 64*1024*1024
for source,name in [(boot_old,'boot-partition-before.img'),(log_old,'logdump-before.img')]:
    assert not (out/name).exists(); shutil.copyfile(source,out/name)
boot_candidate = out / 'boot-partition-k113.img'
log_candidate = out / 'logdump-k113-sensor-power.img'
assert not boot_candidate.exists() and not log_candidate.exists()
payload = (out / 'canonical-firmware/boot-k113-sensors.img').read_bytes()
assert len(payload) == fw['boot_bytes'] and hashlib.sha256(payload).hexdigest() == fw['boot_sha256']
buffer = bytearray(boot_old.read_bytes()); buffer[:len(payload)] = payload
boot_candidate.write_bytes(buffer)
assert boot_candidate.read_bytes()[len(payload):] == boot_old.read_bytes()[len(payload):]
shutil.copyfile(log_old,log_candidate)
listing = lambda: set(subprocess.check_output(['mdir','-b','-s','-i',str(log_candidate),'::'],text=True).splitlines())
assert listing() == {'::/Image','::/samurai.dtb'}
for source,target in [('Image-sensor-power','::/Image'),('dtb-sensor-power','::/samurai.dtb')]:
    subprocess.run(['mcopy','-o','-i',str(log_candidate),str(out/source),target],check=True)
    assert subprocess.check_output(['mcopy','-i',str(log_candidate),target,'-']) == (out/source).read_bytes()
assert listing() == {'::/Image','::/samurai.dtb'} and log_candidate.stat().st_size == 64*1024*1024
package = out / 'module-package'; assert not package.exists(); package.mkdir()
for name in ['drivers/misc/fastrpc.ko','drivers/soc/qcom/socinfo.ko']:
    p = package / Path(name).name; shutil.copy2(stage / 'kernel' / name,p)
    subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(p)],check=True)
    assert not subprocess.check_output(['modinfo','-F','depends',str(p)],text=True).strip()
    assert subprocess.check_output(['modinfo','-F','vermagic',str(p)],text=True).strip() == '7.3.0-rc6-rmx1931-samurai+ SMP preempt mod_unload aarch64'
(package / 'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(package.glob('*.ko'))))
with tarfile.open(out / 'sensor-modules.tar','w') as t:
    for p in sorted(package.iterdir()): t.add(p,arcname=p.name)
report = dict(candidate_audit_pass=True,kernel_build=113,slpi_auto_boot=False,
              sensor_power_auto_enable=False,firmware_only_dtb_change=True,
              baseline_source_and_artifacts_preserved=True,rootfs_handoff_preserved=True,
              config_delta=k['config_delta'],flash_partitions=['boot','logdump'],
              userdata_reformatted=False,nv_partition_writes=False,persist_partition_writes=False,gpt_writes=False,
              before_boot_sha256=sha(boot_old),before_logdump_sha256=sha(log_old),
              boot_sha256=sha(boot_candidate),logdump_sha256=sha(log_candidate),
              image_sha256=k['image_sha256'],dtb_sha256=k['dtb_sha256'],
              module_package_sha256=sha(out/'sensor-modules.tar'),physical_hardware_tested=False,goal_complete=False)
(out / 'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(ref / 'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('KERNEL113_FULL_BOOT_LOGDUMP_FAT_READBACK_MODULES_ROLLBACK_AUDIT_PASS')
