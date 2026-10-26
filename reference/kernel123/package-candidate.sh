#!/bin/bash
set -euo pipefail
umask 077
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py'
root=/home/cy122/pmos-samurai-rootfs122/camera123
cd "$root/kernel"
out=/mnt/e/edk2-samurai-out/kernel123
test ! -e "$root/modules-root"
mkdir -m700 "$root/modules-root"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- INSTALL_MOD_PATH="$root/modules-root" INSTALL_MOD_STRIP=1 modules_install > "$out/modules-install-private.txt" 2>&1
release=$(cat include/config/kernel.release)
test -f "$root/modules-root/lib/modules/$release/modules.dep"
test -e "$root/modules-root/lib/modules/$release/build"
rm "$root/modules-root/lib/modules/$release/build"
depmod -e -F System.map -b "$root/modules-root" "$release" > "$out/depmod-check-private.txt" 2>&1
test ! -s "$out/depmod-check-private.txt"
tar -C "$root/modules-root" -czf "$out/modules-k123-private.tar.gz" lib/modules
echo KERNEL123_MATCHING_MODULE_ARCHIVE_DEPMOD_PASS_NOT_DEPLOYED
