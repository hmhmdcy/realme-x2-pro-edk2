#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k136-current132
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k132+
test "$(cat /proc/sys/kernel/tainted)" = 0
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -a > "$dest/uname.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partitions-private.sha256"
grep -q '^501074e6feb3c5e93eff86f40848acbfc102da44e06cf52f95770d80a83d07f6 ' "$dest/partitions-private.sha256"
grep -q '^db6b966975b987cd51e91f9488185b0a5e4a557755cc3b7043f0e6550aa19751 ' "$dest/partitions-private.sha256"
grep -q '^7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3 ' "$dest/partitions-private.sha256"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
sha256sum -c /var/lib/samurai/k135-preflash/gui-config.sha256 > "$dest/gui-check.txt"
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k132-preflash/new-module-tree.sha256) > "$dest/module-check.txt"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"
cat /sys/class/power_supply/mp2650-input/uevent > "$dest/power-uevent.txt"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-state-private.txt"
dmesg > "$dest/dmesg-private.txt"
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k136-current132-private.tar.gz .
sha256sum /tmp/k136-current132-private.tar.gz > /tmp/k136-current132-private.tar.gz.sha256
echo K136_CURRENT_NEW_BOOT132_PARTITIONS_MODULES_SOURCES_AND_GUI_CHECKED
