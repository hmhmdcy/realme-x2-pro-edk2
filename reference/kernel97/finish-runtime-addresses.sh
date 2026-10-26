#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#95 SMP PREEMPT'
dir=/tmp/k97-runtime-retry1
test ! -e "$dir"
mkdir -m 700 "$dir"
test -f /tmp/k97-runtime/wlan-first.txt
test ! -f /tmp/k97-runtime/bt-stop.txt
cp /usr/sbin/samurai-bt-address /tmp/k97-runtime/samurai-bt-address-before-length-fix
sha256sum /tmp/k97-samurai-bt-address-v4 > "$dir/helper-before-install.sha"
cp /tmp/k97-samurai-bt-address-v4 /usr/sbin/samurai-bt-address
chmod 700 /usr/sbin/samurai-bt-address
/usr/sbin/samurai-radio-address bt > "$dir/bt-existing.txt" 2>&1
query=$(cat /run/samurai-radio-address/current)
cmp "$query/wlan-mac-le.bin" /tmp/k96-verified-wlan-mac-le.bin
cmp "$query/bt-mac-le.bin" /tmp/k96-verified-bt-mac-le.bin
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
sh /tmp/k97-samurai-bluetooth stop > "$dir/bt-stop.txt" 2>&1
sh /tmp/k97-samurai-bluetooth start > "$dir/bt-start.txt" 2>&1
sh /tmp/k97-samurai-bluetooth start > "$dir/bt-start-repeat.txt" 2>&1
/tmp/k96-bt-mgmt-probe-scan-only info > "$dir/bt-info-provisioned.txt"
/tmp/k96-bt-mgmt-probe-scan-only configure > "$dir/bt-configure.txt"
/tmp/k96-bt-mgmt-probe-scan-only scan > "$dir/bt-scan.txt"
/tmp/k96-bt-mgmt-probe-scan-only off > "$dir/bt-off.txt"
/tmp/k96-bt-mgmt-probe-scan-only info > "$dir/bt-info-final.txt"
wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-after.txt"
grep -qx wpa_state=COMPLETED "$dir/wpa-after.txt"
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sha256sum -c /tmp/k96-persist-before.sha > "$dir/persist-check.txt"
dmesg > "$dir/dmesg-after.txt"
cp -a /run/samurai-radio-address "$dir/radio-address"
echo RUNTIME_ADDRESS_LIFECYCLE_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k97-runtime-retry1.tar k97-runtime-retry1
sha256sum /tmp/k97-runtime-retry1.tar
echo RUNTIME_ADDRESS_LIFECYCLE_PASS
