#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/rx45
echo 'e17acbd5d6139c94c3e22f6d6bcd442186d3bd24e9292a10e29f3d5781970dd2  /home/cy122/x2pro-linux/linux/drivers/tty/serial/eud.c' | sha256sum -c -
cp '/mnt/e/RealmeX2Pro edk2/linux-port/eud.c' "$src/drivers/tty/serial/eud.c"
cp "$src/drivers/tty/serial/eud.c" "$out/eud-mask-candidate.c"
cd "$src"
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/build-mask.log" 2>&1
base=/mnt/e/edk2-samurai-out/logdump-rx41-native-ordered-tty.img
dest=/mnt/e/edk2-samurai-out/logdump-rx45-rx-mask.img
test ! -e "$dest"
echo 'cdf0c1eb633c906f424dfd33c4d7757e1cc1bfe6edd88002127da4ebbdca477f  /mnt/e/edk2-samurai-out/logdump-rx41-native-ordered-tty.img' | sha256sum -c -
cp "$base" "$dest"
mcopy -o -i "$dest" "$src/arch/arm64/boot/Image" ::Image
cmp <(mcopy -i "$base" ::samurai.dtb -) <(mcopy -i "$dest" ::samurai.dtb -)
cmp "$src/arch/arm64/boot/Image" <(mcopy -i "$dest" ::Image -)
cp "$src/arch/arm64/boot/Image" "$out/Image-mask-candidate"
sha256sum "$dest" "$src/arch/arm64/boot/Image" "$src/drivers/tty/serial/eud.c" /home/cy122/x2pro-linux/initramfs/init /home/cy122/x2pro-linux/initramfs/bin/busybox | tee "$out/mask-hashes.txt"
