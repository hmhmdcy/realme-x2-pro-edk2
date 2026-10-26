#!/bin/bash
set -euo pipefail
ref="/mnt/e/RealmeX2Pro edk2/reference/kernel77"
out=/mnt/e/edk2-samurai-out/kernel77
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static "$ref/read-gauge.c" -o "$out/read-gauge"
file "$out/read-gauge"
sha256sum "$ref/read-gauge.c" "$out/read-gauge"
