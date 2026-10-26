#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k114-final-health/boot-id-private.txt)"
dest=/var/lib/samurai/k115-runtime-stage
test -d "$dest"
test ! -e "$dest/installed"
echo '4ba1f89ab386e8c749cc2cb5d193e4a553b4e47bd480db9a591e6d21f845089e  /tmp/k115-runtime-package-private.tar.gz' | sha256sum -c -
(cd "$dest" && sha256sum -c SHA256SUMS) > "$dest/package-check.txt"
version=7.3.0-rc6-rmx1931-samurai+
test ! -e "/lib/modules/$version"
test -d /lib/modules/samurai
cp -a /lib/modules/samurai "$dest/rollback-modules-samurai"
cp -a /etc/init.d/elogind /etc/init.d/postmarketos-zram-swap "$dest/"
mkdir "$dest/rollback-firmware"
for src in "$dest"/lib/firmware/qcom/sm8150/realme/samurai/*; do
    target=/lib/firmware/qcom/sm8150/realme/samurai/${src##*/}
    if test -e "$target"; then cp -p "$target" "$dest/rollback-firmware/"; fi
    cp -p "$src" "$target"
done
# Install the complete tree after preserving the current runtime modules.
cp -a "$dest/lib/modules/$version" "/lib/modules/$version"
depmod "$version"
modinfo ipa > "$dest/ipa-module.txt"
modinfo zram > "$dest/zram-module.txt"
test ! -e /sys/module/ipa
test ! -e /sys/module/zram
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sync
touch "$dest/installed"
echo KERNEL115_RUNTIME_PACKAGE_STAGED_WITH_KERNEL113_ROLLBACK
