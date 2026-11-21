#!/bin/sh
set -eu

SOURCE=/home/cy122/charging-management-20261023/charging-integration-20261026-01/source
BUILD=/home/cy122/charging-management-20261023/charging-integration-20261026-01/build
SOURCE_IN="/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/usb-input-irq-wake-r8-candidate/source"
OUT=/home/cy122/charging-management-20261023/usb-input-irq-wake-r8-module-01

test ! -e "$OUT"
mkdir -p "$OUT/module"
cp "$SOURCE_IN/Makefile" "$SOURCE_IN/samurai-usb-input.c" \
    "$SOURCE_IN/samurai-usb-input-decode.h" "$OUT/module/"

export PATH="/home/cy122/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin:/home/cy122/.cargo/bin:$PATH"
export KBUILD_BUILD_USER=builder
export KBUILD_BUILD_HOST=samurai
export KBUILD_BUILD_VERSION=517
export TMPDIR="$OUT"

make -C "$SOURCE" O="$BUILD" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
    LOCALVERSION=+ W=1 KCFLAGS=-Werror -j4 M="$OUT/module" modules \
    >"$OUT/build.log" 2>&1
tail -n 80 "$OUT/build.log"
test -f "$OUT/module/samurai-usb-input.ko"
sha256sum "$OUT/module/samurai-usb-input.ko"
