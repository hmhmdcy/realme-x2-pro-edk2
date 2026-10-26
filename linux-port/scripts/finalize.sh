#!/bin/bash
# 收尾：归档产物、生成补丁、提交 EDK2 源码改动（不含 30MB 内核二进制）
set -u
LK=/home/cy122/x2pro-linux/linux
RK=/home/cy122/edk2-samurai/repo
OUT=/mnt/e/edk2-samurai-out
W="/mnt/e/RealmeX2Pro edk2/linux-port"

echo "=== 1. 归档固件 ==="
cp -f "$RK/boot-samurai.img" "$OUT/boot-samurai-linux.img"
cp -f "$RK/workspace/Build/samurai/RELEASE_GCC5/FV/SM8150_UEFI.fd" "$OUT/SM8150_UEFI-samurai-linux.fd"
ls -la "$OUT/boot-samurai-linux.img" "$OUT/SM8150_UEFI-samurai-linux.fd"
sha256sum "$OUT/boot-samurai-linux.img" "$OUT/SM8150_UEFI-samurai-linux.fd"

echo
echo "=== 2. 内核补丁重新生成 ==="
cd "$LK"
rm -f /home/cy122/x2pro-linux/patches/*.patch
git format-patch -2 -o /home/cy122/x2pro-linux/patches >/dev/null
ls /home/cy122/x2pro-linux/patches/
cp -f /home/cy122/x2pro-linux/patches/0001-*.patch "$W/patches/0001-tty-serial-add-Qualcomm-EUD-COM-early-console.patch"
cp -f /home/cy122/x2pro-linux/patches/0002-*.patch "$W/patches/0002-arm64-dts-qcom-add-realme-samurai-X2-Pro-bring-up-description.patch"
cp -f "$LK/arch/arm64/boot/Image" "$W/artifacts/Image-rmx1931-samurai" 2>/dev/null || true
sha256sum "$W/patches/"*.patch
echo "Image: $(sha256sum $LK/arch/arm64/boot/Image | cut -d' ' -f1)"
cp -f "$LK/arch/arm64/boot/Image" "$OUT/Image-rmx1931-samurai"
ls -la "$OUT/Image-rmx1931-samurai"
ls -la "$W/patches/"

echo
echo "=== 3. 提交 EDK2 源码改动 ==="
cd "$RK"
git add Platform/Realme/sm8150/samurai.dsc \
        Platform/Realme/sm8150/samurai.fdf.inc \
        Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb \
        Platform/Realme/sm8150/LinuxKernel/SamuraiLinuxKernel.inf \
        Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c \
        Platform/Qualcomm/sm8150/sm8150.fdf \
        configs/sm8150.conf
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m 'samurai: boot the mainline Linux kernel from the firmware volume

The port shipped cepheus (Xiaomi Mi 9) as its "mainline" DTB and had no way
to hand a kernel to the OS at all, so nothing could be validated beyond the
boot menu.

  - FdtBlob/samurai: replace the cepheus blob with a real device tree for
    this handset (Platform/Realme/sm8150/../linux-port, built from
    v7.3-rc6 with the MTP reference as a starting point);
  - LinuxKernel/SamuraiLinuxKernel.inf: the mainline kernel Image (EFI stub,
    built-in diagnostic initramfs, EUD earlycon) embedded as a UEFI
    application, exactly like LinuxSimpleMassStorage.efi;
  - PlatformBm.c: register it as a boot option ("Linux (mainline samurai)").
    BDS has already enabled EUD by then, so a host PC can open the COM port
    before the kernel starts and capture the complete earlycon log;
  - FD grows from 7 MiB to 20 MiB to make room (configs/sm8150.conf,
    sm8150.fdf NumBlocks and the FD region size).  0xCE000000 + 20 MiB is
    inside the 3 GiB conventional region at 0xC0000000 that both the live
    /memory node and the Mem8G profile describe.

PcdDefaultDtPref is TRUE, so DtPlatformDxe installs FdtBlob/samurai as the
FDT configuration table and the EFI stub picks it up.

The kernel Image itself is a build product and is not committed (see
linux-port/scripts/build-image.sh).'
git log --oneline -3
git status --short | head
echo DONE
