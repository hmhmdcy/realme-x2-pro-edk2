#!/bin/sh
set -eu
umask 077
result=0
timeout -s TERM -k 3 140 python3 /tmp/k114-gnss-single-client-v3.py || result=$?
dest=/var/lib/samurai/k114-gnss-single-client-v3
test -d "$dest"
echo "$result" > "$dest/program-result.txt"
if test "$result" != 0; then
    timeout -s TERM -k 3 30 qmicli -d qrtr://0 --loc-session-id=117 --loc-stop > "$dest/fallback-stop-private.txt" 2>&1 || true
fi
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k114-gnss-single-client-v3-private.tar.gz .
sha256sum /tmp/k114-gnss-single-client-v3-private.tar.gz
