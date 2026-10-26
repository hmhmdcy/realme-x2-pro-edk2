#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k114-qmi-readonly
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k114-rootfs-export/boot-id-private.txt)"
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before.txt"
qrtr-lookup > "$dest/qrtr-before.txt"
for query in dms-get-capabilities dms-get-operating-mode uim-get-card-status nas-get-system-info loc-get-supported-messages; do
    result=0
    timeout -s TERM -k 3 30 qmicli -d qrtr://0 --"$query" > "$dest/$query-private.txt" 2>&1 || result=$?
    printf '%s %s\n' "$query" "$result" >> "$dest/results.txt"
done
mmcli -L > "$dest/mm-list.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
cat /proc/sys/kernel/tainted > "$dest/taint-after.txt"
dmesg > "$dest/dmesg-after.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k114-qmi-readonly-private.tar.gz .
sha256sum /tmp/k114-qmi-readonly-private.tar.gz
cat "$dest/results.txt"
echo QMI114_READONLY_BOUNDED_PROBES_ARCHIVED
