#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel66
base=/mnt/e/edk2-samurai-out/logdump-k66-cpu.img
dest=/mnt/e/edk2-samurai-out/logdump-k66-adc.img
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = 43b1c0799acac5878cb1541bfceb4237249db3a2ed5181b39c917e27344eb154
cd "$src"
cmp .config "$out/config-cpu"
cmp arch/arm64/boot/Image "$out/Image-cpu"
scripts/config --enable QCOM_SPMI_ADC5
make -s ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/adc-olddefconfig.log" 2>&1
test "$(scripts/config --state INTERCONNECT_QCOM_OSM_L3)" = y
test "$(scripts/config --state QCOM_SPMI_ADC5)" = y
test "$(scripts/config --state QCOM_VADC_COMMON)" = y
diff -u "$out/config-cpu" .config > "$out/adc-config.diff" || test $? = 1
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/adc-build.log" 2>&1
if grep -Eq 'warning:|error:' "$out/adc-build.log"; then tail -50 "$out/adc-build.log"; exit 1; fi
cp "$base" "$dest"
mcopy -o -i "$dest" arch/arm64/boot/Image ::Image
cmp <(mcopy -i "$base" ::samurai.dtb -) <(mcopy -i "$dest" ::samurai.dtb -)
cmp arch/arm64/boot/Image <(mcopy -i "$dest" ::Image -)
test "$(sha256sum drivers/tty/serial/eud.c | cut -d' ' -f1)" = 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4
test "$(sha256sum drivers/tty/serial/eud_earlycon.c | cut -d' ' -f1)" = f0de320d4028d180099d0251b115371ca68bc84b51757910e6b0cdf94a9ddd53
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
cp .config "$out/config-adc"
cp arch/arm64/boot/Image "$out/Image-adc"
sha256sum "$dest" .config arch/arm64/boot/Image drivers/tty/serial/eud.c drivers/tty/serial/eud_earlycon.c /home/cy122/x2pro-linux/initramfs/init | tee "$out/adc-hashes.txt"
