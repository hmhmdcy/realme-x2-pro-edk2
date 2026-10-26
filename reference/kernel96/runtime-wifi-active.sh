#!/bin/sh
# Bounded RAM-only lifecycle test on the already-running stage95 deployment.
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#94 SMP PREEMPT'
dir=/tmp/k96-runtime-active
test ! -e "$dir"
mkdir -m 700 "$dir"
check()
{
    [ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]
    test -e /sys/class/graphics/fb0
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-$2.txt"
    grep -qx wpa_state=COMPLETED "$dir/wpa-$2.txt"
    cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-$2.txt"
}
check "$1" before
dmesg > "$dir/dmesg-before.txt"
cp /usr/sbin/samurai-bluetooth "$dir/service-before"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-before.txt"
cp /tmp/k96-samurai-bluetooth /usr/sbin/samurai-bluetooth
chmod 755 /usr/sbin/samurai-bluetooth
/tmp/k95-bt-mgmt-probe off > "$dir/bt-off-before.txt"
/usr/sbin/samurai-bluetooth stop
/usr/sbin/samurai-bluetooth stop
check "$1" stopped
/usr/sbin/samurai-bluetooth start
/usr/sbin/samurai-bluetooth start
for attempt in $(seq 1 30); do
    /tmp/k95-bt-mgmt-probe info > "$dir/bt-unconfigured.txt" || true
    grep -qx 'command=0x0036 status=0x00 payload=01000000' "$dir/bt-unconfigured.txt" && break
    sleep 1
done
grep -qx 'command=0x0036 status=0x00 payload=01000000' "$dir/bt-unconfigured.txt"
/tmp/k95-bt-mgmt-probe test-address /tmp/k95-temp-bt-address.bin > "$dir/bt-address.txt"
for attempt in $(seq 1 30); do
    if /tmp/k95-bt-mgmt-probe info > "$dir/bt-configured.txt"; then break; fi
    sleep 1
done
grep -qx 'command=0x0003 status=0x00 payload=01000000' "$dir/bt-configured.txt"
/tmp/k95-bt-mgmt-probe configure > "$dir/bt-configure.txt"
/tmp/k95-bt-mgmt-probe scan > "$dir/bt-scan.txt"
/tmp/k95-bt-mgmt-probe off > "$dir/bt-off-after.txt"
check "$1" after
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-after.txt"
dmesg > "$dir/dmesg-after.txt"
cat /proc/modules > "$dir/modules-after.txt"
/usr/sbin/samurai-bluetooth status > "$dir/service-status.txt"
echo WIFI_ACTIVE_LIFECYCLE_PASS
