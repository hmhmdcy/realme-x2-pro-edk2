#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = 02ba5ffd-9768-43e4-9c6e-511bb1aeccd1 ]
grep -q CONNECTIVITY_SETUP_PASS /tmp/k95-test-connectivity.log
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > /tmp/k95-5ghz-coexistence-status.txt
grep -qx freq=5180 /tmp/k95-5ghz-coexistence-status.txt
test ! -e /tmp/k95-5ghz-coexistence-scan.txt
cat /sys/kernel/debug/dri/1/encoder-0/status > /tmp/k95-5ghz-display-before-scan.txt
/tmp/k95-bt-mgmt-probe scan > /tmp/k95-5ghz-coexistence-scan.txt 2>&1 &
scan_pid=$!
for attempt in $(seq 1 45); do
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]
    test -e /sys/class/drm/card1
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status | grep -qx wpa_state=COMPLETED
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status | grep -qx freq=5180
    printf 'sample=%s uptime=%s MPSS=running WPA=COMPLETED DRM=present taint=0\n' "$attempt" "$(cut -d ' ' -f1 /proc/uptime)"
    sleep 2
done
wait "$scan_pid"
grep -q 'command=0x0023 status=0x00' /tmp/k95-5ghz-coexistence-scan.txt
grep -q 'event=0x0012' /tmp/k95-5ghz-coexistence-scan.txt
grep -q 'discovering=0' /tmp/k95-5ghz-coexistence-scan.txt
cat /sys/kernel/debug/dri/1/encoder-0/status > /tmp/k95-5ghz-display-after-scan.txt
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt
echo COEXISTENCE_OBSERVATION_PASS
