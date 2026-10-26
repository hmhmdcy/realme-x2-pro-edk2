#!/bin/bash
# Preserve the verified kernel/DTB, change only the FAT boot entry.
set -euo pipefail
baseline=/mnt/e/edk2-samurai-out/logdump-rx33-console.img
output=${1:-/mnt/e/edk2-samurai-out/logdump-rx39-uefi.img}
app=${2:-/home/cy122/edk2-samurai/repo/workspace/Build/RxProbe/RELEASE_GCC5/AARCH64/RxProbe.efi}
expected=d5a36aa2152dd77735f1ea8861f05ad35cb7f714605d5c3cd9db106b6c5f8953
test "$(sha256sum "$baseline" | cut -d' ' -f1)" = "$expected"
test ! -e "$output"
test -f "$app"
cp --no-clobber "$baseline" "$output"
mren -i "$output" ::Image ::Kernel
mcopy -i "$output" "$app" ::Image
cmp <(mcopy -i "$baseline" ::Image -) <(mcopy -i "$output" ::Kernel -)
cmp <(mcopy -i "$baseline" ::samurai.dtb -) <(mcopy -i "$output" ::samurai.dtb -)
cmp "$app" <(mcopy -i "$output" ::Image -)
mdir -i "$output" ::
sha256sum "$baseline" "$output" "$app"
