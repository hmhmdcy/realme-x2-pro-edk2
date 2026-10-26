#!/bin/sh
set -eu
umask 077
[ "$#" = 3 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
case "$2" in initial|initial-retry1|recovery|five-ghz) phase=$2;; *) exit 2;; esac
case "$3" in 2462|5180) frequency=$3;; *) exit 2;; esac
dir=/tmp/k97-$phase-coexistence
test ! -e "$dir"
mkdir -m 700 "$dir"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
/tmp/k97-bt-mgmt-probe scan > "$dir/bt-scan.txt" 2>&1 &
scan_pid=$!
for attempt in $(seq 1 45); do
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]
    test -e /sys/class/drm/card1
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-current.txt"
    grep -qx wpa_state=COMPLETED "$dir/wpa-current.txt"
    grep -qx "freq=$frequency" "$dir/wpa-current.txt"
    printf 'sample=%s uptime=%s MPSS=running WPA=COMPLETED DRM=present taint=0\n' "$attempt" "$(cut -d ' ' -f1 /proc/uptime)"
    sleep 2
done
wait "$scan_pid"
grep -q 'command=0x0023 status=0x00' "$dir/bt-scan.txt"
grep -q 'event=0x0012' "$dir/bt-scan.txt"
grep -q 'discovering=0' "$dir/bt-scan.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-after.txt"
dmesg > "$dir/dmesg-after.txt"
echo COEXISTENCE_OBSERVATION_PASS
