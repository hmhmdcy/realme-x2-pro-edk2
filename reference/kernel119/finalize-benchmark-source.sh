#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k119-benchmark-source
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test -s "$dest/glmark2-2023.01-r1.apk"
apk verify "$dest/glmark2-2023.01-r1.apk" > "$dest/signature-final-verify.txt" 2>&1
sha256sum -c "$dest/package-db-before.sha256" > "$dest/package-db-final-check.txt"
test -s "$dest/extract-help.txt"
cd "$dest"
find . -type f ! -name SHA256SUMS -exec sha256sum {} \; > SHA256SUMS
tar -czf /tmp/k119-benchmark-source-private.tar.gz .
echo SIGNED_BENCHMARK_SOURCE_VERIFIED_ARCHIVED_NO_INSTALL_OR_EXECUTION
