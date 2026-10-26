#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel71
base=/mnt/e/edk2-samurai-out/logdump-k67-usb.img
dest=$out/logdump-k71-touch.img
cd "$src"
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = cfbe4509da3e4455351c11cad6400af7cc4044f21cc3ba04e3927bd01c35e6d7
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
for opt in I2C_QCOM_GENI QCOM_GPI_DMA RMI4_CORE RMI4_I2C RMI4_F12 INPUT_EVDEV REGULATOR_FIXED_VOLTAGE; do grep -qx "CONFIG_$opt=y" .config; done
grep -qx '# CONFIG_RMI4_F34 is not set' .config
grep -qx 'CONFIG_INITRAMFS_SOURCE="/home/cy122/x2pro-linux/initramfs"' .config
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
if grep -Eq 'Warning|warning:|Error|error:' "$out/kernel-build.log"; then cat "$out/kernel-build.log"; exit 1; fi
test "$(sha256sum drivers/tty/serial/eud.c | cut -d' ' -f1)" = 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4
test "$(sha256sum drivers/tty/serial/eud_earlycon.c | cut -d' ' -f1)" = 34da9936de5de9b36f232be3b8e0a730f9a56a77a6121b283b8e551bb3c65ad9
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
cp arch/arm64/boot/Image "$out/Image-touch"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/samurai-after.dtb"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dts "$out/samurai-after.dts"
cp drivers/input/rmi4/rmi_i2c.c "$out/rmi_i2c-after.c"
cp .config "$out/config-touch"
diff -u "$out/config-before" .config > "$out/config.diff" || test "$?" = 1
diff -u "$out/rmi_i2c-before.c" drivers/input/rmi4/rmi_i2c.c > "$out/rmi_i2c.diff" || test "$?" = 1
diff -u "$out/samurai-before.dts" arch/arm64/boot/dts/qcom/sm8150-samurai.dts > "$out/samurai.diff" || test "$?" = 1
cp "$base" "$dest"
mcopy -o -i "$dest" arch/arm64/boot/Image ::Image
mcopy -o -i "$dest" arch/arm64/boot/dts/qcom/sm8150-samurai.dtb ::samurai.dtb
cmp arch/arm64/boot/Image <(mcopy -i "$dest" ::Image -)
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb <(mcopy -i "$dest" ::samurai.dtb -)
mdir -i "$dest" :: > "$out/logdump-directory.txt"
sha256sum "$dest" arch/arm64/boot/Image .config arch/arm64/boot/dts/qcom/sm8150-samurai.dtb > "$out/kernel-build-hashes.txt"
tail -8 "$out/kernel-build.log"
