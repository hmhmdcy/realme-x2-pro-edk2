#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k134-early-display-readonly
test ! -e "$dest"
uname -v | grep -q '^#134 '
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -a > "$dest/uname.txt"
dmesg > "$dest/dmesg-private.txt"
cat /proc/modules > "$dest/modules.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
cat /sys/kernel/debug/devices_deferred > "$dest/deferred.txt"
rc-status default > "$dest/services.txt"
ls -l /dev/dri /sys/class/drm > "$dest/drm.txt" 2>&1 || true
ls -l /sys/bus/platform/devices/ae00000.display-subsystem /sys/bus/platform/devices/ae01000.display-controller > "$dest/platform.txt" 2>&1 || true
cat /home/cy122/.local/state/samurai-phosh-session.log > "$dest/phosh-session-private.txt" 2>&1 || true
cat /sys/class/power_supply/samurai-usb-input/uevent > "$dest/usb-input-uevent.txt"
cat /sys/class/power_supply/mp2650-input/uevent > "$dest/mp2650-uevent.txt"
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k134+ && sha256sum -c /var/lib/samurai/k134-preflash/new-module-tree.sha256) > "$dest/module-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k134-early-display-private.tar.gz .
echo K134_EARLY_DISPLAY_READONLY_CAPTURE_COMPLETE
