#!/bin/bash
set -euo pipefail
umask 077
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py'
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=121
cd /home/cy122/pmos-samurai-kernel118/camera121/kernel
out=/mnt/e/edk2-samurai-out/kernel121
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/config-build.log" 2>&1
grep -qx CONFIG_MFD_QCOM_PM8008=m .config
grep -qx CONFIG_REGULATOR_QCOM_PM8008=m .config
grep -qx CONFIG_VIDEO_QCOM_CAMSS=m .config
grep -qx CONFIG_I2C_QCOM_CCI=m .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image modules qcom/sm8150-samurai.dtb > "$out/kernel-full-build.log" 2>&1
test -s drivers/mfd/qcom-pm8008.ko
test -s arch/arm64/boot/Image
echo KERNEL121_FULL_IMAGE_MODULES_PMIC_DTB_BUILD_PASS_NOT_DEPLOYED
