#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#115 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-first-runtime/boot-id-private.txt)"
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
test -z "$(pgrep -u 10000 || true)"
test -f /var/lib/samurai/k115-delay-fix-quiesce/SHA256SUMS
dest=/var/lib/samurai/k115-delay-fix-install
test ! -e "$dest"
mkdir -m700 "$dest"
echo 'bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0  /tmp/k115-ipa-delay-fixed.ko' | sha256sum -c - > "$dest/package-check.txt"
module=/lib/modules/7.3.0-rc6-rmx1931-samurai+/kernel/drivers/net/ipa/ipa.ko
cp -p "$module" "$dest/ipa-before.ko"
cp -p /tmp/k115-ipa-delay-fixed.ko "$module"
cmp /tmp/k115-ipa-delay-fixed.ko "$module"
depmod 7.3.0-rc6-rmx1931-samurai+
sha256sum "$module" > "$dest/installed.sha256"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sync
echo IPA_DELAY_FIX_INSTALLED_FOR_NEXT_NORMAL_BOOT
