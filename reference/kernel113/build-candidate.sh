#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel113
cd /home/cy122/pmos-samurai-kernel113/kernel
test ! -e "$out/Image-sensor-power"
export KBUILD_BUILD_VERSION=113
export PATH=/home/cy122/.cargo/bin:$PATH
export RUSTUP_HOME=/home/cy122/.rustup
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
grep -qx CONFIG_SAMURAI_SENSOR_POWER=y .config
make -j8 W=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- drivers/misc/samurai-sensor-power.o > "$out/sensor-power-build-w1.log" 2>&1
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-sensor-power"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-sensor-power"
cp usr/initramfs_data.cpio "$out/cpio-sensor-power"
cp .config "$out/config-after"
sha256sum "$out/Image-sensor-power" "$out/dtb-sensor-power" "$out/cpio-sensor-power" > "$out/kernel-candidate.sha256"
echo KERNEL113_MANUAL_SENSOR_POWER_BUILD_COMPLETE
