#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel103
repo=/home/cy122/x2pro-linux/refs/tinyalsa-k103
cd "$repo"
test "$(git rev-parse HEAD)" = 1c5fb68ced57d838f2b7ecd0c00bc1fefc9ab60d
grep -q 'Redistribution and use in source and binary forms' LICENSE
# Build only the static archive. A shared-library target cannot accept -static.
make -C src -j4 CC=aarch64-linux-gnu-gcc AR=aarch64-linux-gnu-ar libtinyalsa.a > "$out/tinyalsa-static-build.log" 2>&1
for name in tinymix tinypcminfo tinyplay tinycap; do
    test ! -e "$out/$name"
    aarch64-linux-gnu-gcc -static -O2 -Iinclude "utils/$name.c" src/libtinyalsa.a -ldl -o "$out/$name" >> "$out/tinyalsa-static-build.log" 2>&1
    aarch64-linux-gnu-readelf -h "$out/$name" | grep -q AArch64
    ! aarch64-linux-gnu-readelf -l "$out/$name" | grep -q INTERP
done
sha256sum "$out/tinymix" "$out/tinypcminfo" "$out/tinyplay" "$out/tinycap" > "$out/tinyalsa-tools.sha256"
echo FOUR_STATIC_AARCH64_AUDIO_TOOLS_BUILT
