#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/rx46
echo '2666a654225f898f07b8e3696f7ba6cc203ee3d0746ce4bf66286cc190f035cb  /home/cy122/x2pro-linux/linux/drivers/tty/serial/eud.c' | sha256sum -c -
echo 'ddefb54c52963acc9a8ad447e3da8d4da56b6e60abddd213937d3b875378b8cc  /home/cy122/x2pro-linux/linux/arch/arm64/boot/Image' | sha256sum -c -
cp '/mnt/e/RealmeX2Pro edk2/linux-port/eud.c' "$src/drivers/tty/serial/eud.c"
cp "$src/drivers/tty/serial/eud.c" "$out/eud-irq-candidate-b.c"
cd "$src"
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/build-irq-b.log" 2>&1
if grep -Eq 'warning:|error:' "$out/build-irq-b.log"; then
    cat "$out/build-irq-b.log"
    exit 1
fi
base=/mnt/e/edk2-samurai-out/logdump-rx41-native-ordered-tty.img
dest=/mnt/e/edk2-samurai-out/logdump-rx46-rx-irq-b.img
test ! -e "$dest"
echo 'cdf0c1eb633c906f424dfd33c4d7757e1cc1bfe6edd88002127da4ebbdca477f  /mnt/e/edk2-samurai-out/logdump-rx41-native-ordered-tty.img' | sha256sum -c -
cp "$base" "$dest"
mcopy -o -i "$dest" "$src/arch/arm64/boot/Image" ::Image
cmp <(mcopy -i "$base" ::samurai.dtb -) <(mcopy -i "$dest" ::samurai.dtb -)
cmp "$src/arch/arm64/boot/Image" <(mcopy -i "$dest" ::Image -)
cp "$src/arch/arm64/boot/Image" "$out/Image-irq-candidate-b"
sha256sum "$dest" "$src/arch/arm64/boot/Image" "$src/drivers/tty/serial/eud.c" /home/cy122/x2pro-linux/initramfs/init /home/cy122/x2pro-linux/initramfs/bin/busybox | tee "$out/irq-b-hashes.txt"
