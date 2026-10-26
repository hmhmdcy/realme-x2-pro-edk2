#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
trace_out=/mnt/e/edk2-samurai-out/kernel84
test -f "$trace_out/initial-raw.tar"
test ! -e "$trace_out/Image-ready"
scripts/config --enable HIST_TRIGGERS --set-str BOOT_CONFIG_EMBED_FILE "$trace_out/display-bootconfig-ready.txt"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >"$trace_out/olddefconfig-ready.log" 2>&1
cp .config "$trace_out/config-ready"
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KBUILD_BUILD_VERSION=85 Image >"$trace_out/build-ready.log" 2>&1
cmp .config "$trace_out/config-ready"
cmp usr/initramfs_data.cpio "$trace_out/cpio-before"
cp arch/arm64/boot/Image "$trace_out/Image-ready"
test ! -e "$trace_out/logdump-k84-ready.img"
cp "$trace_out/logdump-before.img" "$trace_out/logdump-k84-ready.img"
mcopy -o -i "$trace_out/logdump-k84-ready.img" arch/arm64/boot/Image ::Image
cmp arch/arm64/boot/Image <(mcopy -i "$trace_out/logdump-k84-ready.img" ::Image -)
sha256sum "$trace_out/Image-ready" "$trace_out/logdump-k84-ready.img" .config >"$trace_out/build-ready-hashes.txt"
tail -n 10 "$trace_out/build-ready.log"
