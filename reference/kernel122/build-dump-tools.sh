#!/bin/bash
set -euo pipefail
umask 077
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py'
out=/mnt/e/edk2-samurai-out/kernel122
stage=/home/cy122/pmos-samurai-rootfs122
mkdir -p "$stage/tools/tmp"
export TMPDIR="$stage/tools/tmp"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends uuid-dev > "$out/dump-tools-dependency-private.txt" 2>&1
cd "$stage/tools/f2fs-tools"
test "$(git rev-parse HEAD)" = 83fd39a184df96db5def895ddc55bf68e720ef76
./autogen.sh > "$out/dump-tools-autogen-private.txt" 2>&1
./configure --without-selinux --without-blkid > "$out/dump-tools-configure-private.txt" 2>&1
make -j4 > "$out/dump-tools-build-private.txt" 2>&1
make DESTDIR="$stage/tools/install-root" install > "$out/dump-tools-install-private.txt" 2>&1
test -x "$stage/tools/install-root/usr/local/sbin/dump.f2fs"
echo K122_UPSTREAM_DIRECTORY_DUMP_TOOL_BUILD_PASS
