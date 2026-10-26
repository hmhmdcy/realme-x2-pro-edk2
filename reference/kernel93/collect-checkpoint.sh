#!/bin/sh
set -eu
umask 077
dir=/tmp/k93-checkpoint-final
test ! -e "$dir"
[ "$(cat /proc/sys/kernel/random/boot_id)" = b65a234f-44f4-4ad3-9d40-ecafdeb233b1 ]
mkdir -m 700 "$dir"
mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null || true
mount -t pstore pstore /sys/fs/pstore 2>/dev/null || true
dmesg > "$dir/dmesg.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
    if [ -f /sys/kernel/debug/dri/1/encoder-0/status ]; then
        cat /sys/kernel/debug/dri/1/encoder-0/status
    else
        echo 'DRM absent: inherited boot CTL shutdown failed -22; preserve full dmesg'
    fi
} > "$dir/state.txt"
if [ -f /sys/kernel/debug/dri/1/state ]; then
    cat /sys/kernel/debug/dri/1/state > "$dir/drm-state.txt"
else
    ls /sys/class/drm /sys/class/graphics > "$dir/drm-state.txt"
fi
cat /sys/kernel/debug/devices_deferred > "$dir/devices-deferred.txt"
for file in /sys/fs/pstore/*; do [ -f "$file" ] || continue; cp "$file" "$dir/"; done
cat /proc/interrupts > "$dir/interrupts.txt"
tr '\0' '\n' < /proc/device-tree/soc@0/geniqup@cc0000/serial@c8c000/bluetooth/firmware-name > "$dir/bt-firmware-name.txt"
/usr/sbin/qrtr-lookup > "$dir/qrtr.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
/usr/sbin/iw dev wlan0 info > "$dir/iw-info.txt"
/usr/sbin/iw dev wlan0 link > "$dir/iw-link.txt"
cp /run/samurai-wifi/dhcp-lease.txt "$dir/"
cp /run/samurai-wifi-boot.log "$dir/"
for name in rmtfs.log tftp.log nv-source-hashes.txt wpa-retry.log; do cp "/run/samurai-wifi/$name" "$dir/"; done
for file in /tmp/k93-retry.log /tmp/k93-coexistence.log /tmp/k93-coexistence-scan.txt /tmp/k93-coexistence-wpa.txt /tmp/k93-traffic-server.log /tmp/k93-traffic-sha.txt /tmp/k93-bt-*.txt /tmp/k93-nfc-controller.txt /tmp/k93-5ghz2-*.txt /tmp/k93-5ghz2-test.log /tmp/k93-5ghz-network-*.txt /tmp/k93-5ghz-traffic-*.txt /tmp/k93-5ghz-traffic-server.log /tmp/k93-5ghz-ping-*.txt /tmp/k93-5ghz-dns-test.txt /tmp/k93-5ghz-http-test.txt /tmp/k93-5ghz-http-test.log; do cp "$file" "$dir/"; done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde32 /usr/sbin/samurai-wifi
} > "$dir/deployment-readback.txt"
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k93-checkpoint-final.tar k93-checkpoint-final
sha256sum /tmp/k93-checkpoint-final.tar
