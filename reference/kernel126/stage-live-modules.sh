#!/bin/sh
set -eu
umask 077
release=7.3.0-rc6-rmx1931-samurai-k126+
old_release=7.3.0-rc6-rmx1931-samurai+
dest=/var/lib/samurai/k126-preflash
uname -v | grep -q '^#118 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -d "/lib/modules/$old_release"
test ! -e "/usr/lib/modules/$release"
test ! -e "$dest/staging-receipt"
test "$(sha256sum /tmp/modules-k126-private.tar.gz | cut -d' ' -f1)" = 62bfd60937b992d0f59063d70bd7b40f4cfa73668d7b894641f289e734753510
test "$(sha256sum /tmp/bluetooth-script-k126-private | cut -d' ' -f1)" = 104159825484fafc3ab5cacac368a9b7a8a38bc209c509207e73d1be00102319
cmp /usr/sbin/samurai-bluetooth "$dest/bluetooth-script-before"
sha256sum -c "$dest/ipa-module.sha256" > /tmp/k126-ipa-before-check.txt
live_script=$(readlink -f /usr/sbin/samurai-bluetooth)
case "$live_script" in /usr/bin/samurai-bluetooth|/usr/sbin/samurai-bluetooth) ;; *) echo unexpected_bluetooth_script_target >&2; exit 1;; esac
mkdir /run/samurai-k126-stage.lock
trap 'rmdir /run/samurai-k126-stage.lock' EXIT HUP INT TERM
stage=$(mktemp -d /var/lib/samurai/k126-module-stage.XXXXXX)
tar -xzf /tmp/modules-k126-private.tar.gz -C "$stage"
new="$stage/lib/modules/$release"
test "$(find "$new" -type f -name '*.ko' | wc -l)" = 770
test -z "$(find "$new" -type l)"
test "$(sha256sum "$new/kernel/drivers/net/ipa/ipa.ko" | cut -d' ' -f1)" = 979975a67b2af59c5487f26f1d66ab84beb8374f74db4d75740eb3a362016ad3
mv "$new" "/usr/lib/modules/$release"
cp /tmp/bluetooth-script-k126-private "$live_script.k126-new"
chmod 0755 "$live_script.k126-new"
chown 0:0 "$live_script.k126-new"
mv "$live_script.k126-new" "$live_script"
test "$(sha256sum "$live_script" | cut -d' ' -f1)" = 104159825484fafc3ab5cacac368a9b7a8a38bc209c509207e73d1be00102319
test -d "/lib/modules/$old_release"
sha256sum -c "$dest/ipa-module.sha256" > "$dest/old-ipa-still-exact.txt"
(cd "/usr/lib/modules/$release" && find . -type f -exec sha256sum '{}' ';') > "$dest/new-module-tree.sha256"
printf '%s\n' "$release" > "$dest/new-release.txt"
sha256sum "$live_script" > "$dest/new-bluetooth-script.sha256"
cat /proc/sys/kernel/random/boot_id > "$dest/staging-boot-id-private.txt"
printf 'OLD118_MODULE_DIRECTORY_PRESERVED\nNEW126_770_MODULES_STAGED_NO_LOAD\nBLUETOOTH_RELEASE_PATH_INSTALLED\n' > "$dest/staging-receipt"
sync
tar -C "$dest" -cf /tmp/k126-staging-receipt.tar new-module-tree.sha256 new-release.txt new-bluetooth-script.sha256 staging-boot-id-private.txt staging-receipt old-ipa-still-exact.txt
echo K126_DISTINCT_MODULES_STAGED_OLD118_PRESERVED_NO_NEW_MODULE_LOAD
