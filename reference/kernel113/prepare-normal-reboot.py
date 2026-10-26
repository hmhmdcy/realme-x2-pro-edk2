from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference')
text=(ref/'kernel112/observe-radio-clean-reboot.ps1').read_text().replace('112','113')
text=text.replace("$BootCheckpoint='clean-reboot-1'", "$BootCheckpoint='first-before-slpi'")
text=text.replace('k113-rpcd-ram-trial/reboot-radio-clean.sh','k113-tools/reboot-radio-clean.sh')
text=text.replace("$command='test ", """$command='uname -v | grep -q "^#113 " && test "$(cat /sys/devices/platform/sensor-power/state)" = "vdd=0 vddio=0" && test """,1)
(ref/'kernel113/observe-radio-clean-reboot.ps1').write_text(text)
print('KERNEL113_NORMAL_REBOOT_POWER_OFF_GUARD_PREPARED')
