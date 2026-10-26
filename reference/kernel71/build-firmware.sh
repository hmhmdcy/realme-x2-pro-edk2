#!/bin/bash
set -euo pipefail
repo=/home/cy122/edk2-samurai/repo
linux=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel71
blob=Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
fv=workspace/Build/samurai/RELEASE_GCC5/FV
cd "$repo"
test "$(git rev-parse HEAD)" = 0819bd544089e5120108203f8cd2d5c56e374e23
test -z "$(git status --porcelain)"
test ! -e "$out/boot-before.img"
test "$(sha256sum boot-samurai.img | cut -d' ' -f1)" = 785071a405d839b13d3d0ef040f42d227b09659e6dd0d3df96bb3689ced0635b
cmp boot-samurai.img /mnt/e/edk2-samurai-out/kernel68/boot-k68-opp.img
test "$(sha256sum "$blob" | cut -d' ' -f1)" = 4641207124f1276f00749132d118ba73c3fdeaef24aeac8b2b1df017ef5dea9a
test "$(sha256sum "$linux/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb" | cut -d' ' -f1)" = 5f184f24c3fe23723b01639f7462c6be9ed7238505b50102794de064bd6f4849
test "$(sha256sum "$linux/arch/arm64/boot/Image" | cut -d' ' -f1)" = 9d1639ee02d6844225feed1969e90b0a87aec2559b855085e94ca5862efbef66
test "$(sha256sum "$linux/.config" | cut -d' ' -f1)" = e60916a738518e6fc904519371745d271418d1554b86a4b522f68af28b3a98e1
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
test "$(sha256sum "$linux/arch/arm64/boot/Image" | cut -d' ' -f1)" = 9d1639ee02d6844225feed1969e90b0a87aec2559b855085e94ca5862efbef66
test "$(sha256sum "$linux/.config" | cut -d' ' -f1)" = e60916a738518e6fc904519371745d271418d1554b86a4b522f68af28b3a98e1
test "$(sha256sum "$linux/drivers/tty/serial/eud.c" | cut -d' ' -f1)" = 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4
test "$(sha256sum "$linux/drivers/tty/serial/eud_earlycon.c" | cut -d' ' -f1)" = 34da9936de5de9b36f232be3b8e0a730f9a56a77a6121b283b8e551bb3c65ad9
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
cmp Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb "$out/compat-before.dtb"
cp boot-samurai.img "$out/boot-k71-touch.img"
cp "$blob" "$out/firmware-after.dtb"
cp "$fv/SM8150_UEFI.fd" "$out/firmware-after.fd"
cp "$fv/FVMAIN.Fv" "$out/fvmain-after.Fv"
cp "$fv/FVMAIN_COMPACT.Fv" "$out/fvcompact-after.Fv"
sha256sum "$out/boot-k71-touch.img" "$blob" "$fv/SM8150_UEFI.fd" "$linux/arch/arm64/boot/Image" "$linux/.config" > "$out/build-hashes.txt"
tail -8 "$out/firmware-build.log"
