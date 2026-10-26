#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
trace_out=/mnt/e/edk2-samurai-out/kernel84
test -f "$trace_out/preserved-private-manifest.json"
test ! -e "$trace_out/Image-trace"
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KBUILD_BUILD_VERSION=84 Image >"$trace_out/build-trace.log" 2>&1
cmp .config "$trace_out/config-trace"
cmp usr/initramfs_data.cpio "$trace_out/cpio-before"
cp arch/arm64/boot/Image "$trace_out/Image-trace"
test ! -e "$trace_out/logdump-k84-trace.img"
cp "$trace_out/logdump-before.img" "$trace_out/logdump-k84-trace.img"
mcopy -o -i "$trace_out/logdump-k84-trace.img" arch/arm64/boot/Image ::Image
cmp arch/arm64/boot/Image <(mcopy -i "$trace_out/logdump-k84-trace.img" ::Image -)
sha256sum "$trace_out/Image-trace" "$trace_out/logdump-k84-trace.img" .config >"$trace_out/build-hashes.txt"
tail -n 10 "$trace_out/build-trace.log"
