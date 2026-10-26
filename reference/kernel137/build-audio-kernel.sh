#!/bin/bash
set -euo pipefail
umask 077
stage=/home/cy122/pmos-samurai-kernel136
out=/mnt/e/edk2-samurai-out/kernel137
test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel137/audio-source-validation.json'
test ! -e "$out/audio-image-build-private.log"
cd "$stage/kernel"
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=137
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/audio-config-build-private.log" 2>&1
grep -qx 'CONFIG_LOCALVERSION="-rmx1931-samurai-k132"' .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- W=1 -j8 drivers/mfd/wcd934x.o drivers/slimbus/qcom-ngd-ctrl.o drivers/dma/qcom/bam_dma.o > "$out/audio-objects-build-private.log" 2>&1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image modules qcom/sm8150-samurai.dtb > "$out/audio-image-build-private.log" 2>&1
mkdir -m700 "$stage/modules-root137"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- INSTALL_MOD_PATH="$stage/modules-root137" INSTALL_MOD_STRIP=1 modules_install > "$out/audio-modules-install-private.log" 2>&1
release=$(cat include/config/kernel.release)
test "$release" = 7.3.0-rc6-rmx1931-samurai-k132+
unlink "$stage/modules-root137/lib/modules/$release/build"
depmod -e -F System.map -b "$stage/modules-root137" "$release" > "$out/audio-depmod-private.log" 2>&1
test ! -s "$out/audio-depmod-private.log"
echo K137_IMAGE_MODULES_DTB_BUILD_COMPLETE_RELEASE132_PRESERVED
