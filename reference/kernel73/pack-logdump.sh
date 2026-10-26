#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel73
src=/home/cy122/x2pro-linux/linux
base=/mnt/e/edk2-samurai-out/kernel72/logdump-k72-ncm-ssh.img
dest=$out/logdump-k73-display.img
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = 13a8263dac6c75f909b6fa8dc89520949c7009ddcb9de2b2a5f6125e26d4292b
cp "$base" "$out/logdump-before.img"
cp "$base" "$dest"
mcopy -o -i "$dest" "$src/arch/arm64/boot/Image" ::Image
mcopy -o -i "$dest" "$src/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb" ::samurai.dtb
cmp "$src/arch/arm64/boot/Image" <(mcopy -i "$dest" ::Image -)
cmp "$src/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb" <(mcopy -i "$dest" ::samurai.dtb -)
mdir -i "$dest" :: > "$out/logdump-directory.txt"
sha256sum "$dest" "$out/boot-k73-display.img" > "$out/flash-image-hashes.txt"
cat "$out/flash-image-hashes.txt"
