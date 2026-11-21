#!/bin/sh
set -eu

test "$(id -u)" -eq 0

release=7.3.0-rc6-rmx1931-samurai-k363+
target=/lib/modules/$release/extra/samurai-charging/samurai-mp2650.ko
manifest=/usr/share/samurai-charging/manifest.json
module=${1:-./samurai-mp2650.ko}
module_backup=/root/samurai-mp2650-before-sdpboost.ko
manifest_backup=/root/manifest-before-sdpboost.json

test -f "$module"
test -f "$target"
test -f "$manifest"

rc-service samurai-charging stop 2>/dev/null || true
sleep 1

[ -e "$module_backup" ] || cp -a "$target" "$module_backup"
[ -e "$manifest_backup" ] || cp -a "$manifest" "$manifest_backup"

cp "$module" "$target"
chmod 0644 "$target"

python3 - "$manifest" "$target" <<'PY'
import hashlib
import json
import sys

manifest, target = sys.argv[1:]
path = "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko"
data = json.load(open(manifest))
data["installed_files"][path] = hashlib.sha256(open(target, "rb").read()).hexdigest()
with open(manifest, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY

rc-service samurai-charging start
sleep 2

test "$(cat /sys/module/samurai_mp2650/parameters/control)" = Y
input_ua=$(cat /sys/class/power_supply/mp2650-input/input_current_limit)
charge_ua=$(cat /sys/class/power_supply/mp2650-input/constant_charge_current)
echo "managed charging active: input=${input_ua}uA charge=${charge_ua}uA"
