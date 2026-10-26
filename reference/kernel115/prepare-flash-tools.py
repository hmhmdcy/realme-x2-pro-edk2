from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference')
ref=root/'kernel115'
t=(root/'kernel113/quiesce-clean-boot14.sh').read_text().replace('/var/lib/samurai/k113-reboot-audio-clean-14/boot-id-private.txt','/var/lib/samurai/k114-final-health/boot-id-private.txt').replace('kernel/tainted)" = 0','kernel/tainted)" = 512').replace('k113-$prefix','k115-$prefix')
(ref/'quiesce-clean.sh').write_text(t)
t=(root/'kernel113/enter-bootloader.ps1').read_text().replace('kernel113','kernel115').replace('k113','k115').replace('KERNEL113','KERNEL115')
(ref/'enter-bootloader.ps1').write_text(t)
t=(root/'kernel113/flash-sensor-power.ps1').read_text().replace('kernel113','kernel115').replace('k113','k115').replace('KERNEL113','KERNEL115').replace('kernel_build -ne 113','kernel_build -ne 115').replace('kernel_build=113','kernel_build=115').replace('logdump-k115-sensor-power.img','logdump-k115-ipa-zram.img')
t=t.replace("if ($audit.sensor_power_auto_enable", "if (!$audit.ipa_enabled -or !$audit.own_ipa_firmware -or $audit.gsi_wait_bounded_ms -ne 1000 -or $audit.sensor_power_auto_enable")
(ref/'flash-ipa-zram.ps1').write_text(t)
print('KERNEL115_FRESH_QUIESCE_FROZEN_ROOT_F1_AND_FLASH_SCOPE_GUARDS_READY')
