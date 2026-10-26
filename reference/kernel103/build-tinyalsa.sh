#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel103
repo=/home/cy122/x2pro-linux/refs/tinyalsa-k103
test ! -e "$repo"
git clone --depth 1 --branch v2.0.0 https://github.com/tinyalsa/tinyalsa.git "$repo" > "$out/tinyalsa-fetch.log" 2>&1
cd "$repo"
test "$(git rev-parse HEAD)" = 1c5fb68ced57d838f2b7ecd0c00bc1fefc9ab60d
test -s NOTICE
grep -q 'Redistribution and use in source and binary forms' NOTICE
make -j4 CC=aarch64-linux-gnu-gcc LD=aarch64-linux-gnu-gcc AR=aarch64-linux-gnu-ar LDFLAGS=-static > "$out/tinyalsa-build.log" 2>&1
cp utils/tinymix "$out/tinymix"
cp utils/tinypcminfo "$out/tinypcminfo"
cp utils/tinyplay "$out/tinyplay"
cp utils/tinycap "$out/tinycap"
file "$out/tinymix" "$out/tinyplay"
sha256sum "$out/tinymix" "$out/tinypcminfo" "$out/tinyplay" "$out/tinycap" > "$out/tinyalsa-tools.sha256"
