#!/bin/bash
# 按顺序第 1 步：准备诊断内核配置 + 内置 initramfs，构建 EFI stub 的 Image。
# base = 旧工程 artifacts/build/bringup.config（同内核版本、同设备的诊断配置）
set -eu
LK=/home/cy122/x2pro-linux/linux
BASE="/mnt/e/Realme X2 Pro移植主线Linux/artifacts/build/bringup.config"
BUSYBOX="/mnt/e/Realme X2 Pro移植主线Linux/artifacts/build/busybox"
IRFS=/home/cy122/x2pro-linux/initramfs
LOGDIR=/home/cy122/x2pro-linux
cd "$LK"

echo "=== 1. 组装 initramfs ==="
rm -rf "$IRFS"; mkdir -p "$IRFS"/{bin,sbin,etc,proc,sys,dev,tmp}
cp "$BUSYBOX" "$IRFS/bin/busybox"
chmod +x "$IRFS/bin/busybox"
# 用 busybox 自己建符号链接
"$IRFS/bin/busybox" --install -s "$IRFS/bin" >/dev/null 2>&1 || true
cp "/mnt/e/RealmeX2Pro edk2/linux-port/initramfs/init" "$IRFS/init"
chmod +x "$IRFS/init"
ls "$IRFS/bin" | head -8
echo "initramfs: $(du -sh "$IRFS" | cut -f1)"

echo
echo "=== 2. 配置：以旧工程诊断配置为基线 ==="
cp -f .config "$LOGDIR/config.defconfig-base.bak" 2>/dev/null || true
cp -f "$BASE" .config
S=scripts/config
# UEFI 引导（旧配置里是关的）
$S --enable  EFI
$S --enable  EFI_STUB
$S --enable  EFI_GENERIC_STUB
$S --enable  EFI_ARMSTUB_DTB_LOADER
$S --enable  EFI_PARAMS_FROM_FDT
# EFI GOP -> simpledrm -> 屏幕控制台
$S --enable  DRM
$S --enable  DRM_SIMPLEDRM
$S --enable  SYSFB
$S --enable  SYSFB_SIMPLEFB
$S --enable  FRAMEBUFFER_CONSOLE
$S --enable  DRM_FBDEV_EMULATION
$S --enable  FONTS
$S --enable  FONT_8x16
$S --enable  VT
$S --enable  VT_CONSOLE
# 我们自己的 EUD earlycon
$S --enable  SERIAL_EUD_EARLYCON
$S --enable  SERIAL_EUD_CONSOLE
# pstore/ramoops 内置（DTS 里已经声明 0xb7e00000）
$S --enable  PSTORE
$S --enable  PSTORE_RAM
$S --enable  PSTORE_CONSOLE
$S --enable  PSTORE_PMSG
# 标识
$S --set-str LOCALVERSION "-rmx1931-samurai"
$S --set-str INITRAMFS_SOURCE "$IRFS"

echo "--- olddefconfig ---"
make -s ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$LOGDIR/olddefconfig.log" 2>&1 \
  || { echo "olddefconfig 失败"; tail -20 "$LOGDIR/olddefconfig.log"; exit 1; }

echo "--- 关键配置确认 ---"
grep -E '^CONFIG_(EFI=|EFI_STUB|EFI_ARMSTUB_DTB_LOADER|SYSFB_SIMPLEFB|DRM_SIMPLEDRM|FRAMEBUFFER_CONSOLE|SERIAL_EUD_EARLYCON|SERIAL_MSM=|SCSI_UFS_QCOM|USB_DWC3_GADGET|PSTORE_RAM|LOCALVERSION|INITRAMFS_SOURCE|DRM=)' .config

echo
echo "=== 3. 后台构建 Image ==="
nohup make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image \
  > "$LOGDIR/build-image.log" 2>&1 &
echo "构建已在后台启动： tail -f $LOGDIR/build-image.log"
sleep 20
tail -5 "$LOGDIR/build-image.log" 2>/dev/null || true
