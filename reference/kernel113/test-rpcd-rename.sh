#!/bin/bash
set -euo pipefail
cd /home/cy122/hexagonrpc-v04-k112
out=/mnt/e/edk2-samurai-out/kernel113
cp '/mnt/e/RealmeX2Pro edk2/reference/kernel113/test_rpcd_rename.c' hexagonrpcd/test_rpcd_rename.c
gcc -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -DHEXAGONRPC_VERBOSE -Wall -Wextra -Wno-unused-parameter -Iinclude -Ihexagonrpcd \
 libhexagonrpc/{context,fastrpc,interfaces,session}.c \
 hexagonrpcd/{aee_error,apps_mem,interfaces,hexagonfs,hexagonfs_mapped,hexagonfs_plat_subtype_name,hexagonfs_virt_dir,hexagonfs_ram_registry,iobuffer,localctl,rpcd_builder,test_rpcd_rename}.c \
 -pthread -o "$out/test-rpcd-rename" > "$out/test-rpcd-rename-build.log" 2>&1
# Upstream's builder intentionally has no tree destructor; ignore that known
# process-lifetime allocation while retaining ASan/UBSan memory error checks.
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 "$out/test-rpcd-rename" > "$out/test-rpcd-rename.log" 2>&1
tail -1 "$out/test-rpcd-rename.log"
