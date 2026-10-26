#!/bin/bash
set -euo pipefail
work=/home/cy122/x2pro-linux/wifi-tools-k91
out=/mnt/e/edk2-samurai-out/kernel91
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel91'
cd "$work"
test ! -e "$out/wpa_supplicant"
printf '%s\n' '08e23937e16d0155e55cab2b51f51fbe10d80a1aa91c4e15442645059b737ef6  wpa_supplicant-2.12.tar.gz' '603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a  openssl-3.5.9.tar.gz' | sha256sum -c -
sha256sum -c openssl-3.5.9.tar.gz.sha256
mkdir -m 700 -p gpg-verify
gpg --homedir "$work/gpg-verify" --batch --import openssl-pubkeys.asc > "$out/openssl-key-import.txt" 2>&1
gpg --homedir "$work/gpg-verify" --batch --status-fd 1 --verify openssl-3.5.9.tar.gz.asc openssl-3.5.9.tar.gz > "$out/openssl-signature.txt" 2>&1
grep '^\[GNUPG:\] VALIDSIG ' "$out/openssl-signature.txt" | grep -q 'B146647E45A7B33947AB226B2A2C87D161692D40'
test ! -e openssl-3.5.9
tar xzf openssl-3.5.9.tar.gz
cd openssl-3.5.9
./Configure linux-aarch64 --cross-compile-prefix=aarch64-linux-gnu- no-shared no-tests no-module no-dso no-engine no-async > "$out/openssl-configure.txt" 2>&1
make -j8 build_libs > "$out/openssl-build.txt" 2>&1
cd "$work/wpa_supplicant-2.12/wpa_supplicant"
test ! -e .config
cp "$ref/wpa-build.config" .config
export LD_LIBRARY_PATH=/mnt/e/edk2-samurai-out/kernel90/pkgconf/usr/lib/x86_64-linux-gnu
export PKG_CONFIG_LIBDIR=/home/cy122/x2pro-linux/wifi-tools-k90/install/lib/pkgconfig
make -j8 CC=aarch64-linux-gnu-gcc PKG_CONFIG='/mnt/e/edk2-samurai-out/kernel90/pkgconf/usr/bin/pkgconf --static' LDFLAGS=-static > "$out/wpa-build.txt" 2>&1
for binary in wpa_supplicant wpa_cli wpa_passphrase; do
    if aarch64-linux-gnu-readelf -l "$binary" | grep -q INTERP; then exit 1; fi
    aarch64-linux-gnu-strip "$binary"
    cp "$binary" "$out/$binary"
    file "$out/$binary"
done
cp "$work/wpa_supplicant-2.12.tar.gz" "$work/openssl-3.5.9.tar.gz" "$out/"
sha256sum "$out/wpa_supplicant" "$out/wpa_cli" "$out/wpa_passphrase" "$out/wpa_supplicant-2.12.tar.gz" "$out/openssl-3.5.9.tar.gz" > "$out/wpa-hashes.txt"
cat "$out/wpa-hashes.txt"
