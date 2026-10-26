#!/bin/bash
# 第 2 步：把主线内核装进 EDK2 固件，并换成正确的 samurai DTB。
# 可重复执行（幂等）。
set -eu
RK=/home/cy122/edk2-samurai/repo
LINUX=/home/cy122/x2pro-linux/linux
DTB_SRC="/mnt/e/RealmeX2Pro edk2/linux-port/artifacts/sm8150-samurai.dtb"
GUID_STR="7a3c1e42-9d55-4c8b-b621-0f8a442e913d"
cd "$RK"

echo "=== 0. 配置加载顺序确认（决定 FD_SIZE 改哪个文件）==="
grep -n 'configs/' build.sh | head -12

echo
echo "=== 1. 换掉错误的主线 DTB（原来是 cepheus 的）==="
echo "旧: $(sha256sum Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb | cut -c1-16)"
cp -f "$DTB_SRC" Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
echo "新: $(sha256sum Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb | cut -c1-16)  (应为 1c760ec9cf74389c)"

echo
echo "=== 2. 内核 Image + INF ==="
mkdir -p Platform/Realme/sm8150/LinuxKernel
cp -f "$LINUX/arch/arm64/boot/Image" Platform/Realme/sm8150/LinuxKernel/Image
cat > Platform/Realme/sm8150/LinuxKernel/SamuraiLinuxKernel.inf <<EOF
# Mainline Linux kernel for realme X2 Pro (samurai), built with the EFI stub and
# a built-in diagnostic initramfs.  Embedded in the firmware volume as a UEFI
# application, exactly like LinuxSimpleMassStorage.efi, so BDS can start it
# after having enabled EUD (the host PC can then already have the COM port open
# and capture the full earlycon log).

[Defines]
  INF_VERSION                    = 0x00010005
  BASE_NAME                      = SamuraiLinuxKernel
  FILE_GUID                      = $GUID_STR
  MODULE_TYPE                    = UEFI_APPLICATION
  VERSION_STRING                 = 1.0

[Binaries.AARCH64]
  PE32|Image|RELEASE
EOF
ls -la Platform/Realme/sm8150/LinuxKernel/
sha256sum Platform/Realme/sm8150/LinuxKernel/Image

echo
echo "=== 3. 把 INF 加进设备 FDF 片段 ==="
if ! grep -q 'SamuraiLinuxKernel' Platform/Realme/sm8150/samurai.fdf.inc; then
	cat >> Platform/Realme/sm8150/samurai.fdf.inc <<'EOF'

// SAMURAI: mainline Linux kernel (EFI stub) as a UEFI application in this FV.
INF Platform/Realme/sm8150/LinuxKernel/SamuraiLinuxKernel.inf
EOF
fi
tail -5 Platform/Realme/sm8150/samurai.fdf.inc

echo
echo "=== 4. 在 PlatformBm.c 里注册启动项 ==="
python3 - <<'PY'
import re
p = "Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c"
src = open(p).read()
if "mSamuraiLinuxKernelGuid" in src:
    print("已经改过，跳过")
else:
    # 文件作用域插入 GUID 定义：放在最后一个 #include 之后
    lines = src.splitlines(True)
    idx = max(i for i, l in enumerate(lines) if l.startswith("#include"))
    guid_block = """
#ifdef SAMURAI_LINUX_KERNEL
//
// SAMURAI: GUID of the mainline Linux kernel embedded in this firmware volume
// (Platform/Realme/sm8150/LinuxKernel/SamuraiLinuxKernel.inf).  Must match the
// FILE_GUID there.
//
STATIC CONST EFI_GUID  mSamuraiLinuxKernelGuid = {
  0x7a3c1e42, 0x9d55, 0x4c8b, { 0xb6, 0x21, 0x0f, 0x8a, 0x44, 0x2e, 0x91, 0x3d }
};
#endif
"""
    lines.insert(idx + 1, guid_block)
    src = "".join(lines)

    marker = """#ifdef ENABLE_LINUX_SIMPLE_MASS_STORAGE
  //
  // Register Built-in Linux Kernel
  //
  PlatformRegisterFvBootOption(
      &gLinuxSimpleMassStorageGuid, L"USB Attached SCSI (UAS) Storage", LOAD_OPTION_ACTIVE);
#endif
"""
    assert marker in src, "找不到 UAS 注册块"
    addition = """
#ifdef SAMURAI_LINUX_KERNEL
  //
  // SAMURAI: the mainline Linux kernel built for this device.  BDS has already
  // enabled EUD before the console is set up, so a host PC that ran "eudtool
  // com-up" on the boot menu gets the complete kernel log from earlycon.
  //
  PlatformRegisterFvBootOption(
      &mSamuraiLinuxKernelGuid, L"Linux (mainline samurai)", LOAD_OPTION_ACTIVE);
#endif
"""
    src = src.replace(marker, marker + addition, 1)
    open(p, "w").write(src)
    print("PlatformBm.c 已修改")
PY
grep -n -A3 'mSamuraiLinuxKernelGuid, L"' Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c | head

echo
echo "=== 5. samurai.dsc 打开宏 ==="
if ! grep -q 'SAMURAI_LINUX_KERNEL' Platform/Realme/sm8150/samurai.dsc; then
	sed -i 's/-DSAMURAI_ENABLE_EUD/-DSAMURAI_ENABLE_EUD -DSAMURAI_LINUX_KERNEL/' Platform/Realme/sm8150/samurai.dsc
fi
grep -n 'GCC:\*_\*_AARCH64_CC_FLAGS' Platform/Realme/sm8150/samurai.dsc

echo
echo "=== 6. FD 尺寸 7MB -> 20MB（内核 30MB，压缩后约 11.7MB）==="
sed -i 's/^FD_SIZE=0x00700000/FD_SIZE=0x01400000/' configs/sm8150.conf
sed -i 's/^NumBlocks     = 0x700$/NumBlocks     = 0x1400/' Platform/Qualcomm/sm8150/sm8150.fdf
sed -i 's#^0x00000000|0x00700000$#0x00000000|0x01400000#' Platform/Qualcomm/sm8150/sm8150.fdf
echo "configs/sm8150.conf: $(grep FD_SIZE configs/sm8150.conf)"
grep -n 'NumBlocks' Platform/Qualcomm/sm8150/sm8150.fdf
grep -n 'PcdFvBaseAddress|gArmTokenSpaceGuid.PcdFvSize' Platform/Qualcomm/sm8150/sm8150.fdf
sed -n '/0x00000000|/p' Platform/Qualcomm/sm8150/sm8150.fdf | head -3

echo
echo "=== 7. 变更清单 ==="
git -C "$RK" status --short
echo READY
