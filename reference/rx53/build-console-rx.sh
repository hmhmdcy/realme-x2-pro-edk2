#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/rx53
win='/mnt/e/RealmeX2Pro edk2/linux-port/eud.c'
test "$(sha256sum "$src/drivers/tty/serial/eud.c" | cut -d' ' -f1)" = e25d7fe215cab2ff842bdc3aa3bdf644d8f1701ecd27ea694fe43f848f5f5066
test "$(sha256sum "$src/arch/arm64/boot/Image" | cut -d' ' -f1)" = 5565d69447afa60d18aab045030b3ccedb1188daa9022bb379d8a6e38ef9117d
test "$(sha256sum "$src/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb" | cut -d' ' -f1)" = 68001bab92e8611373200f2928d1d83ef5256890528df59dea92c72c1900756e
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/bin/busybox | cut -d' ' -f1)" = 999cb969d09093a71716cfc747bb53cdada3f332c05eb5046c56e0f66a4d6d22
python3 - "$win" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
PY
cp "$win" "$src/drivers/tty/serial/eud.c"
cp "$win" "$out/eud-console-rx-candidate.c"
cd "$src"
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/build-console-rx.log" 2>&1
if grep -Eq 'warning:|error:' "$out/build-console-rx.log"; then
    cat "$out/build-console-rx.log"
    exit 1
fi
base=/mnt/e/edk2-samurai-out/logdump-rx48-tx-journal.img
dest=/mnt/e/edk2-samurai-out/logdump-rx53-console-rx.img
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = 61c0315cd24e24ce2bd020a8179647862eeacced28b142f21ffa0d2de00b953d
cp "$base" "$dest"
mcopy -o -i "$dest" "$src/arch/arm64/boot/Image" ::Image
cmp <(mcopy -i "$base" ::samurai.dtb -) <(mcopy -i "$dest" ::samurai.dtb -)
cmp "$src/arch/arm64/boot/Image" <(mcopy -i "$dest" ::Image -)
cp "$src/arch/arm64/boot/Image" "$out/Image-console-rx-candidate"
sha256sum "$dest" "$src/arch/arm64/boot/Image" "$src/drivers/tty/serial/eud.c" \
    "$src/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb" \
    /home/cy122/x2pro-linux/initramfs/init /home/cy122/x2pro-linux/initramfs/bin/busybox | tee "$out/console-rx-hashes.txt"
