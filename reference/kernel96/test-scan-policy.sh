#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
dir=/tmp/k96-scan-policy
test ! -e "$dir"
mkdir -m 700 "$dir"
/tmp/k96-bt-mgmt-probe-scan-only info > "$dir/bt-info-before.txt"
/tmp/k96-bt-mgmt-probe-scan-only scan-policy > "$dir/policy.txt"
/tmp/k96-bt-mgmt-probe-scan-only info > "$dir/bt-info-policy.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
/tmp/k96-bt-mgmt-probe-scan-only scan > "$dir/bt-scan.txt"
/tmp/k96-bt-mgmt-probe-scan-only off > "$dir/bt-off.txt"
/tmp/k96-bt-mgmt-probe-scan-only info > "$dir/bt-info-final.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa.txt"
grep -qx wpa_state=COMPLETED "$dir/wpa.txt"
grep -qx freq=5180 "$dir/wpa.txt"
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sha256sum -c /tmp/k96-persist-before.sha > "$dir/persist-check.txt"
sha256sum /tmp/k96-bt-mgmt-probe-scan-only > "$dir/helper-sha.txt"
dmesg > "$dir/dmesg-after.txt"
echo SCAN_ONLY_POLICY_PASS > "$dir/result.txt"
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k96-scan-policy.tar k96-scan-policy
sha256sum /tmp/k96-scan-policy.tar
echo SCAN_ONLY_POLICY_PASS
