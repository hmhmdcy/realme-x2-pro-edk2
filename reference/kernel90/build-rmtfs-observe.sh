#!/bin/bash
set -euo pipefail
src='/mnt/e/RealmeX2Pro edk2/reference/kernel90'
out=/mnt/e/edk2-samurai-out/kernel90
qrtr=/mnt/e/edk2-samurai-out/kernel88/qrtr
rmtfs=$out/rmtfs
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -I"$qrtr/include" -I"$rmtfs" \
  -c "$src/rmtfs-observe.c" -o "$out/rmtfs-observe.o"
aarch64-linux-gnu-gcc -O2 -static -I"$qrtr/include" -I"$qrtr/lib" -I"$rmtfs" \
  "$out/rmtfs-observe.o" "$rmtfs/qmi_rmtfs.c" \
  "$qrtr/lib/qrtr.c" "$qrtr/lib/qmi.c" "$qrtr/lib/logging.c" \
  -o "$out/rmtfs-observe"
aarch64-linux-gnu-readelf -h "$out/rmtfs-observe"
if aarch64-linux-gnu-readelf -l "$out/rmtfs-observe" | grep -q INTERP; then exit 1; fi
sha256sum "$out/rmtfs-observe" | tee "$out/rmtfs-observe.sha256"
