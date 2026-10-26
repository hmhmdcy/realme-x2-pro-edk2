#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k114-loc-readonly
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k114-rootfs-export/boot-id-private.txt)"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
for query in loc-get-operation-mode loc-get-engine-lock loc-get-nmea-types; do
    result=0
    timeout -s TERM -k 3 30 qmicli -d qrtr://0 --"$query" > "$dest/$query-private.txt" 2>&1 || result=$?
    printf '%s %s\n' "$query" "$result" >> "$dest/results.txt"
done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k114-loc-readonly-private.tar.gz .
sha256sum /tmp/k114-loc-readonly-private.tar.gz
cat "$dest/results.txt"
