#!/bin/bash
# 等内核重编结束 -> 验证 -> 换进 EDK2 -> 启动固件重建
set -u
LK=/home/cy122/x2pro-linux/linux
RK=/home/cy122/edk2-samurai/repo
LOG=$HOME/x2pro-linux/build-image2.log

echo "=== 等内核重编 ==="
for i in $(seq 1 60); do
	pgrep -f 'make -j12 ARCH=arm64' >/dev/null 2>&1 || { echo "已结束（第 $i 次）"; break; }
	sleep 10
done
tail -3 "$LOG"
grep -E 'eud_earlycon' "$LOG" | tail -3
echo "错误: $(grep -ciE 'error' "$LOG" || true)"

echo
echo "=== 新 Image ==="
ls -la "$LK/arch/arm64/boot/Image"
sha256sum "$LK/arch/arm64/boot/Image"
echo "kernelrelease: $(cat $LK/include/config/kernel.release)"
od -An -c -N 4 -j 56 "$LK/arch/arm64/boot/Image"

echo
echo "=== 换进 EDK2 并重建固件 ==="
cp -f "$LK/arch/arm64/boot/Image" "$RK/Platform/Realme/sm8150/LinuxKernel/Image"
sha256sum "$RK/Platform/Realme/sm8150/LinuxKernel/Image"
cd "$RK"
export PATH=$HOME/.local/bin:$PATH
export CPATH=$HOME/edk2-samurai/local/uuid/usr/include
export LIBRARY_PATH=$HOME/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu
nohup ./build.sh -d samurai --toolchain GCC5 > $HOME/edk2-samurai/build-kernel-embed2.log 2>&1 &
echo "固件重建已启动：$HOME/edk2-samurai/build-kernel-embed2.log"
sleep 15
tail -3 $HOME/edk2-samurai/build-kernel-embed2.log
