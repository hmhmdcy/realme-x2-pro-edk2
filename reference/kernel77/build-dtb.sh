#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel77
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- qcom/sm8150-samurai.dtb > "$out/dtb-build.log" 2>&1
cmp .config "$out/config-before"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/firmware-after.dtb"
tail -8 "$out/dtb-build.log"
