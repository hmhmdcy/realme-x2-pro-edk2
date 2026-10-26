#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = dfe8e722-f6b7-4ce8-85cc-17dfba80f69d ]
dir=/tmp/k91-connected
test ! -e "$dir"
mkdir -m 700 "$dir"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state /sys/class/remoteproc/remoteproc0/recovery
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$dir/state.txt"
dmesg > "$dir/dmesg.txt"
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 status > "$dir/wpa-status.txt"
/tmp/k91-iw dev wlan0 link > "$dir/link.txt"
/tmp/k91-iw reg get > "$dir/reg.txt"
ip addr > "$dir/addresses.txt"
ip route > "$dir/routes.txt"
cp /tmp/k91-wpa-observed.log /tmp/k91-wpa-24-connected.log "$dir/"
cp /tmp/k91-stability2-rmtfs.txt /tmp/k91-stability2-tftp.txt "$dir/"
cp /tmp/k91-stability1-wpa-scan.txt /tmp/k91-stability2-qrtr-final.txt "$dir/"
cp /tmp/k91-dhcp.log /tmp/k91-dhcp-lease.txt /tmp/k91-ping-gateway.txt "$dir/"
cp /tmp/k91-ping-internet.txt /tmp/k91-dns-test.txt /tmp/k91-http-test.txt /tmp/k91-http-test.log "$dir/"
cp /tmp/k91-traffic-server.log "$dir/"
sha256sum /tmp/k91-traffic.bin /tmp/k91-traffic-upload.bin > "$dir/traffic-sha256.txt"
sha256sum -c /tmp/k91-nv-source-hashes.txt > "$dir/nv-partitions.txt"
(cd /tmp/k91-nv && sha256sum -c /tmp/k91-nv-SHA256SUMS) > "$dir/nv-snapshots.txt"
sha256sum /dev/sde4 > "$dir/modem-partition.txt"
for name in trace snapshot; do
    if [ -f "/sys/kernel/tracing/instances/display/$name" ]; then
        cat "/sys/kernel/tracing/instances/display/$name" > "$dir/display-$name.txt"
    fi
done
cat /sys/kernel/debug/dri/1/state > "$dir/drm-state.txt"
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k91-connected.tar k91-connected
sha256sum /tmp/k91-connected.tar
grep '^wpa_state=\|^freq=' "$dir/wpa-status.txt"
cat /proc/uptime /proc/sys/kernel/tainted
