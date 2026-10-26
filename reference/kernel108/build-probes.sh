#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel108
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel108'
test ! -e "$out/http-packet-capture"
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static -o "$out/http-packet-capture" "$ref/http-packet-capture.c" > "$out/probe-build.log" 2>&1
file "$out/http-packet-capture"
sha256sum "$out/http-packet-capture"
