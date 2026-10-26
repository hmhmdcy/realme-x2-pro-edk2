from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference')
text=(ref/'kernel112/collect-layout-after.sh').read_text().replace('112','113')
text=text.replace("uname -v | grep -q '^#113 '",'''uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-radio-clean-3/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
''')
(ref/'kernel113/collect-layout-after.sh').write_text(text)
print('KERNEL113_POST_TRIAL_LAYOUT_CAPTURE_PREPARED')
