#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = b65a234f-44f4-4ad3-9d40-ecafdeb233b1 ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > /tmp/k93-coexistence-wpa.txt
grep -qx wpa_state=COMPLETED /tmp/k93-coexistence-wpa.txt
grep -qx freq=2462 /tmp/k93-coexistence-wpa.txt
/tmp/k93-bt-mgmt-probe power
/tmp/k93-bt-mgmt-probe scan > /tmp/k93-coexistence-scan.txt 2>&1 &
scan_pid=$!
for attempt in $(seq 1 45); do
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status | grep -qx wpa_state=COMPLETED
    printf 'sample=%s uptime=%s MPSS=running WPA=COMPLETED taint=0\n' "$attempt" "$(cut -d ' ' -f1 /proc/uptime)"
    sleep 2
done
# Discovery can end naturally before STOP_DISCOVERY, yielding Rejected (0x0b).
wait "$scan_pid" || true
grep -q 'command=0x0023 status=0x00' /tmp/k93-coexistence-scan.txt
grep -q 'event=0x0012' /tmp/k93-coexistence-scan.txt
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt
echo COEXISTENCE_OBSERVATION_PASS
