#!/bin/bash
# 1) EDK2 侧：FdtBlob 的 FFS GUID 到底有没有消费者（决定我们的 DTB 能否到内核）
# 2) 内核侧：屏幕控制台相关配置现状
set -eu
RK=/home/cy122/edk2-samurai/repo
LK=/home/cy122/x2pro-linux/linux
OLD="/mnt/e/Realme X2 Pro移植主线Linux/artifacts/build/bringup.config"

echo "=== FdtBlob FFS GUID 消费者 ==="
grep -rn -i '25462CDA' "$RK" --include='*.c' --include='*.h' --include='*.inf' --include='*.inc' --include='*.dsc' --include='*.fdf' --include='*.depex' 2>/dev/null | grep -v '/workspace/' | head
echo "--- Fdt.h 里的 GUID ---"
sed -n '1,40p' "$RK/Common/edk2/EmbeddedPkg/Include/Guid/Fdt.h" 2>/dev/null
echo "--- 谁读取 FFS 里的 DTB（搜 FvSimpleFileSystem/DtbLoader/LoadFile) ---"
grep -rn -i 'fdtblob\|LoadFdt\|InstallConfigurationTable' "$RK/Platform/Realme" "$RK/Platform/RenegadePkg" "$RK/Silicon/Qualcomm/QcomPkg" 2>/dev/null | head
echo "--- AndroidBootImgLib 用 gFdtTableGuid 的地方 ---"
sed -n '405,430p' "$RK/Common/edk2/EmbeddedPkg/Library/AndroidBootImgLib/AndroidBootImgLib.c" 2>/dev/null

echo
echo "=== 内核：屏幕/EFI 帧缓冲相关（当前树 .config） ==="
grep -E '^CONFIG_(SYSFB|SYSFB_SIMPLEFB|DRM_SIMPLEDRM|FB_EFI|FRAMEBUFFER_CONSOLE|DRM=|DRM_FBDEV_EMULATION|VT|DUMMY_CONSOLE|EFI_EARLYCON)' "$LK/.config" | head -20

echo
echo "=== 内核：同一批符号在旧工程 bringup.config ==="
grep -E '^CONFIG_(SYSFB|SYSFB_SIMPLEFB|DRM_SIMPLEDRM|FB_EFI|FRAMEBUFFER_CONSOLE|DRM=|VT=|DUMMY_CONSOLE|UFS_QCOM|SCSI_UFSHCD|PHY_QCOM_QMP_UFS|USB_DWC3|USB_CONFIGFS|USB_GADGET|USB_ETH|QCOM_TSENS|PINCTRL_SPMI|PINCTRL_SPMI_GPIO|QCOM_WDT|SERIAL_MSM|SERIAL_MSM_CONSOLE|PSTORE_RAM|INITRAMFS)' "$OLD" | sort | head -40

echo
echo "=== 旧工程 initramfs/init 头 20 行 ==="
head -20 "/mnt/e/Realme X2 Pro移植主线Linux/initramfs/init"
