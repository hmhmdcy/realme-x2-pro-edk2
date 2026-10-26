#!/bin/bash
set -euo pipefail
repo=/home/cy122/edk2-samurai/repo
out=/mnt/e/edk2-samurai-out/kernel99
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel99'
blob=Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
fv=workspace/Build/samurai/RELEASE_GCC5/FV
cd "$repo"
test "$(git rev-parse HEAD)" = f23a9f8aa619388412c8aad5834a460e51eae9eb
test "$(git status --porcelain)" = " M $blob"
cmp "$blob" "$out/dtb-before"
test ! -e "$out/boot-k99-haptics.img"
cp boot-samurai.img "$out/boot-before.img"
cp "$blob" "$out/firmware-before.dtb"
cp "$out/dtb-haptics" "$out/firmware-after.dtb"
cp Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb "$out/compat-before.dtb"
cp "$fv/SM8150_UEFI.fd" "$out/firmware-before.fd"
cp "$fv/FVMAIN.Fv" "$out/fvmain-before.Fv"
cp "$fv/FVMAIN_COMPACT.Fv" "$out/fvcompact-before.Fv"
sha256sum Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.c Platform/Realme/sm8150/EudLogDxe/EudLogDxe.c Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c > "$out/core-sources-before.sha256"
cp "$out/dtb-haptics" "$blob"
export PATH=/home/cy122/.local/bin:$PATH
export CPATH=/home/cy122/edk2-samurai/local/uuid/usr/include
export LIBRARY_PATH=/home/cy122/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu
./build.sh -d samurai --toolchain GCC5 --skip-rootfs-gen > "$out/firmware-build.log" 2>&1
sha256sum -c "$out/core-sources-before.sha256"
cmp Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb "$out/compat-before.dtb"
cp boot-samurai.img "$out/boot-k99-haptics.img"
cp "$fv/SM8150_UEFI.fd" "$out/firmware-after.fd"
cp "$fv/FVMAIN.Fv" "$out/fvmain-after.Fv"
cp "$fv/FVMAIN_COMPACT.Fv" "$out/fvcompact-after.Fv"
python3 "$ref/verify-firmware.py" > "$out/firmware-audit.txt"
tail -6 "$out/firmware-build.log"
