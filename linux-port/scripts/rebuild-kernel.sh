#!/bin/bash
# 先停掉用旧 Image 的固件构建，然后把内核 Image 真正重编出来
set -u
LK=/home/cy122/x2pro-linux/linux
RK=/home/cy122/edk2-samurai/repo

echo "=== 停掉当前固件构建 ==="
pkill -f 'build.sh -d samurai' 2>/dev/null && echo killed || echo "没有在跑"
sleep 2
pgrep -af 'build.sh|make -j' | head

echo
echo "=== 内核增量重编（前台，最多 10 分钟）==="
cd "$LK"
echo "改动文件的时间戳:"
ls -la drivers/tty/serial/eud_earlycon.c
timeout 600 make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image 2>&1 | tail -15
echo "MAKE_EXIT=${PIPESTATUS[0]}"

echo
ls -la arch/arm64/boot/Image
sha256sum arch/arm64/boot/Image
