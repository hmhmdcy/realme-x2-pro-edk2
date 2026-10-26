#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel85
source='/mnt/e/RealmeX2Pro edk2/reference/kernel85/read-short-ic.c'
test ! -e "$out/read-short-ic"
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static "$source" -o "$out/read-short-ic"
file "$out/read-short-ic"
sha256sum "$source" "$out/read-short-ic" >"$out/reader-build-hashes.txt"
cat "$out/reader-build-hashes.txt"
