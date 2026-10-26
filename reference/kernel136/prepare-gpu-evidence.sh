#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k136-gpu-vm-evidence
work=/tmp/k136-gpu-tools
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k136-current132/boot-id-private.txt)"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k132+
test "$(cat /proc/sys/kernel/tainted)" = 0
test ! -e "$dest"
test ! -e "$work"
test "$(cat /sys/module/msm/parameters/vm_log_shift)" = 0
test "$(sha256sum /var/lib/samurai/k131-native-build/glmark2-es2-wayland-fixed | cut -d ' ' -f1)" = 0df9560877295140d00b0a3e7d7931598acf7958d7c63475d907dd107f4f7095
test "$(sha256sum /var/lib/samurai/k119-benchmark-source/glmark2-2023.01-r1.apk | cut -d ' ' -f1)" = f440c872d9d49faf5f463d73eba3eb325d3545d22dc540e94b122105bb01c681
mkdir -m700 "$dest" "$work"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
sha256sum /etc/apk/world /lib/apk/db/installed > "$dest/package-db-before.sha256"
apk verify /var/lib/samurai/k119-benchmark-source/glmark2-2023.01-r1.apk > "$dest/apk-signature-private.txt" 2>&1
apk extract --destination "$work" /var/lib/samurai/k119-benchmark-source/glmark2-2023.01-r1.apk > "$dest/apk-extract-private.txt" 2>&1
cp /var/lib/samurai/k131-native-build/glmark2-es2-wayland-fixed "$work/glmark2-es2-wayland-fixed"
cp /var/lib/samurai/k131-native-build/build-receipts.json "$dest/"
cp /var/lib/samurai/k131-native-build/fbo-size-only.patch "$dest/"
chmod 755 "$work/glmark2-es2-wayland-fixed"
chown -R 10000:10000 "$work"
sha256sum -c "$dest/package-db-before.sha256" > "$dest/package-db-prepared-check.txt"
echo K136_VERIFIED_EXISTING_FIXED_FBO_TOOL_PREPARED_NO_PACKAGE_CHANGE
