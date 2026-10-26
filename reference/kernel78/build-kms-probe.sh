#!/bin/bash
set -euo pipefail
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel78'
out=/mnt/e/edk2-samurai-out/kernel78
python3 "$ref/prepare-kms-probe.py"
aarch64-linux-gnu-gcc -Wall -Wextra -Werror -O2 -static -I/usr/aarch64-linux-gnu/include "$ref/kms-refresh.c" -o "$out/kms-refresh"
sha256sum "$ref/kms-refresh.c" "$out/kms-refresh"
