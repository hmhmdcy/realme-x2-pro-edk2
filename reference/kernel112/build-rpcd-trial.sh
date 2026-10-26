#!/bin/bash
set -euo pipefail
cd /home/cy122/hexagonrpc-v04-k112
out=/mnt/e/edk2-samurai-out/kernel112
version=${1:-v1}
case "$version" in v1) suffix=;; v2) suffix=-v2;; v3) suffix=-v3;; *) exit 2;; esac
test "$(git describe --tags --exact-match HEAD)" = v0.4.0
grep -q 'hexagonfs_enable_ram_registry(sns_reg)' hexagonrpcd/rpcd_builder.c
grep -q 'impl = apps_std_fwrite' hexagonrpcd/apps_std.c
aarch64-linux-gnu-gcc -static -O2 -g -DHEXAGONRPC_VERBOSE -Wall -Wextra -Wno-unused-parameter -Iinclude \
 libhexagonrpc/{context,fastrpc,interfaces,session}.c \
 hexagonrpcd/{aee_error,apps_mem,apps_std,interfaces,hexagonfs,hexagonfs_mapped,hexagonfs_plat_subtype_name,hexagonfs_virt_dir,hexagonfs_ram_registry,iobuffer,listener,localctl,rpcd,rpcd_builder}.c \
 -pthread -o "$out/hexagonrpcd-ram-trial$suffix" > "$out/rpcd-ram-trial$suffix-build.log" 2>&1
aarch64-linux-gnu-strip --strip-debug "$out/hexagonrpcd-ram-trial$suffix"
git diff > "$out/rpcd-ram-trial$suffix.patch"
sha256sum "$out/hexagonrpcd-ram-trial$suffix" > "$out/rpcd-ram-trial$suffix.sha256"
file "$out/hexagonrpcd-ram-trial$suffix"
