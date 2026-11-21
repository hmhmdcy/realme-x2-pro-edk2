#!/usr/bin/env bash
set -euo pipefail

base=/home/cy122/charging-management-20261023/charging-integration-20261026-01
snapshot="$base/r8-module/pre-status-precharge-snapshot"
patch="/mnt/e/RealmeX2Pro edk2/reference/charging-management-20261023/integration-20261026/trial-517-r9-status-precharge/source-snapshot/drivers/power/supply/bq27xxx-status-override.patch"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/a/drivers/power/supply" "$tmp/a/include/linux/power"
cp "$snapshot/bq27xxx_battery.c" "$tmp/a/drivers/power/supply/"
cp "$snapshot/bq27xxx_battery.h" "$tmp/a/include/linux/power/"
patch --batch --silent -d "$tmp/a" -p1 < "$patch"

cmp "$tmp/a/drivers/power/supply/bq27xxx_battery.c" \
	"$base/source/drivers/power/supply/bq27xxx_battery.c"
cmp "$tmp/a/drivers/power/supply/bq27xxx-status-policy.h" \
	"$base/source/drivers/power/supply/bq27xxx-status-policy.h"
cmp "$tmp/a/include/linux/power/bq27xxx_battery.h" \
	"$base/source/include/linux/power/bq27xxx_battery.h"

printf 'PATCH_REPRODUCES_SOURCE=1\n'
sha256sum "$patch"
