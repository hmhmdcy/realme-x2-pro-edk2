#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel67
base=/mnt/e/edk2-samurai-out/logdump-k67-opp.img
dest=/mnt/e/edk2-samurai-out/logdump-k67-usb.img
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = 5c33242b2ba92f17dc9d1fd98c6b22de03f0ef2258542bf4bc435af87e365a10
cd "$src"
test "$(sha256sum .config | cut -d' ' -f1)" = 39d295de31e2ca99aad3782fecca0dad8028cf3ff832c21b4ff1aaafd464cdb9
test "$(sha256sum arch/arm64/boot/Image | cut -d' ' -f1)" = a60ff451c714d3d86887e1e01056f5fa71ce3f94046a0083a5f30d15ca21a242
test "$(sha256sum arch/arm64/boot/dts/qcom/sm8150-samurai.dtb | cut -d' ' -f1)" = 4641207124f1276f00749132d118ba73c3fdeaef24aeac8b2b1df017ef5dea9a
cp .config "$out/config-usb-before"
scripts/config --enable PHY_QCOM_USB_SNPS_FEMTO_V2
make -s ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/usb-olddefconfig.log" 2>&1
cp .config "$out/config-usb-after"
python3 - <<'PY'
from pathlib import Path
import difflib
out=Path('/mnt/e/edk2-samurai-out/kernel67')
before=(out/'config-usb-before').read_text()
after=(out/'config-usb-after').read_text()
assert after == before.replace('CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=m\n','CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=y\n')
(out/'usb-config.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='config-before',tofile='config-after')))
PY
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/usb-build.log" 2>&1
if grep -Eq 'warning:|error:' "$out/usb-build.log"; then tail -50 "$out/usb-build.log"; exit 1; fi
test "$(sha256sum drivers/tty/serial/eud.c | cut -d' ' -f1)" = 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4
test "$(sha256sum drivers/tty/serial/eud_earlycon.c | cut -d' ' -f1)" = 34da9936de5de9b36f232be3b8e0a730f9a56a77a6121b283b8e551bb3c65ad9
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
test "$(sha256sum arch/arm64/boot/dts/qcom/sm8150-samurai.dtb | cut -d' ' -f1)" = 4641207124f1276f00749132d118ba73c3fdeaef24aeac8b2b1df017ef5dea9a
cp "$base" "$dest"
mcopy -o -i "$dest" arch/arm64/boot/Image ::Image
cmp <(mcopy -i "$base" ::samurai.dtb -) <(mcopy -i "$dest" ::samurai.dtb -)
cmp arch/arm64/boot/Image <(mcopy -i "$dest" ::Image -)
sha256sum "$dest" .config arch/arm64/boot/Image arch/arm64/boot/dts/qcom/sm8150-samurai.dtb drivers/tty/serial/eud.c drivers/tty/serial/eud_earlycon.c /home/cy122/x2pro-linux/initramfs/init | tee "$out/usb-hashes.txt"
