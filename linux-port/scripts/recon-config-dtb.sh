#!/bin/bash
# 旧配置的设备驱动现状 + EDK2 到底有没有把 FdtBlob 装进 EFI 配置表
set -eu
RK=/home/cy122/edk2-samurai/repo
OLD="/mnt/e/Realme X2 Pro移植主线Linux/artifacts/build/bringup.config"

echo "=== 旧 bringup.config：设备驱动 ==="
grep -E 'CONFIG_(SCSI_UFS|PHY_QCOM|PINCTRL_SPMI|USB_DWC3|USB_GADGET|USB_ETH|USB_CONFIGFS|QCOM_TSENS|QCOM_WDT|SERIAL_MSM|SERIAL_EARLYCON|SERIAL_EUD|PSTORE|RAMOOPS|QCOM_SCM|QCOM_SMD|RPMH|QCOM_CLK|QCOM_GDSC|DRM|FB_|SYSFB|EFI)' "$OLD" | sort

echo
echo "=== EDK2：谁安装 FDT 配置表 / 谁读 gDtPlatformDefaultDtbFileGuid ==="
grep -rn 'DtPlatformDefaultDtbFile\|DtPlatformDxe\|FdtPlatformDxe' "$RK/Platform/Realme" "$RK/Platform/RenegadePkg" "$RK/Silicon/Qualcomm/QcomPkg" "$RK/Platform/Qualcomm/sm8150" 2>/dev/null | head -20
echo "--- 全仓库（排除 workspace / edk2-platforms 自身驱动实现） ---"
grep -rln 'DtPlatformDefaultDtbFileGuid' "$RK" --include='*.c' --include='*.inf' --include='*.dsc' --include='*.fdf' 2>/dev/null | grep -v '/workspace/' | head -20
echo "--- SimpleInit 有没有装 DTB ---"
grep -rn -i 'fdt\|dtb' "$RK/GPLDrivers/Library/SimpleInit/src" --include='*.c' --include='*.h' 2>/dev/null | head -20
echo "--- samurai.dsc/fdf 里有没有 Fdt/Dt platform 驱动 ---"
grep -rn -i 'Fdt\|DtPlatform' "$RK/Platform/Realme/sm8150/samurai.dsc" "$RK/Platform/Realme/sm8150/samurai.fdf.inc" "$RK/Silicon/Qualcomm/QcomPkg/QcomCommonDsc.inc" 2>/dev/null | head -20
