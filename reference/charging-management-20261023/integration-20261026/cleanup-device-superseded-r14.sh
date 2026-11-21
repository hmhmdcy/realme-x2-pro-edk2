#!/bin/sh
set -eu

base=/root/charging-management-20261023
targets='
charging-integration-trial-20261026-02
charging-integration-trial-20261026-03
charging-integration-trial-20261026-04
charging-integration-trial-20261026-05
charging-integration-trial-20261026-06
charging-integration-trial-20261026-07
charging-integration-trial-20261026-08
charging-integration-trial-20261026-09
charging-integration-trial-20261026-10
charging-integration-trial-20261026-10-attempt1-device
charging-integration-trial-20261027-01
charging-integration-trial-20261027-01-attempt1-device
charging-integration-trial-20261027-r9-status-precharge-07
charging-integration-trial-20261027-r9-status-precharge-08
charging-integration-trial-20261027-r9-status-precharge-11
charging-integration-trial-20261027-r9-status-precharge-12
trial-517-r9-status-precharge-r13-06-20261027
r14-status-precharge-11-upload.tar
r14-status-precharge-12-upload.tar
trial-r13-upload.tar
charging-integration-trial-20261027-01-upload-r2.tar.gz
'

before=$(df -B1 "$base" | awk 'NR == 2 { print $4 }')
count=0
for name in $targets; do
    path=$base/$name
    if [ ! -e "$path" ]; then
        continue
    fi
    resolved=$(readlink -f "$path")
    case "$resolved" in
        "$base"/*) ;;
        *) echo "refusing path outside base: $resolved" >&2; exit 1 ;;
    esac
    rm -rf -- "$resolved"
    count=$((count + 1))
done
after=$(df -B1 "$base" | awk 'NR == 2 { print $4 }')
echo "removed=$count"
echo "reclaimed_bytes=$((after - before))"
df -h "$base"
