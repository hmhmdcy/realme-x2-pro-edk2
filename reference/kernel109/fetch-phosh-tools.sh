#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel109/apk-tools
mkdir -p "$out"
for pkg in evtest-1.36-r0 grim-1.5.0-r0 stevia-schemas-0.57.0-r2 wlr-randr-0.5.0-r1; do
    curl --fail --show-error --silent --connect-timeout 10 --max-time 60 \
        "https://mirrors.ustc.edu.cn/alpine/edge/community/aarch64/$pkg.apk" \
        -o "$out/$pkg.apk"
done
sha256sum "$out/"*.apk > "$out/SHA256SUMS"
echo OFFICIAL_ALPINE_MIRROR_TOOLS_DOWNLOADED
