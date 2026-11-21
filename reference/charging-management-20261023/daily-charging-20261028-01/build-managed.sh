#!/bin/sh
set -eu

base=/home/cy122/charging-management-20261023/charging-integration-20261026-01/r8-module
source=/mnt/e/RealmeX2Pro\ edk2/reference/charging-management-20261023/daily-charging-20261028-01
dest="$base/deferred-mp2650-build-20261028-02"
log="$source/managed-build.log"

rm -rf "$dest"
mkdir -p "$dest"
cp -a "$source"/managed-src/* "$dest"/
make -C "$base/final-source-view" O="$base/final-build" M="$dest" \
    ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j2 W=1 modules \
    >"$log" 2>&1
cp "$dest/samurai-mp2650.ko" "$source/artifacts/samurai-mp2650-deferred.ko"
sha256sum "$source/artifacts/samurai-mp2650-deferred.ko"
