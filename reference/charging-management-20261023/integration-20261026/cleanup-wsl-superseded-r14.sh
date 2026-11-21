#!/bin/sh
set -eu

base=/home/cy122/charging-management-20261023
targets='
apsd-image505-01
dwc-image503-start-recovery-01
dwc-image504-budget-fence-01
gauge-image363-baseline-01
gauge-image501-B-01
gauge-image501-B-repro-01
gauge-image502-notify-01
route-pm-image506-02
tcpm-sink-image507-01
tcpm-sink-shutdown-image507-01
tcpm-usb-budget-image508-01
'

before=$(df -B1 --output=avail "$base" | tail -n 1 | tr -d ' ')
count=0
for name in $targets; do
    path=$base/$name
    [ -e "$path" ] || continue
    resolved=$(realpath -e "$path")
    case "$resolved" in
        "$base"/*) ;;
        *) echo "refusing path outside base: $resolved" >&2; exit 1 ;;
    esac
    rm -rf -- "$resolved"
    count=$((count + 1))
done
after=$(df -B1 --output=avail "$base" | tail -n 1 | tr -d ' ')
echo "removed=$count"
echo "reclaimed_bytes=$((after - before))"
df -h "$base"
