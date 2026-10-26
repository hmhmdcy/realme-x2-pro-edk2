#!/bin/bash
set -euo pipefail
umask 077
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py'
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel134/ensure-build-volume.py'
stage=/home/cy122/pmos-samurai-build134/usb134
out=/mnt/e/edk2-samurai-out/kernel134
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=134
test ! -e "$out/modules-build-private.log"
test ! -e "$out/usb-input-build-r2-private.log"
cd "$stage/kernel"
grep -qx CONFIG_USB_INPUT_SAMURAI=y .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- W=1 drivers/power/supply/samurai-usb-input.o > "$out/usb-input-build-r2-private.log" 2>&1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules qcom/sm8150-samurai.dtb > "$out/modules-build-private.log" 2>&1
/home/cy122/pmos-samurai-kernel118/camera120/schema-venv/bin/python '/mnt/e/RealmeX2Pro edk2/reference/kernel134/validate-usb-schema.py'
mkdir -m700 "$stage/modules-root"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- INSTALL_MOD_PATH="$stage/modules-root" INSTALL_MOD_STRIP=1 modules_install > "$out/modules-install-private.log" 2>&1
release=$(cat include/config/kernel.release)
test "$release" = 7.3.0-rc6-rmx1931-samurai-k134+
for name in btbcm btqca hci_uart; do
    source="$stage/modules-root/lib/modules/$release/kernel/drivers/bluetooth/$name.ko"
    cp "$source" "$stage/initramfs/lib/modules/samurai/$name.ko"
    cmp "$source" "$stage/initramfs/lib/modules/samurai/$name.ko"
done
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image > "$out/image-build-private.log" 2>&1
test -L "$stage/modules-root/lib/modules/$release/build"
unlink "$stage/modules-root/lib/modules/$release/build"
depmod -e -F System.map -b "$stage/modules-root" "$release" > "$out/depmod-private.txt" 2>&1
test ! -s "$out/depmod-private.txt"
tar -C "$stage/modules-root" -czf "$out/modules-k134-private.tar.gz" lib/modules
echo K134_FULL_KERNEL_MODULES_DTB_MATCHING_INITRAMFS_BUILD_PASS_NOT_DEPLOYED
