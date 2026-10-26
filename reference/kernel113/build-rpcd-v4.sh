#!/bin/bash
set -euo pipefail
umask 077
cd /home/cy122/hexagonrpc-v04-k112
out=/mnt/e/edk2-samurai-out/kernel113
test "$(git describe --tags --exact-match HEAD)" = v0.4.0
test ! -e "$out/hexagonrpcd-ram-trial-v4"
aarch64-linux-gnu-gcc -static -O2 -g -DHEXAGONRPC_VERBOSE -DHEXAGONRPC_FLYWHEEL_TRACE -Wall -Wextra -Wno-unused-parameter -Iinclude \
 libhexagonrpc/{context,fastrpc,interfaces,session}.c \
 hexagonrpcd/{aee_error,apps_mem,apps_std,interfaces,hexagonfs,hexagonfs_mapped,hexagonfs_plat_subtype_name,hexagonfs_virt_dir,hexagonfs_ram_registry,iobuffer,listener,localctl,rpcd,rpcd_builder}.c \
 -pthread -o "$out/hexagonrpcd-ram-trial-v4" > "$out/rpcd-v4-build.log" 2>&1
aarch64-linux-gnu-strip --strip-debug "$out/hexagonrpcd-ram-trial-v4"
sha256sum "$out/hexagonrpcd-ram-trial-v4" > "$out/rpcd-v4.sha256"
git diff > "$out/rpcd-v4-private.patch"
echo KERNEL113_RPCD_V4_DIAGNOSTIC_BUILD_PASS
