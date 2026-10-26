#!/bin/bash
set -euo pipefail
cd /home/cy122/hexagonrpc-v04-k112
out=/mnt/e/edk2-samurai-out/kernel112
cp '/mnt/e/RealmeX2Pro edk2/reference/kernel112/test_listener_large.c' hexagonrpcd/test_listener_large.c
gcc -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra \
 -Wno-unused-parameter -Iinclude -Ihexagonrpcd \
 hexagonrpcd/{test_listener_large,iobuffer,interfaces}.c -o "$out/test-listener-large" \
 > "$out/test-listener-large-build.log" 2>&1
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 "$out/test-listener-large" \
 > "$out/test-listener-large.log" 2>&1
tail -1 "$out/test-listener-large.log"
