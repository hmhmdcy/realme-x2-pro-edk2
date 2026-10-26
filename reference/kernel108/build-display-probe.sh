#!/bin/sh
set -eu
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel108'
out=/mnt/e/edk2-samurai-out/kernel108
test ! -e "$out/display-cycle"
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static "$ref/drm-panel-cycle.c" -o "$out/display-cycle"
sha256sum "$out/display-cycle" | cut -d ' ' -f 1 > "$out/display-cycle.sha256"
file "$out/display-cycle"
sha256sum "$ref/drm-panel-cycle.c" "$out/display-cycle"
