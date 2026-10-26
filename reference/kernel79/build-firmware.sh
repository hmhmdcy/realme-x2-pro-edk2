#!/bin/bash
set -euo pipefail
repo=/home/cy122/edk2-samurai/repo
linux=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel79
blob=Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
fv=workspace/Build/samurai/RELEASE_GCC5/FV
cd "$repo"
test "$(git rev-parse HEAD)" = 3dd07f48513c3c1b949dd8d911bb0bf7c84f7c96
test -z "$(git status --porcelain)"
cmp boot-samurai.img "$out/boot-before.img"
cmp "$blob" "$out/firmware-before.dtb"
test ! -e "$out/boot-k79-bus.img"
sha256sum Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.c Platform/Realme/sm8150/EudLogDxe/EudLogDxe.c Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c > "$out/core-sources-before.sha256"
cp "$out/firmware-after.dtb" "$blob"
export PATH=/home/cy122/.local/bin:$PATH
export CPATH=/home/cy122/edk2-samurai/local/uuid/usr/include
export LIBRARY_PATH=/home/cy122/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu
./build.sh -d samurai --toolchain GCC5 --skip-rootfs-gen > "$out/firmware-build.log" 2>&1
sha256sum -c "$out/core-sources-before.sha256"
cmp Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb "$out/compat-before.dtb"
cp boot-samurai.img "$out/boot-k79-bus.img"
cmp "$blob" "$out/firmware-after.dtb"
cp "$fv/SM8150_UEFI.fd" "$out/firmware-after.fd"
cp "$fv/FVMAIN.Fv" "$out/fvmain-after.Fv"
cp "$fv/FVMAIN_COMPACT.Fv" "$out/fvcompact-after.Fv"
sha256sum "$out/boot-k79-bus.img" "$blob" "$fv/SM8150_UEFI.fd" > "$out/firmware-build-hashes.txt"
tail -8 "$out/firmware-build.log"
