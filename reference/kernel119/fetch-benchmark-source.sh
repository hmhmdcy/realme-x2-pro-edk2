#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k119-benchmark-source
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k119-first-runtime/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
sha256sum /etc/apk/world /lib/apk/db/installed > "$dest/package-db-before.sha256"
apk policy glmark2 > "$dest/policy.txt"
apk fetch --url glmark2 > "$dest/source-url.txt"
test "$(cat "$dest/source-url.txt")" = https://dl-cdn.alpinelinux.org/alpine/edge/testing/aarch64/glmark2-2023.01-r1.apk
timeout -s TERM -k 2 60 apk fetch --output "$dest" glmark2 > "$dest/fetch.txt" 2>&1
test -s "$dest/glmark2-2023.01-r1.apk"
apk verify "$dest/glmark2-2023.01-r1.apk" > "$dest/signature-verify.txt" 2>&1
sha256sum -c "$dest/package-db-before.sha256" > "$dest/package-db-after-check.txt"
sha256sum "$dest/glmark2-2023.01-r1.apk" > "$dest/package.sha256"
apk extract --help > "$dest/extract-help.txt"
echo SIGNED_BENCHMARK_SOURCE_FETCHED_NO_INSTALL_OR_EXECUTION
