#!/bin/sh
set -eu

CC="${CC:-aarch64-linux-gnu-gcc}"
SRC_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
OUT="${1:-${SRC_DIR}/samucaptureinject.so}"

"${CC}" -shared -fPIC -O2 \
	-nostdlib \
	-fno-stack-protector \
	-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 \
	-Wl,--unresolved-symbols=ignore-all \
	-o "${OUT}" "${SRC_DIR}/samucaptureinject.c"

echo "built ${OUT}"
sha256sum "${OUT}"
