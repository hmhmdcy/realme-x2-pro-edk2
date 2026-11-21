#!/usr/bin/env bash
set -euo pipefail

base=/home/cy122/charging-management-20261023/charging-integration-20261026-01
snapshot="$base/r8-module/pre-status-precharge-snapshot"
out="/mnt/e/RealmeX2Pro edk2/reference/charging-management-20261023/integration-20261026/trial-517-r9-status-precharge/source-snapshot/drivers/power/supply/bq27xxx-status-override.patch"

for path in \
	"$snapshot/bq27xxx_battery.c" \
	"$snapshot/bq27xxx_battery.h" \
	"$base/source/drivers/power/supply/bq27xxx_battery.c" \
	"$base/source/drivers/power/supply/bq27xxx-status-policy.h" \
	"$base/source/include/linux/power/bq27xxx_battery.h"; do
	test -f "$path"
done

tmp=$(mktemp "${out}.tmp.XXXXXX")
trap 'rm -f "$tmp"' EXIT

emit_diff() {
	set +e
	diff -u "$@" >> "$tmp"
	status=$?
	set -e
	if [ "$status" -gt 1 ]; then
		exit "$status"
	fi
}

emit_diff \
	--label a/drivers/power/supply/bq27xxx_battery.c \
	--label b/drivers/power/supply/bq27xxx_battery.c \
	"$snapshot/bq27xxx_battery.c" \
	"$base/source/drivers/power/supply/bq27xxx_battery.c"
emit_diff \
	--label a/include/linux/power/bq27xxx_battery.h \
	--label b/include/linux/power/bq27xxx_battery.h \
	"$snapshot/bq27xxx_battery.h" \
	"$base/source/include/linux/power/bq27xxx_battery.h"
emit_diff \
	--label /dev/null \
	--label b/drivers/power/supply/bq27xxx-status-policy.h \
	/dev/null \
	"$base/source/drivers/power/supply/bq27xxx-status-policy.h"

test -s "$tmp"
chmod 0644 "$tmp"
mv -f "$tmp" "$out"
trap - EXIT

printf 'PATCH_SHA256='
sha256sum "$out" | awk '{print $1}'
printf 'PATCH_LINES='
wc -l < "$out"
