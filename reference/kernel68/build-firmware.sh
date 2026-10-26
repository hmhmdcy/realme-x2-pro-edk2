#!/bin/bash
set -euo pipefail
repo=/home/cy122/edk2-samurai/repo
linux=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel68
blob=Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
fv=workspace/Build/samurai/RELEASE_GCC5/FV
cd "$repo"
test "$(git rev-parse HEAD)" = 2d389cff3d24b06ca1d407556997a114cb116178
test -z "$(git status --porcelain)"
test ! -e "$out/boot-before.img"
test "$(sha256sum boot-samurai.img | cut -d' ' -f1)" = 8c9dea12a8eca687f9da59e067da8c3dfb91bec4d61ae3371c67292d434c7edd
cmp boot-samurai.img /mnt/e/edk2-samurai-out/boot-samurai-f1.img
test "$(sha256sum "$blob" | cut -d' ' -f1)" = 68001bab92e8611373200f2928d1d83ef5256890528df59dea92c72c1900756e
test "$(sha256sum "$linux/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb" | cut -d' ' -f1)" = 4641207124f1276f00749132d118ba73c3fdeaef24aeac8b2b1df017ef5dea9a
test "$(sha256sum "$linux/arch/arm64/boot/Image" | cut -d' ' -f1)" = d51d1260091d0d568c30b6dc6e673474658259654d63b0e65d5f3baf036145ff
test "$(sha256sum "$linux/.config" | cut -d' ' -f1)" = 439398137656726f4d2abe57011b9e1c42eb21dbc7f1095ddebec2cf23443546
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
test "$(sha256sum "$linux/arch/arm64/boot/Image" | cut -d' ' -f1)" = d51d1260091d0d568c30b6dc6e673474658259654d63b0e65d5f3baf036145ff
test "$(sha256sum "$linux/.config" | cut -d' ' -f1)" = 439398137656726f4d2abe57011b9e1c42eb21dbc7f1095ddebec2cf23443546
test "$(sha256sum "$linux/drivers/tty/serial/eud.c" | cut -d' ' -f1)" = 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4
test "$(sha256sum "$linux/drivers/tty/serial/eud_earlycon.c" | cut -d' ' -f1)" = 34da9936de5de9b36f232be3b8e0a730f9a56a77a6121b283b8e551bb3c65ad9
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
cmp Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb "$out/compat-before.dtb"
cp boot-samurai.img "$out/boot-k68-opp.img"
cp "$blob" "$out/firmware-after.dtb"
cp "$fv/SM8150_UEFI.fd" "$out/firmware-after.fd"
cp "$fv/FVMAIN.Fv" "$out/fvmain-after.Fv"
cp "$fv/FVMAIN_COMPACT.Fv" "$out/fvcompact-after.Fv"
sha256sum "$out/boot-k68-opp.img" "$blob" "$fv/SM8150_UEFI.fd" "$linux/arch/arm64/boot/Image" "$linux/.config" > "$out/build-hashes.txt"
tail -8 "$out/firmware-build.log"
