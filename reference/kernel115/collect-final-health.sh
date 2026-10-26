#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k115-final-health
test ! -e "$dest"
uname -v | grep -q '^#115 '
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -v > "$dest/uname.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensors.txt"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
rc-status default > "$dest/services.txt"
pgrep -x phosh > "$dest/phosh.txt" || true
pgrep -x phoc > "$dest/phoc.txt" || true
cat /proc/swaps /sys/block/zram0/comp_algorithm /sys/block/zram0/disksize > "$dest/zram.txt"
cat /sys/block/zram0/mm_stat > "$dest/zram-mm-stat.txt"
cat /sys/class/net/wlan0/operstate > "$dest/wlan-state.txt"
ip -details link show rmnet_ipa0 > "$dest/ipa-net.txt"
sysctl net.ipv4.tcp_syncookies > "$dest/syncookies.txt"
mmcli -L > "$dest/modem-list-private.txt"
mmcli -m 0 -J > "$dest/modem-private.json" || true
sha256sum /lib/modules/7.3.0-rc6-rmx1931-samurai+/kernel/drivers/net/ipa/ipa.ko > "$dest/ipa-module.sha256"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partition-check.sha256"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"
cat /proc/mounts > "$dest/mounts.txt"
cat /sys/kernel/debug/devices_deferred > "$dest/deferred.txt"
for instance in /sys/kernel/tracing/instances/*; do
    test -d "$instance" || continue
    printf '%s ' "${instance##*/}" >> "$dest/traces.txt"
    cat "$instance/tracing_on" >> "$dest/traces.txt"
done
dmesg > "$dest/dmesg.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k115-final-health-private.tar.gz .
sha256sum /tmp/k115-final-health-private.tar.gz
echo KERNEL115_FINAL_NATIVE_HEALTH_SAVED
