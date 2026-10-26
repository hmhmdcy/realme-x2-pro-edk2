from pathlib import Path
root = Path('/mnt/e/RealmeX2Pro edk2/reference')
text = (root/'kernel109/verify-desktop-after-reboot.sh').read_text()
text = text.replace('k109-desktop-', 'k113-desktop-')
text = text.replace('dest=/var/lib/samurai/', "uname -v | grep -q '^#113 '\ndest=/var/lib/samurai/",1)
text = text.replace('tar -C "$dest"', '''cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -a > "$dest/uname.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-state.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest"''',1)
(root/'kernel113/collect-desktop.sh').write_text(text)
print('KERNEL113_DESKTOP_VERIFICATION_PREPARED')
