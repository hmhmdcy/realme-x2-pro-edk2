#!/bin/bash
set -euo pipefail
source='/mnt/e/RealmeX2Pro edk2/reference/kernel92'
out=/mnt/e/edk2-samurai-out/kernel92
nl=/home/cy122/x2pro-linux/wifi-tools-k90/install
aarch64-linux-gnu-gcc -static -O2 -Wall -Wextra -Werror -Wno-misleading-indentation "$source/bt-mgmt-probe.c" -o "$out/bt-mgmt-probe"
aarch64-linux-gnu-gcc -static -O2 -Wall -Wextra -Werror -Wno-misleading-indentation -I"$nl/include/libnl3" "$source/nfc-controller-probe.c" -L"$nl/lib" -lnl-genl-3 -lnl-3 -lpthread -o "$out/nfc-controller-probe"
sha256sum "$out/bt-mgmt-probe" "$out/nfc-controller-probe"
