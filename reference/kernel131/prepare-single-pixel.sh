#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k131-single-pixel
work=/tmp/k131-glmark2
source=/var/lib/samurai/k119-benchmark-source/glmark2-2023.01-r1.apk
uname -v | grep -q '^#129 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k130-warmboot-r2/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test ! -e "$dest"
test ! -e "$work"
test -f "$source"
test "$(sha256sum "$source" | cut -d ' ' -f1)" = f440c872d9d49faf5f463d73eba3eb325d3545d22dc540e94b122105bb01c681
mkdir -m700 "$dest" "$work"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
sha256sum /etc/apk/world /lib/apk/db/installed > "$dest/package-db-before.sha256"
apk verify "$source" > "$dest/apk-signature.txt" 2>&1
apk extract --destination "$work" "$source" > "$dest/extract-private.txt" 2>&1
test -f "$work/usr/bin/glmark2-es2-wayland"
test ! -L "$work/usr/bin/glmark2-es2-wayland"
chown -R 10000:10000 "$work"
sha256sum "$work/usr/bin/glmark2-es2-wayland" > "$dest/binary.sha256"
timeout -k 2 5 su -s /bin/sh cy122 -c '/tmp/k131-glmark2/usr/bin/glmark2-es2-wayland --help' > "$dest/help.txt" 2>&1
sha256sum -c "$dest/package-db-before.sha256" > "$dest/package-db-prepared-check.txt"
cat /sys/class/devcoredump/disabled > "$dest/devcoredump-disabled.txt"
echo K131_SIGNED_SINGLE_SCENE_TOOL_READY_NO_PACKAGE_INSTALL
