#!/bin/bash
set -euo pipefail
cd /mnt/e/edk2-samurai-out/kernel88
own='/mnt/e/RealmeX2Pro edk2/reference/kernel88'
aarch64-linux-gnu-gcc -D_GNU_SOURCE -O2 -static -Iqrtr/include qrtr/src/lookup.c qrtr/lib/qrtr.c qrtr/lib/logging.c -o qrtr-lookup >build-qrtr.log 2>&1
aarch64-linux-gnu-gcc -D_GNU_SOURCE -O2 -static -Iqrtr/include tqftpserv/tqftpserv.c tqftpserv/translate.c qrtr/lib/qrtr.c qrtr/lib/logging.c "$own/ro-firmware.c" -o tqftpserv-ro >build-tqftp.log 2>&1
sha256sum qrtr-lookup tqftpserv-ro >tools-build-hashes.txt
cat tools-build-hashes.txt
