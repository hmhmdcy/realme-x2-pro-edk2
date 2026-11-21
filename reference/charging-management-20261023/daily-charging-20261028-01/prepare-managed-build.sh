#!/bin/sh
set -eu

# Materialize the deferred driver beside the already verified r20 source
# snapshot. This script only writes inside a new private WSL build directory.
test "$(id -u)" -eq 0
test -d /home/cy122/charging-management-20261023/charging-integration-20261026-01
test -f /mnt/e/RealmeX2Pro\ edk2/reference/charging-management-20261023/daily-charging-20261028-01/managed-src/samurai-mp2650.c

root=/home/cy122/charging-management-20261023/charging-integration-20261026-01/r8-module
base="$root/new-patch-01"
dest="$root/deferred-mp2650-build"
src=/mnt/e/RealmeX2Pro\ edk2/reference/charging-management-20261023/daily-charging-20261028-01/managed-src/samurai-mp2650.c

rm -rf "$dest"
mkdir -p "$dest"
cp -a "$base"/charge-cycle-hold.h "$base"/charge-cycle.h \
    "$base"/charging-notify.h "$base"/gauge-i2c.h \
    "$base"/gauge-protocol.h "$base"/mp2650-core.h \
    "$base"/negotiated-input.h "$base"/oem-full-cycle.h \
    "$base"/oem-profile.h "$base"/reattach-observation.h \
    "$base"/samurai-status.h "$base"/thermal-bands.h "$dest"/
cp "$src" "$dest/samurai-mp2650.c"
printf 'obj-m += samurai-mp2650.o\n' > "$dest/Makefile"
printf '%s\n' "$dest/samurai-mp2650.c"
