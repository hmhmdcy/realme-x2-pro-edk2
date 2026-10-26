#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel91
qrtr=/mnt/e/edk2-samurai-out/kernel88/qrtr
src=$out/rmtfs-cow-src
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel91/prepare-rmtfs-cow.py'
for file in storage sharedmem; do
 aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -I"$src" -I"$qrtr/include" -c "$src/$file.c" -o "$out/$file-cow.o"
done
aarch64-linux-gnu-gcc -O2 -Wall -Werror=format -static -I"$qrtr/include" -I"$qrtr/lib" -I"$src" \
 "$src/rmtfs.c" "$src/qmi_rmtfs.c" "$src/rproc-disabled.c" \
 "$out/storage-cow.o" "$out/sharedmem-cow.o" \
 "$qrtr/lib/qrtr.c" "$qrtr/lib/qmi.c" "$qrtr/lib/logging.c" -o "$out/rmtfs-cow"
if aarch64-linux-gnu-readelf -l "$out/rmtfs-cow" | grep -q INTERP; then exit 1; fi
sha256sum "$out/rmtfs-cow" | tee "$out/rmtfs-cow.sha256"
