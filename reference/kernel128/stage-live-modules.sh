#!/bin/sh
set -eu
umask 077
test "$#" = 1
archive_hash=$1
release=7.3.0-rc6-rmx1931-samurai-k128+
old_release=7.3.0-rc6-rmx1931-samurai-k126+
dest=/var/lib/samurai/k128-preflash
test "$(uname -r)" = "$old_release"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
test ! -e "/usr/lib/modules/$release"
test ! -e "$dest/staging-receipt"
test "$(sha256sum /tmp/modules-k128-private.tar.gz | cut -d' ' -f1)" = "$archive_hash"
sha256sum -c "$dest/bluetooth-script.sha256" > "$dest/bt-script-still-exact.txt"
sha256sum -c "$dest/old118-ipa.sha256" > "$dest/old118-ipa-still-exact.txt"
(cd "/usr/lib/modules/$old_release" && sha256sum -c "$dest/old126-module-tree.sha256") > "$dest/old126-still-exact.txt"
mkdir /run/samurai-k128-stage.lock
trap 'rmdir /run/samurai-k128-stage.lock' EXIT HUP INT TERM
stage=$(mktemp -d /var/lib/samurai/k128-module-stage.XXXXXX)
tar -xzf /tmp/modules-k128-private.tar.gz -C "$stage"
new="$stage/lib/modules/$release"
test "$(find "$new" -type f -name '*.ko' | wc -l)" = 770
test -z "$(find "$new" -type l)"
(cd "$new" && sha256sum -c /tmp/k128-module-tree.sha256) > "$dest/new-module-check.txt"
mv "$new" "/usr/lib/modules/$release"
cp /tmp/k128-module-tree.sha256 "$dest/new-module-tree.sha256"
printf '%s\n' "$release" > "$dest/new-release.txt"
cat /proc/sys/kernel/random/boot_id > "$dest/staging-boot-id-private.txt"
printf 'OLD118_AND126_MODULE_DIRECTORIES_PRESERVED\nNEW128_770_MODULES_STAGED_NO_LOAD\n' > "$dest/staging-receipt"
sync
tar -C "$dest" -czf /tmp/k128-staging-private.tar.gz new-module-tree.sha256 new-release.txt new-module-check.txt staging-boot-id-private.txt staging-receipt old118-ipa-still-exact.txt old126-still-exact.txt bt-script-still-exact.txt
echo K128_MATCHING_MODULES_STAGED_OLD118_126_PRESERVED_NO_NEW_LOAD
