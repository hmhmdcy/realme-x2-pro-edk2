#!/bin/bash
set -euo pipefail
umask 077
k=/home/cy122/pmos-samurai-kernel115/kernel
out=/mnt/e/edk2-samurai-out/kernel115
pkg=/home/cy122/pmos-samurai-kernel115/runtime-package
test ! -e "$pkg"
mkdir "$pkg"
make -C "$k" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- INSTALL_MOD_PATH="$pkg" INSTALL_MOD_STRIP=1 modules_install > "$out/modules-install.log" 2>&1
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel115/finalize-module-package.py'
echo KERNEL115_COMPLETE_MODULE_TREE_AND_OWN_IPA_FIRMWARE_PACKAGE_READY
