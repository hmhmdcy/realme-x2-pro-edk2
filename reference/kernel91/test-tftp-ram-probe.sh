#!/bin/bash
set -euo pipefail
src='/mnt/e/RealmeX2Pro edk2/reference/kernel91'
out=/mnt/e/edk2-samurai-out/kernel91
ro='/mnt/e/RealmeX2Pro edk2/reference/kernel88/ro-firmware.c'
gcc -O2 -Wall -Wextra -Werror "$src/test-tftp-ram-probe.c" "$src/tftp-ram-probe.c" "$ro" -o "$out/test-tftp-ram-probe-native"
"$out/test-tftp-ram-probe-native"
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static "$src/test-tftp-ram-probe.c" "$src/tftp-ram-probe.c" "$ro" -o "$out/test-tftp-ram-probe"
sha256sum "$out/test-tftp-ram-probe"
