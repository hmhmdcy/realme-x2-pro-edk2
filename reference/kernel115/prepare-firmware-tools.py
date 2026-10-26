from pathlib import Path
import shutil
root=Path('/mnt/e/RealmeX2Pro edk2/reference')
out=Path('/mnt/e/edk2-samurai-out/kernel115')
ref=root/'kernel115'
old=root/'kernel113'
for name in ['dtb-before','boot-before.img']:
    shutil.copy2(out.parent/'kernel113'/name,out/name)
t=(old/'build-canonical-firmware.sh').read_text().replace('kernel113','kernel115').replace('dtb-sensor-power','dtb-ipa-zram').replace('boot-k113-sensors.img','boot-k115-ipa-zram.img')
(ref/'build-canonical-firmware.sh').write_text(t)
t=(old/'verify-original-restore.py').read_text().replace('kernel113','kernel115')
(ref/'verify-original-restore.py').write_text(t)
t=(old/'audit-firmware.py').read_text().replace('kernel113','kernel115').replace('boot-k113-sensors.img','boot-k115-ipa-zram.img').replace('dtb-sensor-power','dtb-ipa-zram')
t=t.replace("prior=base_out.parent/'kernel111/canonical-firmware'","prior=base_out.parent/'kernel113/canonical-firmware'").replace('boot-k111-sensors.img','boot-k113-sensors.img').replace('actual_device_boot_111_executables_preserved','actual_device_boot_113_executables_preserved')
(ref/'audit-firmware.py').write_text(t)
shutil.copy2(out.parent/'kernel113/boot-partition-k113.img',out/'boot-partition-before.img')
shutil.copy2(out.parent/'kernel113/logdump-k113-sensor-power.img',out/'logdump-before.img')
t=(old/'collect-preflash.sh').read_text().replace("'^#112 '","'^#113 '").replace('/var/lib/samurai/k112-reboot-radio-clean-2/boot-id-private.txt','/var/lib/samurai/k114-final-health/boot-id-private.txt').replace('kernel/tainted)" = 0','kernel/tainted)" = 512').replace('k113','k115').replace('KERNEL113','KERNEL115')
(ref/'collect-preflash.sh').write_text(t)
print('KERNEL115_CANONICAL_FIRMWARE_AND_FRESH_BOOT113_READONLY_CAPTURE_TOOLS_READY')
