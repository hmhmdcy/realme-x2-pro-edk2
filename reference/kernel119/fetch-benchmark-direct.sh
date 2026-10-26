#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k119-benchmark-source
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test ! -e "$dest/glmark2-2023.01-r1.apk"
test ! -e "$dest/source-url-direct.txt"
printf '%s\n' https://dl-cdn.alpinelinux.org/alpine/edge/testing/aarch64/glmark2-2023.01-r1.apk > "$dest/source-url-direct.txt"
timeout -s TERM -k 2 60 wget -O "$dest/glmark2-2023.01-r1.apk" "$(cat "$dest/source-url-direct.txt")" > "$dest/fetch-direct.txt" 2>&1
apk verify "$dest/glmark2-2023.01-r1.apk" > "$dest/signature-verify.txt" 2>&1
sha256sum -c "$dest/package-db-before.sha256" > "$dest/package-db-after-check.txt"
sha256sum "$dest/glmark2-2023.01-r1.apk" > "$dest/package.sha256"
apk extract --help > "$dest/extract-help.txt"
cd "$dest"
find . -type f ! -name SHA256SUMS -exec sha256sum {} \; > SHA256SUMS
tar -czf /tmp/k119-benchmark-source-private.tar.gz .
echo SIGNED_BENCHMARK_SOURCE_FETCHED_NO_INSTALL_OR_EXECUTION
