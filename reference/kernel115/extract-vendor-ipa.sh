#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k115-vendor-ipa-source
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k114-final-health/boot-id-private.txt)"
node=
for attrs in /sys/class/block/sd*/uevent; do
    grep -qx PARTNAME=vendor "$attrs" || continue
    test -z "$node"
    sys=${attrs%/uevent}
    test "$(cat "$sys/size")" = 3342336
    node=/dev/${sys##*/}
done
test -n "$node"
mkdir -m700 "$dest"
sha256sum "$node" > "$dest/vendor-before.sha256"
mp=/run/k115-vendor-readonly
test ! -e "$mp"
mkdir -m700 "$mp"
mount -t ext4 -o ro,noload,nosuid,nodev,noexec "$node" "$mp"
cleanup() { umount "$mp" || true; }
trap cleanup EXIT
find "$mp" -iname '*ipa*' -o -iname '*gsi*' > "$dest/matching-paths-private.txt"
mkdir -m700 "$dest/firmware"
for file in "$mp"/firmware/ipa_fws.*; do
    test -f "$file"
    test ! -L "$file"
    cp -p "$file" "$dest/firmware/"
done
test -s "$dest/firmware/ipa_fws.mdt"
(cd "$dest/firmware" && sha256sum *) > "$dest/firmware.sha256"
umount "$mp"
trap - EXIT
sha256sum -c "$dest/vendor-before.sha256" > "$dest/vendor-after-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k115-vendor-ipa-source-private.tar.gz .
sha256sum /tmp/k115-vendor-ipa-source-private.tar.gz
echo SAME_HANDSET_VENDOR_IPA_FIRMWARE_EXTRACTED_READONLY
