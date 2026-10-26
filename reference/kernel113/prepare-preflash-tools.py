from pathlib import Path

root = Path('/mnt/e/RealmeX2Pro edk2/reference')
text = (root / 'kernel112/collect-layout-after.sh').read_text()
text = text.replace('k112-layout-after', 'k113-preflash')
text = text.replace("uname -v | grep -q '^#112 '", '''uname -v | grep -q '^#112 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k112-reboot-radio-clean-2/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/name)" = slpi
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test -z "$(pidof hexagonrpcd)"''')
text = text.replace('dmesg > "$dest/dmesg.txt"', '''dmesg > "$dest/dmesg.txt"
cat /proc/mounts > "$dest/mounts.txt"
uname -a > "$dest/uname.txt"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"''')
text = text.replace('LAYOUT_AFTER_CAPTURED_READ_ONLY', 'KERNEL113_PREFLASH_READONLY_CAPTURED')
path = root / 'kernel113/collect-preflash.sh'
assert not path.exists(); path.write_text(text)
text = (root / 'kernel111/freeze-for-bootloader.sh').read_text()
text = text.replace('k111', 'k113').replace('KERNEL111', 'KERNEL113')
text = text.replace('#109 SMP PREEMPT', '#112 SMP PREEMPT')
text = text.replace('test -d /var/lib/samurai/k113-preflash', '''test -d /var/lib/samurai/k113-preflash
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-preflash/boot-id-private.txt)"
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test -z "$(pidof hexagonrpcd)"''')
path = root / 'kernel113/freeze-for-bootloader.sh'
assert not path.exists(); path.write_text(text)
text = (root / 'kernel111/enter-bootloader.ps1').read_text()
text = text.replace('kernel111', 'kernel113').replace('k111', 'k113').replace('KERNEL111', 'KERNEL113')
text = text.replace("$Prefix='sensors-first'", "$Prefix='sensor-power-first'")
path = root / 'kernel113/enter-bootloader.ps1'
assert not path.exists(); path.write_text(text)
print('Fresh current-boot preflash and filesystem-freeze guards prepared')
