#!/bin/bash
set -euo pipefail
src='/mnt/e/RealmeX2Pro edk2/reference/kernel91'
out=/mnt/e/edk2-samurai-out/kernel91
headers=$out/rmtfs-cow-src
qrtr=/mnt/e/edk2-samurai-out/kernel88/qrtr
for name in storage-cow sharedmem-bounded; do
 gcc -O2 -Wall -Wextra -Werror -I"$headers" -I"$qrtr/include" "$src/test-$name.c" -o "$out/test-$name-native"
 "$out/test-$name-native"
 aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static -I"$headers" -I"$qrtr/include" "$src/test-$name.c" -o "$out/test-$name"
done
sha256sum "$out/test-storage-cow" "$out/test-sharedmem-bounded"
