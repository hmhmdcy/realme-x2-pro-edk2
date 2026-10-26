#!/bin/bash
# 第 2 步准备：FD/FV 尺寸、启动项注册接口、现有 Linux app、手机是否在线
set -u
RK=/home/cy122/edk2-samurai/repo
LK=/home/cy122/x2pro-linux/linux

echo "=== sm8150.fdf 的 FD/FV 定义 ==="
grep -n -A12 '^\[FD' "$RK/Platform/Qualcomm/sm8150/sm8150.fdf" | head -40
echo "--- FVMAIN ---"
grep -n -A14 '^\[FV.FVMAIN' "$RK/Platform/Qualcomm/sm8150/sm8150.fdf" | head -30

echo
echo "=== FD_SIZE 从哪来 ==="
grep -rn 'FD_SIZE' "$RK/build.sh" "$RK/tools/BootShim/Makefile" "$RK/Silicon/"*.sh 2>/dev/null | head -10

echo
echo "=== PlatformRegisterFvBootOption 与 UAS 用的 GUID ==="
grep -n -B4 -A25 'PlatformRegisterFvBootOption' "$RK/Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBootManagerLib.inf" 2>/dev/null | head -30
grep -rn 'gLinuxSimpleMassStorageGuid' "$RK/Common/edk2/EmbeddedPkg/Include/Guid/"*.h "$RK/Platform/RenegadePkg" 2>/dev/null | head -5
grep -rn 'gLinuxSimpleMassStorageGuid\|gUefiShellFileGuid' "$RK/Common/edk2/EmbeddedPkg/EmbeddedPkg.dec" 2>/dev/null | head -5

echo
echo "=== 现有 Linux app 到底是不是"内核+initramfs" ==="
ls -la "$RK/Platform/EFI_Binaries/Applications/LinuxSimpleMassStorage/" 2>/dev/null
file "$RK/Platform/EFI_Binaries/Applications/LinuxSimpleMassStorage/LinuxSimpleMassStorage.efi" 2>/dev/null
strings -a "$RK/Platform/EFI_Binaries/Applications/LinuxSimpleMassStorage/LinuxSimpleMassStorage.efi" 2>/dev/null | grep -m5 -iE 'Linux version|initramfs|gzip|zImage' | head

echo
echo "=== 手机在线吗 ==="
A=/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/adb.exe
F=/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe
"$A" devices 2>&1 | head -3
"$F" devices 2>&1 | head -3

echo
echo "=== 我们的新 DTB 与 EDK2 里占位 DTB ==="
sha256sum "/mnt/e/RealmeX2Pro edk2/linux-port/artifacts/sm8150-samurai.dtb" \
          "$RK/Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb" 2>&1
