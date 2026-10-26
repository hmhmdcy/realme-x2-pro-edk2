#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel86
source='/mnt/e/RealmeX2Pro edk2/reference/kernel86/read-mp2650-input.c'
test ! -e "$out/read-mp2650-input"
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static "$source" -o "$out/read-mp2650-input"
file "$out/read-mp2650-input"
sha256sum "$source" "$out/read-mp2650-input" >"$out/reader-build-hashes.txt"
cat "$out/reader-build-hashes.txt"
