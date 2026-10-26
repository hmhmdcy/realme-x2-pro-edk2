#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel111
mkdir "$out/apk-sensor-tools"
cd "$out/apk-sensor-tools"
curl --fail --location --proto '=https' --tlsv1.2 --max-time 40 --retry 1 \
  -o hexagonrpcd-0.4.0-r3.apk \
  https://mirrors.ustc.edu.cn/alpine/edge/community/aarch64/hexagonrpcd-0.4.0-r3.apk
tar -tzf hexagonrpcd-0.4.0-r3.apk > package-file-list.txt
tar -xOzf hexagonrpcd-0.4.0-r3.apk .PKGINFO > package-info.txt
grep -q '^pkgname = hexagonrpcd$' package-info.txt
grep -q '^pkgver = 0.4.0-r3$' package-info.txt
grep -q '^arch = aarch64$' package-info.txt
sha256sum hexagonrpcd-0.4.0-r3.apk > SHA256SUMS
echo SENSOR_RPCD_APK_FETCH_COMPLETE
