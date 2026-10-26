#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel66
base=/mnt/e/edk2-samurai-out/logdump-rx53-console-rx.img
dest=/mnt/e/edk2-samurai-out/logdump-k66-cpu.img
test ! -e "$dest"
test ! -e "$out/config-before-cpu"
test "$(sha256sum "$base" | cut -d' ' -f1)" = 50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93
test "$(sha256sum "$src/arch/arm64/boot/Image" | cut -d' ' -f1)" = 33efc6bc0c1c2d7b82b80b39dc7cea2331d05cca2005376399dade92b1597952
test "$(sha256sum "$src/drivers/tty/serial/eud.c" | cut -d' ' -f1)" = 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
cp "$src/.config" "$out/config-before-cpu"
cp "$src/arch/arm64/boot/Image" "$out/Image-before-cpu"
cd "$src"
scripts/config --enable INTERCONNECT_QCOM_OSM_L3
make -s ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/cpu-olddefconfig.log" 2>&1
test "$(scripts/config --state INTERCONNECT_QCOM_OSM_L3)" = y
test "$(scripts/config --state QCOM_SPMI_ADC5)" = m
diff -u "$out/config-before-cpu" .config > "$out/cpu-config.diff" || test $? = 1
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/cpu-build.log" 2>&1
if grep -Eq 'warning:|error:' "$out/cpu-build.log"; then
    tail -50 "$out/cpu-build.log"
    exit 1
fi
cp "$base" "$dest"
mcopy -o -i "$dest" "$src/arch/arm64/boot/Image" ::Image
cmp <(mcopy -i "$base" ::samurai.dtb -) <(mcopy -i "$dest" ::samurai.dtb -)
cmp "$src/arch/arm64/boot/Image" <(mcopy -i "$dest" ::Image -)
test "$(sha256sum "$src/drivers/tty/serial/eud.c" | cut -d' ' -f1)" = 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
cp .config "$out/config-cpu"
cp arch/arm64/boot/Image "$out/Image-cpu"
sha256sum "$dest" .config arch/arm64/boot/Image drivers/tty/serial/eud.c drivers/tty/serial/eud_earlycon.c /home/cy122/x2pro-linux/initramfs/init | tee "$out/cpu-hashes.txt"
