#!/bin/bash
# 关键：DtPlatformDxe 只有在"DT 优先"时才把 DTB 装进 EFI 配置表。
# 查 PcdDefaultDtPref 当前值，以及 DTB 加载库的解析。
set -u
RK=/home/cy122/edk2-samurai/repo

echo "=== PcdDefaultDtPref 定义与赋值 ==="
grep -rn 'PcdDefaultDtPref' "$RK/Common/edk2/EmbeddedPkg/EmbeddedPkg.dec" 2>/dev/null
grep -rn 'PcdDefaultDtPref' "$RK" --include='*.dsc' --include='*.inc' --include='*.fdf' 2>/dev/null | grep -v workspace | head
echo "--- 代码默认值 ---"
grep -rn -B4 -A4 'PcdDefaultDtPref' "$RK/Common/edk2/EmbeddedPkg/EmbeddedPkg.dec" 2>/dev/null | head -20

echo
echo "=== DtPlatformDtbLoaderLib 解析到哪个实现 ==="
grep -rn 'DtPlatformDtbLoaderLib' "$RK/Silicon/Qualcomm/QcomPkg/QcomCommonDsc.inc" "$RK/Platform/Realme/sm8150/samurai.dsc" 2>/dev/null | head
grep -rn 'DtPlatformDtbLoaderLib' "$RK/Common/edk2/EmbeddedPkg/EmbeddedPkg.dsc" 2>/dev/null | head -5

echo
echo "=== 构建出的 FD 里 PCD 段是否含 DT 选择信息（间接手段）==="
grep -a -o 'DtAcpiPref' "$RK/workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.Fv" 2>/dev/null | head -2
grep -a -o 'no DTB blob could be loaded' "$RK/workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.Fv" 2>/dev/null | head -2

echo
echo "=== DtPlatformDxe 是否在 FV 里 ==="
grep -a -i 'DtPlatformDxe' "$RK/workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.inf" 2>/dev/null | head -3
