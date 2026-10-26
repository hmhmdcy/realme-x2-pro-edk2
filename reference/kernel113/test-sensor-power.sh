#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel113
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel113'
gcc -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Werror \
 "$ref/test-sensor-power.c" -o "$out/test-sensor-power" > "$out/test-sensor-power-build.log" 2>&1
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 "$out/test-sensor-power" \
 > "$out/test-sensor-power.log" 2>&1
tail -1 "$out/test-sensor-power.log"
