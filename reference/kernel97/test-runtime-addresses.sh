#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#95 SMP PREEMPT'
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
dir=/tmp/k97-runtime
test ! -e "$dir"
mkdir -m 700 "$dir"
wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-before.txt"
grep -qx wpa_state=COMPLETED "$dir/wpa-before.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
sha256sum -c /tmp/k97-tools.sha256 > "$dir/tools-check.txt"
for name in samurai-dms-mac-read samurai-bt-address samurai-radio-address; do
    test ! -e "/usr/sbin/$name"
    cp "/tmp/k97-$name" "/usr/sbin/$name"
    chmod 700 "/usr/sbin/$name"
done
# Existing live identities must remain unchanged; the service refuses to change
# an active WLAN or a powered controller that has a conflicting identity.
/usr/sbin/samurai-radio-address wlan > "$dir/wlan-first.txt" 2>&1
/usr/sbin/samurai-radio-address wlan > "$dir/wlan-repeat.txt" 2>&1
/usr/sbin/samurai-radio-address bt > "$dir/bt-existing.txt" 2>&1
query=$(cat /run/samurai-radio-address/current)
cmp "$query/wlan-mac-le.bin" /tmp/k96-verified-wlan-mac-le.bin
cmp "$query/bt-mac-le.bin" /tmp/k96-verified-bt-mac-le.bin
[ "$(find /run/samurai-radio-address -maxdepth 1 -type d -name 'query.*' | wc -l)" = 1 ]
# No bootstrap marker is fabricated. Wi-Fi/MPSS stay up during UART teardown.
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
tar -C /tmp -cf /tmp/k97-runtime.tar k97-runtime
sha256sum /tmp/k97-runtime.tar
echo RUNTIME_ADDRESS_LIFECYCLE_PASS
