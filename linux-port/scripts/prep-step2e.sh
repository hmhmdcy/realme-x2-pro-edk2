#!/bin/bash
# 最后三个细节：FD_SIZE 定义、启动项注册函数、LinuxSimpleMassStorage.inf 全文
set -u
RK=/home/cy122/edk2-samurai/repo

echo "=== FD_SIZE= 出现在哪 ==="
grep -rn 'FD_SIZE=' "$RK" --include='*.sh' --include='*.conf' --include='*.cfg' --include='*.json' --include='*.inc' 2>/dev/null | grep -v '/workspace/' | head -20
echo "--- 或者从环境/PCD 推 ---"
grep -rn 'PcdFdSize\|FD_SIZE' "$RK/Silicon/Qualcomm/QcomPkg/QcomCommonDsc.inc" "$RK/Platform/Qualcomm/sm8150/sm8150.dsc" 2>/dev/null | head

echo
echo "=== PlatformRegisterFvBootOption 定义（PlatformBm.c 280-340）==="
sed -n '280,340p' "$RK/Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c"

echo
echo "=== LinuxSimpleMassStorage.inf 全文 ==="
cat "$RK/Platform/EFI_Binaries/Applications/LinuxSimpleMassStorage/LinuxSimpleMassStorage.inf"

echo
echo "=== sm8150.fdf 里 INF LinuxSimpleMassStorage 的上下文（175-195）==="
sed -n '175,195p' "$RK/Platform/Qualcomm/sm8150/sm8150.fdf"
