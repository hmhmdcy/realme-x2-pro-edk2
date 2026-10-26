from pathlib import Path
import tarfile,hashlib,subprocess,json
out=Path('/mnt/e/edk2-samurai-out/kernel115');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
archive=out/'delay-fix-runtime-complete.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='29389703cd7e9431df485fb694b4da25270124071025e36fd728d7350df8696e'
with tarfile.open(archive) as tf:
    data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for row in data['SHA256SUMS'].decode().splitlines():
    digest,name=row.split('  ',1);assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert data['state.txt'].splitlines()[-1]==b'0'
log=data['dmesg.txt'].decode()
assert log.count('WARNING: drivers/net/ipa/reg.h:87')==0 and 'IPA driver setup completed successfully' in log
out.joinpath('recover-source-boot-id-private.txt').write_bytes(data['boot-id-private.txt'])
t=(ref/'quiesce-clean-115.sh').read_text().replace('/var/lib/samurai/k115-first-runtime/boot-id-private.txt','/var/lib/samurai/k115-delay-fix-runtime/boot-id-private.txt').replace('kernel/tainted)" = 512','kernel/tainted)" = 0')
(ref/'quiesce-recovery.sh').write_text(t)
t=(ref/'freeze-for-bootloader.sh').read_text().replace("'^#113 '","'^#115 '").replace('/var/lib/samurai/k115-preflash/boot-id-private.txt','/var/lib/samurai/k115-delay-fix-runtime/boot-id-private.txt').replace('kernel/tainted)" = 512','kernel/tainted)" = 0').replace('k115-flash-quiesce/remoteproc-final-state.txt','k115-recovery-quiesce/remoteproc-final-state.txt').replace('/var/lib/samurai/k115-preflash/partition-check.sha256','/var/lib/samurai/k115-delay-fix-runtime/partition-check.sha256')
(ref/'freeze-recovery.sh').write_text(t)
t=(ref/'enter-bootloader.ps1').read_text().replace('source-boot-id-private.txt','recover-source-boot-id-private.txt').replace('k115-freeze-for-bootloader.sh','k115-freeze-recovery.sh')
(ref/'enter-recovery-bootloader.ps1').write_text(t)
report=dict(kernel_build=115,delay_fixed_module_booted=True,ipa_register_warnings=0,taint=0,ipa_setup_pass=True,rcu_boot_stall=log.count('rcu_preempt detected stalls'),display_kms_bind_failed='kms hw init failed: -22' in log,gui_recovery_required=True,no_forced_reset_or_userdata_erase=True,goal_complete=False)
for dest in [out,ref]: (dest/'delay-fix-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
