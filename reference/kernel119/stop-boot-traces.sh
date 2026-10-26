#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k119-boot-traces
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k119-first-runtime/boot-id-private.txt)"
mkdir -m700 "$dest"
for name in display radio; do
    instance=/sys/kernel/tracing/instances/$name
    test -d "$instance"
    cat "$instance/tracing_on" > "$dest/$name-before.txt"
    echo 0 > "$instance/tracing_on"
    cat "$instance/trace" > "$dest/$name-trace-private.txt"
    test "$(cat "$instance/tracing_on")" = 0
done
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
dmesg > "$dest/dmesg-private.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k119-boot-traces-private.tar.gz .
sha256sum /tmp/k119-boot-traces-private.tar.gz
echo BOOT_TRACES_PRESERVED_AND_STOPPED
