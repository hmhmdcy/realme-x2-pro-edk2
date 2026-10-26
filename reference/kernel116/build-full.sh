#!/bin/bash
set -euo pipefail
umask 077
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=116
cd /home/cy122/pmos-samurai-kernel116/kernel
out=/mnt/e/edk2-samurai-out/kernel116
grep -qx CONFIG_VIDEO_QCOM_CAMSS=m .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image modules qcom/sm8150-samurai.dtb > "$out/kernel-full-build.log" 2>&1
test -s drivers/media/platform/qcom/camss/qcom-camss.ko
test -s arch/arm64/boot/Image
echo KERNEL116_FULL_IMAGE_CAMSS_MODULES_DTB_BUILD_PASS_NOT_DEPLOYED
