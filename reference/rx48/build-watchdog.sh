#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/rx48
win='/mnt/e/RealmeX2Pro edk2/linux-port/eud.c'
test "$(sha256sum "$src/drivers/tty/serial/eud.c" | cut -d' ' -f1)" = 673c485843bc551788a0eb90499207371110807d4700a1f3f20d42b76e4e921f
test "$(sha256sum "$src/arch/arm64/boot/Image" | cut -d' ' -f1)" = e0f256d7b08410bc7cd17db03aa2351338753bb7b9add562d3bcedc29964fba3
test ! -e "$out/Image-before-rx48"
cp "$src/arch/arm64/boot/Image" "$out/Image-before-rx48"
cp "$win" "$src/drivers/tty/serial/eud.c"
cp "$win" "$out/eud-watchdog-candidate.c"
cd "$src"
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/build-watchdog.log" 2>&1
if grep -Eq 'warning:|error:' "$out/build-watchdog.log"; then
    cat "$out/build-watchdog.log"
    exit 1
fi
base=/mnt/e/edk2-samurai-out/logdump-rx46-rx-irq-b.img
dest=/mnt/e/edk2-samurai-out/logdump-rx48-watchdog-grace.img
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = ba1689b380b40aeee2714ae7c41b44a7db3365ef61c0937b607b12537b6c320e
cp "$base" "$dest"
mcopy -o -i "$dest" "$src/arch/arm64/boot/Image" ::Image
cmp <(mcopy -i "$base" ::samurai.dtb -) <(mcopy -i "$dest" ::samurai.dtb -)
cmp "$src/arch/arm64/boot/Image" <(mcopy -i "$dest" ::Image -)
cp "$src/arch/arm64/boot/Image" "$out/Image-watchdog-candidate"
sha256sum "$dest" "$src/arch/arm64/boot/Image" "$src/drivers/tty/serial/eud.c" \
    /home/cy122/x2pro-linux/initramfs/init /home/cy122/x2pro-linux/initramfs/bin/busybox | tee "$out/hashes.txt"
