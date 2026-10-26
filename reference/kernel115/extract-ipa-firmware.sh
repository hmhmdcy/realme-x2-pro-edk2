#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k115-ipa-firmware-source
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k114-final-health/boot-id-private.txt)"
mkdir -m700 "$dest"
node=
for sys in /sys/class/block/*; do
    test -f "$sys/uevent" || continue
    grep -qx PARTNAME=modem "$sys/uevent" || continue
    test "$(cat "$sys/size")" = 524288
    test -z "$node"
    node=/dev/${sys##*/}
done
test -n "$node"
sha256sum "$node" > "$dest/modem-before.sha256"
mountpoint=/run/k115-modem-readonly
test ! -e "$mountpoint"
mkdir -m700 "$mountpoint"
mount -t vfat -o ro "$node" "$mountpoint"
cleanup() { umount "$mountpoint" || true; }
trap cleanup EXIT
mkdir -m700 "$dest/firmware"
for file in "$mountpoint"/image/ipa_fws.*; do
    test -f "$file"
    cp -p "$file" "$dest/firmware/"
done
test -f "$dest/firmware/ipa_fws.mdt"
(cd "$dest/firmware" && sha256sum *) > "$dest/firmware.sha256"
umount "$mountpoint"
trap - EXIT
sha256sum -c "$dest/modem-before.sha256" > "$dest/modem-after-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k115-ipa-firmware-source-private.tar.gz .
sha256sum /tmp/k115-ipa-firmware-source-private.tar.gz
echo SAME_HANDSET_IPA_FIRMWARE_EXTRACTED_READONLY
