#!/bin/bash
set -euo pipefail
umask 077
export PATH="/home/cy122/.cargo/bin:$PATH"
cd /home/cy122/pmos-samurai-kernel113/kernel
out=/mnt/e/edk2-samurai-out/kernel113
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=113
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 drivers/misc/fastrpc.ko drivers/soc/qcom/socinfo.ko > "$out/modules-build.log" 2>&1
test -s drivers/misc/fastrpc.ko
test -s drivers/soc/qcom/socinfo.ko
echo KERNEL113_NATIVE_MODULES_BUILD_PASS
