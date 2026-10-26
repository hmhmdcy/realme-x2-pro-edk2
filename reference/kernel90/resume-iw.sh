#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel90
work=/home/cy122/x2pro-linux/wifi-tools-k90
test ! -e "$out/iw"
cd "$out"
for package_file in pkgconf-bin_*.deb libpkgconf7_*.deb; do dpkg-deb -x "$package_file" pkgconf; done
export LD_LIBRARY_PATH="$out/pkgconf/usr/lib/x86_64-linux-gnu"
export PKG_CONFIG="$out/pkgconf/usr/bin/pkgconf"
"$PKG_CONFIG" --version
cd "$work/libnl-3.12.0"
./configure --host=aarch64-linux-gnu --prefix="$work/install" --disable-shared --enable-static --disable-cli --disable-pthreads > "$out/libnl-configure-retry.log" 2>&1
make -j8 > "$out/libnl-build.log" 2>&1
make install > "$out/libnl-install.log" 2>&1
cd "$work/iw-6.17"
export PKG_CONFIG_LIBDIR="$work/install/lib/pkgconfig"
make -j8 CC=aarch64-linux-gnu-gcc PKG_CONFIG="$PKG_CONFIG --static" LDFLAGS=-static > "$out/iw-build.log" 2>&1
file iw
if aarch64-linux-gnu-readelf -l iw | grep -q INTERP; then exit 1; fi
cp iw "$out/iw"
sha256sum "$out/iw" "$out/libnl-3.12.0.tar.gz" "$out/iw-6.17.tar.xz" > "$out/iw-tools-hashes.txt"
cat "$out/iw-tools-hashes.txt"
