#!/bin/bash
set -euo pipefail
umask 077
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel126/ensure-build-volume.py'
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=126
cd /home/cy122/pmos-samurai-build126/kernel
out=/mnt/e/edk2-samurai-out/kernel126
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/config-build.log" 2>&1
grep -qx CONFIG_VIDEO_QCOM_CAMSS=m .config
grep -qx CONFIG_I2C_QCOM_CCI=m .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image modules qcom/sm8150-samurai.dtb > "$out/kernel-full-build.log" 2>&1
test -s arch/arm64/boot/Image
test -s drivers/media/platform/qcom/camss/qcom-camss.ko
echo KERNEL126_FULL_IMAGE_CAMSS_MODULES_DTB_BUILD_PASS_NOT_DEPLOYED
