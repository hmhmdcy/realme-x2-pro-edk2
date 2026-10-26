#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel85
source='/mnt/e/RealmeX2Pro edk2/reference/kernel85/read-stock-chemistry.c'
test ! -e "$out/read-stock-chemistry"
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static "$source" -o "$out/read-stock-chemistry"
file "$out/read-stock-chemistry"
sha256sum "$source" "$out/read-stock-chemistry" >"$out/chemistry-reader-build-hashes.txt"
cat "$out/chemistry-reader-build-hashes.txt"
