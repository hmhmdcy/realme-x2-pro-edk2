#!/bin/sh
set -eu

root=/root/charging-management-20261023
telemetry=/sys/bus/i2c/devices/0-005c/telemetry
result=$root/recharge-drain-r14-result.json
log=$root/recharge-drain-r14.log
post=$root/recharge-post-load-r14.json

rm -f "$result" "$log" "$post"
deadline=$(( $(date +%s) + 3600 ))
while [ "$(date +%s)" -lt "$deadline" ]; do
    if [ -r "$telemetry" ] &&
       grep -q 'full_cause=3' "$telemetry" &&
       grep -q 'full_holding=1' "$telemetry" &&
       grep -q 'protection_ok=1' "$telemetry" &&
       grep -q 'fault=0' "$telemetry"; then
        break
    fi
    sleep 5
done

if ! grep -q 'full_holding=1' "$telemetry"; then
    echo "timed out waiting for a healthy Full hold" >"$log"
    exit 3
fi

sed -e "s#recharge-drain-528-01-result.json#recharge-drain-r14-result.json#" \
    -e "s/if charging_transition or counted_transition:/if charging_transition or control_transition:/" \
    "$root/recharge-drain-528-01.py" >"$root/recharge-drain-r14.py"
chmod 700 "$root/recharge-drain-r14.py"
python3 -u "$root/recharge-drain-r14.py" >"$log" 2>&1 || drain_rc=$?
sleep 10

python3 - "$post" <<'PY'
import json
import pathlib
import sys
import time

root = pathlib.Path("/root/charging-management-20261023/trial-517-r9-status-precharge")
battery = pathlib.Path("/sys/class/power_supply/bq28z610-0")
mp = pathlib.Path("/sys/class/power_supply/mp2650-input")

def read(path):
    try:
        return path.read_text().strip()
    except Exception:
        return None

def number(path):
    try:
        return int(read(path))
    except Exception:
        return None

telemetry = {}
for item in (read("/sys/bus/i2c/devices/0-005c/telemetry") or "").split():
    if "=" not in item:
        continue
    key, value = item.split("=", 1)
    try:
        telemetry[key] = int(value)
    except ValueError:
        telemetry[key] = value

value = {
    "schema": 1,
    "epoch": round(time.time(), 3),
    "boot_id": read("/proc/sys/kernel/random/boot_id"),
    "battery_status": read(battery / "status"),
    "battery_current_ua": number(battery / "current_now"),
    "battery_voltage_uv": number(battery / "voltage_now"),
    "mp_status": read(mp / "status"),
    "telemetry": telemetry,
    "protection": read(
        "/sys/devices/platform/samurai-gauge-protection/protection_state"
    ),
}
value["passed"] = (
    value["battery_status"] == "Charging"
    and isinstance(value["battery_current_ua"], int)
    and value["battery_current_ua"] > 0
    and telemetry.get("desired_enable") == 1
    and telemetry.get("full_holding") == 0
    and telemetry.get("fault") == 0
    and telemetry.get("protection_ok") == 1
)
pathlib.Path(sys.argv[1]).write_text(
    json.dumps(value, indent=2, sort_keys=True) + "\n"
)
PY

exit "${drain_rc:-0}"
