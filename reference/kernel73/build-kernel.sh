#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel73
scripts/config --enable QCOM_LLCC --disable QCOM_OCMEM --enable BACKLIGHT_CLASS_DEVICE \
    --enable DRM_MSM --enable DRM_MSM_DPU \
    --enable DRM_MSM_DSI --enable DRM_MSM_DSI_7NM_PHY \
    --enable DRM_PANEL_SAMSUNG_SOFEF03F --disable DRM_MSM_MDP4 \
    --disable DRM_MSM_MDP5 --disable DRM_MSM_DP --disable DRM_MSM_HDMI \
    --disable DRM_MSM_DSI_28NM_PHY --disable DRM_MSM_DSI_20NM_PHY \
    --disable DRM_MSM_DSI_28NM_8960_PHY --disable DRM_MSM_DSI_14NM_PHY \
    --disable DRM_MSM_DSI_10NM_PHY
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
grep -qx CONFIG_DRM_MSM=y .config
grep -qx CONFIG_DRM_PANEL_SAMSUNG_SOFEF03F=y .config
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-display"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/firmware-after.dtb"
cp .config "$out/config-display"
sha256sum arch/arm64/boot/Image arch/arm64/boot/dts/qcom/sm8150-samurai.dtb .config > "$out/build-hashes.txt"
tail -10 "$out/kernel-build.log"
