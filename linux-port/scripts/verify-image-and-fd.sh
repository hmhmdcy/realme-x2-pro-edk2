#!/bin/bash
# 1) 验证刚构建出的 Image；2) 摸清 EDK2 FD 尺寸/BootShim 约束，为把内核装进 FV 做准备
set -u
LK=/home/cy122/x2pro-linux/linux
RK=/home/cy122/edk2-samurai/repo
IMG=$LK/arch/arm64/boot/Image

echo "=== Image 基本信息 ==="
ls -la "$IMG"
sha256sum "$IMG"
echo "kernelrelease: $(cat $LK/include/config/kernel.release)"
echo "--- 头部（应看到 MZ 与 ARM\\x64 魔数，说明带 EFI stub）---"
od -An -tx1 -N 8 "$IMG"
od -An -c -N 4 -j 56 "$IMG"

echo
echo "--- 关键字符串确认 ---"
for s in 'rmx1931-mainline initramfs reached userspace' 'EFI stub' 'efi-stub' 'eud' 'simpledrm'; do
  n=$(grep -c -a -F "$s" "$IMG" 2>/dev/null || true)
  printf '%-45s %s\n' "$s" "$n"
done
echo "--- earlycon 名字表里有没有 eud ---"
grep -a -o '__earlycon_eud' "$IMG" | head -2
grep -a -o 'CONFIG_SERIAL_EUD_EARLYCON' "$IMG" | head -2

echo
echo "=== EDK2：FD 尺寸与 FV 布局 ==="
grep -rn -iE 'FD_SIZE|FVMAIN|FvMain|0x[0-9a-f]+ *\|' "$RK/Platform/Realme/sm8150/samurai.fdf" 2>/dev/null | head -20
ls "$RK/Platform/Realme/sm8150/"
echo "--- 当前 FD 大小 ---"
ls -la "$RK/SM8150_UEFI-samurai.fd" 2>/dev/null || find "$RK" -maxdepth 2 -name '*.fd' -newermt '2026-10-01' 2>/dev/null | head

echo
echo "=== BootShim：image_size / UEFI 基址约束 ==="
grep -n -iE 'image_size|UEFI_BASE|0xce000000|UEFI_SIZE' "$RK/tools/BootShim/BootShim.S" 2>/dev/null | head -20
grep -n -iE 'UEFI_BASE|FD_BASE|image_size|UEFI_SIZE' "$RK/build.sh" 2>/dev/null | head -10

echo
echo "=== EDK2 仓库状态（改动前先看） ==="
git -C "$RK" log --oneline -3
git -C "$RK" status --short | head -20

echo
echo "=== PlatformBm.c 里注册 UAS/Linux 启动项的那一段 ==="
sed -n '745,775p' "$RK/Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c"
