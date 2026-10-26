#!/bin/bash
set -euo pipefail
repo=/home/cy122/edk2-samurai/repo
out=/mnt/e/edk2-samurai-out/kernel126
target=$out/canonical-firmware
backup=$out/canonical-firmware-source-backup
blob=Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
fv=workspace/Build/samurai/RELEASE_GCC5/FV
cd "$repo"
test "$(git rev-parse HEAD)" = f23a9f8aa619388412c8aad5834a460e51eae9eb
test "$(git status --porcelain)" = " M $blob"
cmp "$blob" "$out/dtb-before"
cmp boot-samurai.img "$out/boot-before.img"
test ! -e "$target"
mkdir "$target" "$backup"
cp -p "$blob" "$backup/firmware-before.dtb"
cp -p boot-samurai.img "$backup/boot-before.img"
cp -p "$fv/SM8150_UEFI.fd" "$backup/firmware-before.fd"
cp -p "$fv/FVMAIN.Fv" "$backup/fvmain-before.Fv"
cp -p "$fv/FVMAIN_COMPACT.Fv" "$backup/fvcompact-before.Fv"
cp -p Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb "$target/compat-before.dtb"
cp "$backup/"* "$target/"
restore_baseline() {
    cp -p "$backup/firmware-before.dtb" "$blob"
    cp -p "$backup/boot-before.img" boot-samurai.img
    cp -p "$backup/firmware-before.fd" "$fv/SM8150_UEFI.fd"
    cp -p "$backup/fvmain-before.Fv" "$fv/FVMAIN.Fv"
    cp -p "$backup/fvcompact-before.Fv" "$fv/FVMAIN_COMPACT.Fv"
    # Ensure future builds regenerate the DTB FFS after any interrupted build.
    touch "$blob"
}
trap restore_baseline EXIT HUP INT TERM
sha256sum Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.c Platform/Realme/sm8150/EudLogDxe/EudLogDxe.c Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c > "$target/core-sources-before.sha256"
cp "$out/DTB-k126-private" "$blob"
cp "$blob" "$target/firmware-after.dtb"
export PATH=/home/cy122/.local/bin:$PATH
export CPATH=/home/cy122/edk2-samurai/local/uuid/usr/include
export LIBRARY_PATH=/home/cy122/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu
./build.sh -d samurai --toolchain GCC5 --skip-rootfs-gen > "$target/firmware-build.log" 2>&1
sha256sum -c "$target/core-sources-before.sha256"
cp boot-samurai.img "$target/boot-k126-internal-tpg.img"
cp "$fv/SM8150_UEFI.fd" "$target/firmware-after.fd"
cp "$fv/FVMAIN.Fv" "$target/fvmain-after.Fv"
cp "$fv/FVMAIN_COMPACT.Fv" "$target/fvcompact-after.Fv"
restore_baseline
# Rebuild the original tree to remove all intermediate references to the candidate DTB.
./build.sh -d samurai --toolchain GCC5 --skip-rootfs-gen > "$target/firmware-restore-build.log" 2>&1
cmp "$blob" "$backup/firmware-before.dtb"
cmp "$fv/SM8150_UEFI.fd" "$backup/firmware-before.fd"
cmp "$fv/FVMAIN.Fv" "$backup/fvmain-before.Fv"
cmp "$fv/FVMAIN_COMPACT.Fv" "$backup/fvcompact-before.Fv"
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel126/verify-original-restore.py' --allow-recompression
cmp boot-samurai.img "$backup/boot-before.img"
sha256sum -c "$target/core-sources-before.sha256"
test "$(git status --porcelain)" = " M $blob"
trap - EXIT HUP INT TERM
echo CANONICAL_FIRMWARE_CANDIDATE_AND_BYTE_EXACT_BASELINE_RESTORE_COMPLETE
