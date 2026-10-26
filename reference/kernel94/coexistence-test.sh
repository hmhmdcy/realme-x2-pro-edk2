#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = 4cc1a6f8-d033-4608-bdd9-98e97a0df439 ]
grep -q CONNECTIVITY_SETUP_PASS /tmp/k94-test-connectivity.log
test ! -e /tmp/k94-coexistence-scan.txt
cat /sys/kernel/debug/dri/1/encoder-0/status > /tmp/k94-display-before-scan.txt
/tmp/k94-bt-mgmt-probe scan > /tmp/k94-coexistence-scan.txt 2>&1 &
scan_pid=$!
for attempt in $(seq 1 45); do
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]
    test -e /sys/class/drm/card1
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status | grep -qx wpa_state=COMPLETED
    printf 'sample=%s uptime=%s MPSS=running WPA=COMPLETED DRM=present taint=0\n' "$attempt" "$(cut -d ' ' -f1 /proc/uptime)"
    sleep 2
done
wait "$scan_pid"
grep -q 'command=0x0023 status=0x00' /tmp/k94-coexistence-scan.txt
grep -q 'event=0x0012' /tmp/k94-coexistence-scan.txt
grep -q 'discovering=0' /tmp/k94-coexistence-scan.txt
cat /sys/kernel/debug/dri/1/encoder-0/status > /tmp/k94-display-after-scan.txt
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt
echo COEXISTENCE_OBSERVATION_PASS
