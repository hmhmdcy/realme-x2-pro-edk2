#!/bin/bash
set -euo pipefail
umask 077
stage=/home/cy122/pmos-samurai-kernel136
out=/mnt/e/edk2-samurai-out/kernel143
test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel143/source-validation.json'
test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel143/actual-function-test-validation.json'
test ! -e "$out/threaded-console-image-build-private.log"
test ! -e "$stage/modules-root143"
cd "$stage/kernel"
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=143
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/threaded-console-config-build-private.log" 2>&1
grep -qx 'CONFIG_LOCALVERSION="-rmx1931-samurai-k132"' .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- W=1 -j8 drivers/tty/serial/eud.o > "$out/threaded-console-objects-build-private.log" 2>&1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image modules qcom/sm8150-samurai.dtb > "$out/threaded-console-image-build-private.log" 2>&1
mkdir -m700 "$stage/modules-root143"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- INSTALL_MOD_PATH="$stage/modules-root143" INSTALL_MOD_STRIP=1 modules_install > "$out/threaded-console-modules-install-private.log" 2>&1
release=$(cat include/config/kernel.release)
test "$release" = 7.3.0-rc6-rmx1931-samurai-k132+
unlink "$stage/modules-root143/lib/modules/$release/build"
depmod -e -F System.map -b "$stage/modules-root143" "$release" > "$out/threaded-console-depmod-private.log" 2>&1
test ! -s "$out/threaded-console-depmod-private.log"
echo K143_THREADED_CONSOLE_IMAGE_MODULES_DTB_BUILD_COMPLETE_RELEASE132
