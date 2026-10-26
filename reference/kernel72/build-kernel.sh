#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel72
base=/mnt/e/edk2-samurai-out/kernel71/logdump-k71-touch.img
dest=$out/logdump-k72-ncm-ssh.img
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = f6837573c908eddad7a2d8d0ab494c259ff99a9a5b85878e3b6747d40b2d3fb8
cd "$src"
cp .config "$out/config-before"
sha256sum drivers/tty/serial/eud.c drivers/tty/serial/eud_earlycon.c \
    drivers/input/rmi4/rmi_i2c.c arch/arm64/boot/dts/qcom/sm8150-samurai.dts \
    arch/arm64/boot/dts/qcom/sm8150-samurai.dtb >"$out/core-before.sha256"
scripts/config --set-val INITRAMFS_ROOT_UID 1000 --set-val INITRAMFS_ROOT_GID 1000
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >"$out/olddefconfig.log" 2>&1
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image \
    >"$out/kernel-build.log" 2>&1
if grep -Eq 'Warning|warning:|Error|error:' "$out/kernel-build.log"; then
    cat "$out/kernel-build.log"; exit 1
fi
sha256sum -c "$out/core-before.sha256"
grep -qx 'CONFIG_USB_CONFIGFS_NCM=y' .config
grep -qx 'CONFIG_INITRAMFS_ROOT_UID=1000' .config
grep -qx 'CONFIG_INITRAMFS_ROOT_GID=1000' .config
cp .config "$out/config-ncm"
diff -u "$out/config-before" .config >"$out/config.diff" || test "$?" = 1
cp arch/arm64/boot/Image "$out/Image-ncm-ssh"
cp "$base" "$dest"
mcopy -o -i "$dest" arch/arm64/boot/Image ::Image
cmp arch/arm64/boot/Image <(mcopy -i "$dest" ::Image -)
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb <(mcopy -i "$dest" ::samurai.dtb -)
mdir -i "$dest" :: >"$out/logdump-directory.txt"
sha256sum "$dest" arch/arm64/boot/Image .config >"$out/kernel-build-hashes.txt"
tail -8 "$out/kernel-build.log"
cat "$out/kernel-build-hashes.txt"
