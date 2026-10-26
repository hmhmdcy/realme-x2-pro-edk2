from pathlib import Path
import json,hashlib,subprocess,shutil
out=Path('/mnt/e/edk2-samurai-out/kernel115')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
k=json.loads((out/'kernel-build-validation.json').read_text())
fw=json.loads((out/'canonical-firmware/firmware-validation.json').read_text())
pre=json.loads((out/'preflash-validation.json').read_text())
pkg=json.loads((out/'runtime-package-validation.json').read_text())
assert k['full_image_modules_dtb_build_pass'] and k['kernel_build']==115 and k['own_imem_address']=='0x146bd000'
assert fw['firmware_audit_pass'] and fw['only_embedded_dtb_changed']
assert pre['preflash_audit_pass'] and pkg['full_module_tree']
oldboot=out/'boot-partition-before.img'
oldlog=out/'logdump-before.img'
assert sha(oldboot)==pre['before_boot_sha256'] and sha(oldlog)==pre['before_logdump_sha256']
boot=out/'boot-partition-k115.img';log=out/'logdump-k115-ipa-zram.img'
assert not boot.exists() and not log.exists()
payload=(out/'canonical-firmware/boot-k115-ipa-zram.img').read_bytes()
assert sha(out/'canonical-firmware/boot-k115-ipa-zram.img')==fw['boot_sha256']
data=bytearray(oldboot.read_bytes());data[:len(payload)]=payload;boot.write_bytes(data)
assert boot.read_bytes()[len(payload):]==oldboot.read_bytes()[len(payload):]
shutil.copyfile(oldlog,log)
for source,target in [('Image-ipa-zram','::/Image'),('dtb-ipa-zram','::/samurai.dtb')]:
    subprocess.run(['mcopy','-o','-i',str(log),str(out/source),target],check=True)
    assert subprocess.check_output(['mcopy','-i',str(log),target,'-'])==(out/source).read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(log),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
assert boot.stat().st_size==100663296 and log.stat().st_size==67108864
report=dict(candidate_audit_pass=True,kernel_build=115,slpi_auto_boot=False,sensor_power_auto_enable=False,ipa_enabled=True,own_ipa_firmware=True,gsi_wait_bounded_ms=1000,firmware_only_dtb_change=True,baseline_source_and_artifacts_preserved=True,flash_partitions=['boot','logdump'],userdata_reformatted=False,nv_partition_writes=False,persist_partition_writes=False,gpt_writes=False,before_boot_sha256=sha(oldboot),before_logdump_sha256=sha(oldlog),boot_sha256=sha(boot),logdump_sha256=sha(log),module_package_sha256=pkg['archive_sha256'],physical_hardware_tested=False,goal_complete=False)
for dest in [out,ref]: (dest/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('KERNEL115_BOOT_LOGDUMP_FAT_READBACK_AND_CURRENT113_ROLLBACK_AUDIT_PASS')
