#!/bin/bash
# 侦察构建条件：交叉编译器、现有 .config 来源、EFI/DTS 相关 Kconfig。
set -eu
cd /home/cy122/x2pro-linux/linux

echo "=== CPU / 编译器 ==="
nproc
for c in aarch64-linux-gnu-gcc aarch64-linux-gnu-gcc-14 aarch64-linux-gnu-gcc-13 clang clang-22 gcc; do
  printf '%-28s %s\n' "$c" "$(command -v $c || echo -)"
done
ls -d /usr/lib/llvm-* 2>/dev/null || echo "no /usr/lib/llvm-*"
ls ~/clangd22 2>/dev/null | head -3

echo
echo "=== 当前 .config 的编译器/来源 ==="
grep -E '^CONFIG_(CC_IS_|CC_VERSION_TEXT|LOCALVERSION|INITRAMFS_SOURCE|EFI_ARMSTUB_DTB_LOADER|EFI_STUB|SERIAL_EUD_EARLYCON|PSTORE_RAM|CMDLINE)' .config | head -20

echo
echo "=== EFI_ARMSTUB_DTB_LOADER 的 Kconfig 说明 ==="
grep -rn -B3 -A12 'config EFI_ARMSTUB_DTB_LOADER' arch/arm64/Kconfig drivers/firmware/efi/Kconfig 2>/dev/null | head -30

echo
echo "=== 旧工程配置的编译器 ==="
grep -E '^CONFIG_(CC_IS_|CC_VERSION_TEXT|LOCALVERSION|INITRAMFS_SOURCE|CMDLINE|EFI_|PSTORE_RAM)' \
  "/mnt/e/Realme X2 Pro移植主线Linux/artifacts/build/bringup.config" | head -20

echo
echo "=== 旧工程的静态 busybox 与 initramfs 素材 ==="
ls -la "/mnt/e/Realme X2 Pro移植主线Linux/artifacts/build/busybox" \
       "/mnt/e/Realme X2 Pro移植主线Linux/artifacts/build/initramfs.cpio.gz" 2>/dev/null
ls "/mnt/e/Realme X2 Pro移植主线Linux/initramfs/" 2>/dev/null
