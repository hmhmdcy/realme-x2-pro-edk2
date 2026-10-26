#!/bin/sh
set -eu
umask 077
source_dir=/var/lib/samurai/k119-benchmark-source
dest=/var/lib/samurai/k119-pixel-validation
work=/tmp/k119-glmark2
test ! -e "$dest"
test ! -e "$work"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$source_dir/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(id -u cy122)" = 10000
mkdir -m700 "$dest" "$work"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
apk verify "$source_dir/glmark2-2023.01-r1.apk" > "$dest/signature-verify.txt" 2>&1
apk extract --destination "$work" "$source_dir/glmark2-2023.01-r1.apk" > "$dest/extract.txt" 2>&1
test -f "$work/usr/bin/glmark2-es2-wayland"
test ! -L "$work/usr/bin/glmark2-es2-wayland"
chown -R 10000:10000 "$work"
sha256sum "$work/usr/bin/glmark2-es2-wayland" > "$dest/binary.sha256"
timeout -s TERM -k 2 5 su -s /bin/sh cy122 -c '/tmp/k119-glmark2/usr/bin/glmark2-es2-wayland --help' > "$dest/help.txt" 2>&1
sha256sum -c "$source_dir/package-db-before.sha256" > "$dest/package-db-check.txt"
echo NONROOT_PIXEL_VALIDATION_TOOL_READY_NO_PACKAGE_INSTALL
