#!/bin/bash
set -euo pipefail
repo=/home/cy122/edk2-samurai/repo
linux=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel75
blob=Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
fv=workspace/Build/samurai/RELEASE_GCC5/FV
cd "$repo"
test "$(git rev-parse HEAD)" = 20a1d6041b0f4a5b3eb384372de65c22ff2ab81e
test -z "$(git status --porcelain)"
cmp boot-samurai.img "$out/boot-before.img"
cmp "$blob" "$out/firmware-before.dtb"
sha256sum Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.c Platform/Realme/sm8150/EudLogDxe/EudLogDxe.c Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c > "$out/core-sources-before.sha256"
cp "$linux/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb" "$blob"
export PATH=/home/cy122/.local/bin:$PATH
export CPATH=/home/cy122/edk2-samurai/local/uuid/usr/include
export LIBRARY_PATH=/home/cy122/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu
./build.sh -d samurai --toolchain GCC5 --skip-rootfs-gen > "$out/firmware-build.log" 2>&1
sha256sum -c "$out/core-sources-before.sha256"
cmp Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb "$out/compat-before.dtb"
cp boot-samurai.img "$out/boot-k75-gpu.img"
cp "$blob" "$out/firmware-after.dtb"
cp "$fv/SM8150_UEFI.fd" "$out/firmware-after.fd"
cp "$fv/FVMAIN.Fv" "$out/fvmain-after.Fv"
cp "$fv/FVMAIN_COMPACT.Fv" "$out/fvcompact-after.Fv"
sha256sum "$out/boot-k75-gpu.img" "$blob" "$fv/SM8150_UEFI.fd" > "$out/firmware-build-hashes.txt"
tail -8 "$out/firmware-build.log"
