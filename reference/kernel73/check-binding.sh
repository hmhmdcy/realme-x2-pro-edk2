#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
export PATH="/home/cy122/x2pro-linux/.venv-dtschema/bin:$PATH"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- DT_SCHEMA_FILES=display/panel/samsung,sofef03f-m.yaml CHECK_DTBS=y qcom/sm8150-samurai.dtb > /mnt/e/edk2-samurai-out/kernel73/dtbs-check.log 2>&1
tail -10 /mnt/e/edk2-samurai-out/kernel73/dtbs-check.log
