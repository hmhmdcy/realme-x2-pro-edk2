#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel67
base=/mnt/e/edk2-samurai-out/logdump-k66-map.img
dest=/mnt/e/edk2-samurai-out/logdump-k67-opp.img
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = c2658235953cbdb8820cfabe6bee9ab0526b8fceb6b69f71f029174690b16e4d
cd "$src"
test "$(sha256sum .config | cut -d' ' -f1)" = 39d295de31e2ca99aad3782fecca0dad8028cf3ff832c21b4ff1aaafd464cdb9
test "$(sha256sum arch/arm64/boot/Image | cut -d' ' -f1)" = a60ff451c714d3d86887e1e01056f5fa71ce3f94046a0083a5f30d15ca21a242
test "$(sha256sum drivers/tty/serial/eud.c | cut -d' ' -f1)" = 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4
test "$(sha256sum drivers/tty/serial/eud_earlycon.c | cut -d' ' -f1)" = 34da9936de5de9b36f232be3b8e0a730f9a56a77a6121b283b8e551bb3c65ad9
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/samurai-before.dtb"
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- qcom/sm8150-samurai.dtb > "$out/opp-build.log" 2>&1
if grep -Eq 'Warning|warning:|Error|error:' "$out/opp-build.log"; then cat "$out/opp-build.log"; exit 1; fi
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/samurai-after.dtb"
cp "$base" "$dest"
mcopy -o -i "$dest" arch/arm64/boot/dts/qcom/sm8150-samurai.dtb ::samurai.dtb
cmp <(mcopy -i "$base" ::Image -) <(mcopy -i "$dest" ::Image -)
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb <(mcopy -i "$dest" ::samurai.dtb -)
cmp .config /mnt/e/edk2-samurai-out/kernel66/config-adc
sha256sum "$dest" .config arch/arm64/boot/Image arch/arm64/boot/dts/qcom/sm8150-samurai.dtb drivers/tty/serial/eud.c drivers/tty/serial/eud_earlycon.c /home/cy122/x2pro-linux/initramfs/init | tee "$out/opp-hashes.txt"
