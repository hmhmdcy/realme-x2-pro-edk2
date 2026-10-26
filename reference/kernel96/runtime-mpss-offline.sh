#!/bin/sh
# Stage95 RAM test. A synthetic terminal failure marker tests dispatch only;
# this does not simulate a failed cold-boot Wi-Fi/MPSS bootstrap.
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#94 SMP PREEMPT'
grep -qx WIFI_ACTIVE_LIFECYCLE_PASS /tmp/k96-runtime-wifi-active.log
dir=/tmp/k96-runtime-offline
test ! -e "$dir"
test ! -e /run/samurai-wifi/boot-finished
mkdir -m 700 "$dir"
cp /run/samurai-wifi/wpa.conf "$dir/wpa-private-before.conf"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-before.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
dmesg > "$dir/dmesg-before.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 terminate | grep -qx OK
sleep 1
/tmp/k95-bt-mgmt-probe off > "$dir/bt-off-before.txt"
/usr/sbin/samurai-bluetooth stop
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
echo stop > /sys/class/remoteproc/remoteproc0/state
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
test ! -e /sys/class/net/wlan0
# Only this RAM marker is synthetic, explicitly recorded in the evidence.
echo SYNTHETIC_WIFI_TERMINAL_FAILURE_MARKER > "$dir/marker-test.txt"
echo 1 > /run/samurai-wifi/boot-finished
/usr/sbin/samurai-bluetooth boot
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
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
/tmp/k95-bt-mgmt-probe scan > "$dir/bt-scan.txt"
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
test ! -e /sys/class/net/wlan0
test -e /sys/class/graphics/fb0
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-offline.txt"
dmesg > "$dir/dmesg-offline.txt"
echo BT_SCAN_WITH_MPSS_OFFLINE_PASS
/tmp/k95-bt-mgmt-probe off > "$dir/bt-off-after.txt"
/usr/sbin/samurai-bluetooth stop
rm /run/samurai-wifi/boot-finished
for file in /run/samurai-wifi/tftp.pid /run/samurai-wifi/rmtfs.pid; do
    pid=$(cat "$file")
    case "$pid" in ''|*[!0-9]*) exit 1;; esac
    tr '\0' ' ' < "/proc/$pid/cmdline" | grep -qE '^/usr/sbin/samurai-(tqftpserv|rmtfs-cow)'
    kill -0 "$pid"
done
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/bind
echo start > /sys/class/remoteproc/remoteproc0/state
for attempt in $(seq 1 60); do
    test -e /sys/class/net/wlan0 && break
    sleep 1
done
test -e /sys/class/net/wlan0
ip link set wlan0 up
nohup /usr/sbin/wpa_supplicant -Dnl80211 -iwlan0 -c/run/samurai-wifi/wpa.conf > "$dir/wpa-restart.log" 2>&1 < /dev/null &
echo $! > /run/samurai-wifi/wpa.pid
for attempt in $(seq 1 45); do
    [ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]
    test -e /sys/class/graphics/fb0
    sleep 1
done
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-after.txt"
grep -qx wpa_state=COMPLETED "$dir/wpa-after.txt"
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp-after.txt" 2>&1
gateway=$(awk '$1=="default" && $5=="wlan0" {print $3}' /proc/net/route)
# BusyBox ip's textual route is used rather than /proc's hexadecimal gateway.
gateway=$(ip route show dev wlan0 | awk '$1=="default" {print $3}')
test -n "$gateway"
ping -I wlan0 -c 3 -W 3 "$gateway" > "$dir/gateway-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-after.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
dmesg > "$dir/dmesg-after.txt"
/usr/sbin/samurai-bluetooth status > "$dir/service-status.txt"
echo WIFI_RECOVERY_AFTER_INDEPENDENT_BT_PASS
