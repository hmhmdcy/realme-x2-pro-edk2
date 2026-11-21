#!/usr/bin/env bash
set -euo pipefail

root=/home/cy122/charging-management-20261023/charging-integration-20261026-01
log="$root/Image-build-r10.log"

cd "$root"
: >"$log"
make -C source O="$root/build" ARCH=arm64 \
    CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ W=1 -j4 \
    Image 2>&1 | tee "$log"

printf '%s\n' '--- kernel.release'
cat build/include/config/kernel.release
printf '%s\n' '--- utsrelease.h'
cat build/include/generated/utsrelease.h
printf '%s\n' '--- image'
sha256sum build/arch/arm64/boot/Image
stat -c '%s bytes %y' build/arch/arm64/boot/Image
