#!/bin/bash
set -euo pipefail
umask 077
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=116
cd /home/cy122/pmos-samurai-kernel116/kernel
out=/mnt/e/edk2-samurai-out/kernel116
scripts/config --enable MEDIA_SUPPORT --enable MEDIA_CAMERA_SUPPORT --enable MEDIA_PLATFORM_SUPPORT --enable V4L_PLATFORM_DRIVERS --enable VIDEO_DEV --module VIDEO_QCOM_CAMSS
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/camss-config.log" 2>&1
grep -qx CONFIG_VIDEO_QCOM_CAMSS=m .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 drivers/media/platform/qcom/camss/ > "$out/camss-targeted-build.log" 2>&1
test -s drivers/media/platform/qcom/camss/qcom-camss.o
echo KERNEL116_CAMSS_TARGET_OBJECT_BUILD_PASS_HARDWARE_DISABLED
