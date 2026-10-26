#!/bin/bash
set -euo pipefail
repo=/home/cy122/edk2-samurai/repo
linux=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel73
blob=Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
fv=workspace/Build/samurai/RELEASE_GCC5/FV
cd "$repo"
test "$(git rev-parse HEAD)" = bd23aaa0980ec726d805f9c0c0d0110e6dcb4858
test -z "$(git status --porcelain)"
test ! -e "$out/boot-before.img"
test "$(sha256sum boot-samurai.img | cut -d' ' -f1)" = a4f4b75a52ec13a9b0b5cd4ebd678daa9a9dafd36548ce82ce4602a1fbcc15db
test "$(sha256sum "$blob" | cut -d' ' -f1)" = 5f184f24c3fe23723b01639f7462c6be9ed7238505b50102794de064bd6f4849
cp boot-samurai.img "$out/boot-before.img"
cp "$blob" "$out/firmware-before.dtb"
cp "$fv/SM8150_UEFI.fd" "$out/firmware-before.fd"
cp "$fv/FVMAIN.Fv" "$out/fvmain-before.Fv"
cp "$fv/FVMAIN_COMPACT.Fv" "$out/fvcompact-before.Fv"
cp Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb "$out/compat-before.dtb"
sha256sum Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.c Platform/Realme/sm8150/EudLogDxe/EudLogDxe.c Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c > "$out/core-sources-before.sha256"
cp "$linux/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb" "$blob"
export PATH=/home/cy122/.local/bin:$PATH
export CPATH=/home/cy122/edk2-samurai/local/uuid/usr/include
export LIBRARY_PATH=/home/cy122/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu
./build.sh -d samurai --toolchain GCC5 --skip-rootfs-gen > "$out/firmware-build.log" 2>&1
sha256sum -c "$out/core-sources-before.sha256"
cmp Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb "$out/compat-before.dtb"
cp boot-samurai.img "$out/boot-k73-display.img"
cp "$blob" "$out/firmware-after.dtb"
cp "$fv/SM8150_UEFI.fd" "$out/firmware-after.fd"
cp "$fv/FVMAIN.Fv" "$out/fvmain-after.Fv"
cp "$fv/FVMAIN_COMPACT.Fv" "$out/fvcompact-after.Fv"
sha256sum "$out/boot-k73-display.img" "$blob" "$fv/SM8150_UEFI.fd" > "$out/firmware-build-hashes.txt"
tail -8 "$out/firmware-build.log"
