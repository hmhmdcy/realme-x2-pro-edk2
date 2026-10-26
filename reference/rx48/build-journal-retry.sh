#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/rx48
win='/mnt/e/RealmeX2Pro edk2/linux-port/eud.c'
cmp "$src/drivers/tty/serial/eud.c" "$out/eud-journal-api-error.c"
test "$(sha256sum "$src/arch/arm64/boot/Image" | cut -d' ' -f1)" = 0e4580dabe7a779a4168e6fec03c968adae6c155a2f259fb01b9178dd7ccd511
cp "$win" "$src/drivers/tty/serial/eud.c"
cp "$win" "$out/eud-journal-candidate.c"
cd "$src"
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/build-journal.log" 2>&1
if grep -Eq 'warning:|error:' "$out/build-journal.log"; then
    cat "$out/build-journal.log"
    exit 1
fi
base=/mnt/e/edk2-samurai-out/logdump-rx48-watchdog-grace.img
dest=/mnt/e/edk2-samurai-out/logdump-rx48-tx-journal.img
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = 9a1740c26cd6de899ef1255262f4a83b920e7f36982a8ec02aff549d599396b4
cp "$base" "$dest"
mcopy -o -i "$dest" "$src/arch/arm64/boot/Image" ::Image
cmp <(mcopy -i "$base" ::samurai.dtb -) <(mcopy -i "$dest" ::samurai.dtb -)
cmp "$src/arch/arm64/boot/Image" <(mcopy -i "$dest" ::Image -)
cp "$src/arch/arm64/boot/Image" "$out/Image-journal-candidate"
sha256sum "$dest" "$src/arch/arm64/boot/Image" "$src/drivers/tty/serial/eud.c" \
    /home/cy122/x2pro-linux/initramfs/init /home/cy122/x2pro-linux/initramfs/bin/busybox | tee "$out/journal-hashes.txt"
