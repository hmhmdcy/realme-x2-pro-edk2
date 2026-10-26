#!/bin/bash
set -euo pipefail
out=${1:?Usage: build-dropbear-usb.sh OUTPUT_DIRECTORY}
src=/home/cy122/x2pro-linux/refs/dropbear
version=2026.94
source_sha=e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81
mkdir -p "$src" "$out"
cd "$src"
if [ ! -f "dropbear-$version.tar.bz2" ]; then
    curl --fail --location --retry 2 --max-time 60 \
        -o "dropbear-$version.tar.bz2" \
        "https://matt.ucc.asn.au/dropbear/releases/dropbear-$version.tar.bz2"
fi
echo "$source_sha  dropbear-$version.tar.bz2" | sha256sum -c -
if [ ! -d "dropbear-$version" ]; then tar xf "dropbear-$version.tar.bz2"; fi
cd "dropbear-$version"
cat >localoptions.h <<'EOF'
/* The direct USB bring-up server accepts public keys only. */
#define DROPBEAR_SVR_PASSWORD_AUTH 0
EOF
./configure --host=aarch64-linux-gnu --disable-zlib --enable-static \
    --disable-lastlog --disable-utmp --disable-wtmp --disable-utmpx --disable-wtmpx \
    >"$out/dropbear-configure.log" 2>&1
make clean >"$out/dropbear-clean.log" 2>&1
make -j12 PROGRAMS="dropbear dropbearkey scp" MULTI=1 \
    >"$out/dropbear-build.log" 2>&1
aarch64-linux-gnu-strip dropbearmulti
cp dropbearmulti "$out/dropbearmulti"
cp localoptions.h "$out/dropbear-localoptions.h"
file dropbearmulti
sha256sum dropbearmulti "../dropbear-$version.tar.bz2" >"$out/dropbear-hashes.txt"
cat "$out/dropbear-hashes.txt"
