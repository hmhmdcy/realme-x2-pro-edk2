#!/bin/bash
set -euo pipefail
umask 077
stage=/home/cy122/pmos-samurai-kernel128
out=/mnt/e/edk2-samurai-out/kernel128
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=128
test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel128/key-delete-c-test-validation.json'
test ! -e "$stage/modules-root"
cd "$stage/kernel"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/config-build-private.log" 2>&1
grep -qx 'CONFIG_LOCALVERSION="-rmx1931-samurai-k128"' .config
grep -qx CONFIG_ATH10K=y .config
grep -qx CONFIG_ATH10K_SNOC=y .config
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules qcom/sm8150-samurai.dtb > "$out/modules-build-private.log" 2>&1
mkdir -m700 "$stage/modules-root"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- INSTALL_MOD_PATH="$stage/modules-root" INSTALL_MOD_STRIP=1 modules_install > "$out/modules-install-private.log" 2>&1
release=$(cat include/config/kernel.release)
test "$release" = 7.3.0-rc6-rmx1931-samurai-k128+
for name in btbcm btqca hci_uart; do
    source="$stage/modules-root/lib/modules/$release/kernel/drivers/bluetooth/$name.ko"
    test -f "$source"
    cp "$source" "$stage/initramfs/lib/modules/samurai/$name.ko"
    cmp "$source" "$stage/initramfs/lib/modules/samurai/$name.ko"
done
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image > "$out/image-build-private.log" 2>&1
test -s arch/arm64/boot/Image
test -L "$stage/modules-root/lib/modules/$release/build"
unlink "$stage/modules-root/lib/modules/$release/build"
depmod -e -F System.map -b "$stage/modules-root" "$release" > "$out/depmod-private.txt" 2>&1
test ! -s "$out/depmod-private.txt"
tar -C "$stage/modules-root" -czf "$out/modules-k128-private.tar.gz" lib/modules
echo K128_FULL_IMAGE_MODULES_DTB_MATCHING_INITRAMFS_BT_BUILD_PASS_NOT_DEPLOYED
