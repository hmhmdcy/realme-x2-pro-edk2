#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k126-final-health
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(wc -l < "$dest/samples.txt")" = 6
test ! -e "$dest/SHA256SUMS"
test -d /sys/class/bluetooth/hci0
cat /sys/class/bluetooth/hci0/uevent > "$dest/bluetooth.txt"
cat /sys/class/net/wlan0/operstate > "$dest/wlan.txt"
ip -details link show rmnet_ipa0 > "$dest/ipa-private.txt"
cat /proc/swaps > "$dest/swaps.txt"
cat /sys/block/zram0/comp_algorithm /sys/block/zram0/disksize > "$dest/zram.txt"
rc-status default > "$dest/services.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k126+ && sha256sum -c /var/lib/samurai/k126-preflash/new-module-tree.sha256) > "$dest/modules-check.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partitions.sha256"
cat /sys/module/qcom_camss/parameters/dma_trace > "$dest/dma-trace.txt"
dmesg > "$dest/dmesg-after.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k126-final-health-private.tar.gz .
echo K126_FINAL_HEALTH_TRACE_PRESERVED_OFF_SIX_SAMPLES_CAPTURED
