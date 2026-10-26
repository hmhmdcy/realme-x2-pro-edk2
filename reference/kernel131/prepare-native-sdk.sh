#!/bin/sh
set -eu
umask 077
work=/tmp/k131-native-sdk
dest=/var/lib/samurai/k131-native-build
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k130-warmboot-r2/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test ! -e "$work"
test ! -e "$dest"
test "$(sha256sum /var/lib/samurai/k131-native-sdk-inputs.tar | cut -d ' ' -f1)" = b5808e31feceeb305c50a0747198bac829e8fe66301ccadcd2d1e556de1c7116
mkdir -m700 "$work" "$dest" "$work/inputs" "$work/sdk"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
sha256sum /etc/apk/world /lib/apk/db/installed > "$dest/package-db-before.sha256"
tar -xf /var/lib/samurai/k131-native-sdk-inputs.tar -C "$work/inputs"
cp /var/lib/samurai/k131-native-musl.apk "$work/inputs/musl.apk"
cp /var/lib/samurai/k131-native-libgcc-static.apk "$work/inputs/libgcc-static.apk"
for input in "$work"/inputs/*.apk; do
 apk verify "$input" >> "$dest/apk-signatures-private.txt" 2>&1
 apk extract --destination "$work/sdk" "$input" >> "$dest/sdk-extract-private.txt" 2>&1
done
test "$(sha256sum "$work/inputs/glmark2-2023.01.tar.gz" | cut -d ' ' -f1)" = 8fece3fc323b643644a525be163dc4931a4189971eda1de8ad4c1712c5db3d67
tar -xzf "$work/inputs/glmark2-2023.01.tar.gz" -C "$work"
sha256sum -c "$dest/package-db-before.sha256" > "$dest/package-db-extract-check.txt"
chown -R 10000:10000 "$work"
echo PRIVATE_SIGNED_NATIVE_SDK_EXTRACTED_WITHOUT_PACKAGE_INSTALL
