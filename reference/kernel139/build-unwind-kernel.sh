#!/bin/bash
set -euo pipefail
umask 077
stage=/home/cy122/pmos-samurai-kernel136
out=/mnt/e/edk2-samurai-out/kernel139
test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel139/host-fault-injection-validation.json'
test ! -e "$out/unwind-image-build-private.log"
cd "$stage/kernel"
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=139
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/unwind-config-build-private.log" 2>&1
grep -qx 'CONFIG_LOCALVERSION="-rmx1931-samurai-k132"' .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- W=1 -j8 drivers/slimbus/qcom-ngd-ctrl.o drivers/slimbus/messaging.o > "$out/unwind-objects-build-private.log" 2>&1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image modules qcom/sm8150-samurai.dtb > "$out/unwind-image-build-private.log" 2>&1
mkdir -m700 "$stage/modules-root139"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- INSTALL_MOD_PATH="$stage/modules-root139" INSTALL_MOD_STRIP=1 modules_install > "$out/unwind-modules-install-private.log" 2>&1
release=$(cat include/config/kernel.release)
test "$release" = 7.3.0-rc6-rmx1931-samurai-k132+
unlink "$stage/modules-root139/lib/modules/$release/build"
depmod -e -F System.map -b "$stage/modules-root139" "$release" > "$out/unwind-depmod-private.log" 2>&1
test ! -s "$out/unwind-depmod-private.log"
echo K139_IMAGE_MODULES_DTB_BUILD_COMPLETE_RELEASE132_PRESERVED
