#!/bin/bash
# Archive the LoadOptions build and commit the firmware change in the EDK2 repo.
set -e
RK=/home/cy122/edk2-samurai/repo
OUT=/mnt/e/edk2-samurai-out
W="/mnt/e/RealmeX2Pro edk2/linux-port"

cp -f "$RK/boot-samurai.img" "$OUT/boot-samurai-linux-cmdline.img"
cp -f "$RK/workspace/Build/samurai/RELEASE_GCC5/FV/SM8150_UEFI.fd" "$OUT/SM8150_UEFI-samurai-linux-cmdline.fd"
ls -la "$OUT/boot-samurai-linux-cmdline.img" "$OUT/SM8150_UEFI-samurai-linux-cmdline.fd"
sha256sum "$OUT/boot-samurai-linux-cmdline.img" "$OUT/SM8150_UEFI-samurai-linux-cmdline.fd"

echo
echo "=== commit ==="
cd "$RK"
git add Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -F "$W/scripts/commit-msg-cmdline.txt"
git log --oneline -3
echo "--- status ---"
git status --short
echo DONE