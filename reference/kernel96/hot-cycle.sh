#!/bin/sh
# One bounded independent BT scan and Wi-Fi/MPSS restart on the fixed kernel.
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#95 SMP PREEMPT'
grep -qx COEXISTENCE_OBSERVATION_PASS /tmp/k96-initial-retry1-coexistence.log
grep -qx CONNECTIVITY_SETUP_DMS_ADDRESSES_PASS /tmp/k96-finish-runtime-setup.log
dir=/tmp/k96-hot-cycle
test ! -e "$dir"
mkdir -m 700 "$dir"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-before.txt"
dmesg > "$dir/dmesg-before.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 terminate | grep -qx OK
sleep 1
/tmp/k96-bt-mgmt-probe off > "$dir/bt-off-before.txt"
/usr/sbin/samurai-bluetooth stop
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
echo WLAN_UNBOUND_WITH_MPSS_RUNNING
echo stop > /sys/class/remoteproc/remoteproc0/state
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
test ! -e /sys/class/net/wlan0
/usr/sbin/samurai-bluetooth start
/usr/sbin/samurai-bluetooth start
for attempt in $(seq 1 30); do
    /tmp/k96-bt-mgmt-probe info > "$dir/bt-offline-unconfigured.txt" || true
    grep -qx 'command=0x0036 status=0x00 payload=01000000' "$dir/bt-offline-unconfigured.txt" && break
    sleep 1
done
grep -qx 'command=0x0036 status=0x00 payload=01000000' "$dir/bt-offline-unconfigured.txt"
/tmp/k96-bt-mgmt-probe dms-address /tmp/k96-verified-bt-mac-le.bin > "$dir/bt-offline-address.txt"
for attempt in $(seq 1 30); do
    if /tmp/k96-bt-mgmt-probe info > "$dir/bt-offline-configured.txt"; then break; fi
    sleep 1
done
grep -qx 'command=0x0003 status=0x00 payload=01000000' "$dir/bt-offline-configured.txt"
/tmp/k96-bt-mgmt-probe configure > "$dir/bt-offline-configure.txt"
/tmp/k96-bt-mgmt-probe scan > "$dir/bt-offline-scan.txt"
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
test ! -e /sys/class/net/wlan0
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
test -e /sys/class/graphics/fb0
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-offline.txt"
dmesg > "$dir/dmesg-offline.txt"
echo BT_SCAN_WITH_MPSS_OFFLINE_PASS
/tmp/k96-bt-mgmt-probe off > "$dir/bt-offline-off.txt"
/usr/sbin/samurai-bluetooth stop
/usr/sbin/samurai-bluetooth stop
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
wlan_mac=$(od -An -tx1 -v /tmp/k96-verified-wlan-mac-le.bin | awk '{printf "%s:%s:%s:%s:%s:%s",$6,$5,$4,$3,$2,$1}')
ip link set wlan0 down
ip link set dev wlan0 address "$wlan_mac"
unset wlan_mac
ip link set wlan0 up
nohup /usr/sbin/wpa_supplicant -Dnl80211 -iwlan0 -c/run/samurai-wifi/wpa.conf > "$dir/wpa-recovery.log" 2>&1 < /dev/null &
echo $! > /run/samurai-wifi/wpa.pid
for attempt in $(seq 1 45); do
    [ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]
    test -e /sys/class/graphics/fb0
    sleep 1
done
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-recovered.txt"
grep -qx wpa_state=COMPLETED "$dir/wpa-recovered.txt"
grep -qx freq=2462 "$dir/wpa-recovered.txt"
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp-recovered.txt" 2>&1
echo WIFI_RECOVERY_AFTER_INDEPENDENT_BT_PASS
/usr/sbin/samurai-bluetooth start
for attempt in $(seq 1 30); do
    /tmp/k96-bt-mgmt-probe info > "$dir/bt-recovered-unconfigured.txt" || true
    grep -qx 'command=0x0036 status=0x00 payload=01000000' "$dir/bt-recovered-unconfigured.txt" && break
    sleep 1
done
grep -qx 'command=0x0036 status=0x00 payload=01000000' "$dir/bt-recovered-unconfigured.txt"
/tmp/k96-bt-mgmt-probe dms-address /tmp/k96-verified-bt-mac-le.bin > "$dir/bt-recovered-address.txt"
for attempt in $(seq 1 30); do
    if /tmp/k96-bt-mgmt-probe info > "$dir/bt-recovered-configured.txt"; then break; fi
    sleep 1
done
grep -qx 'command=0x0003 status=0x00 payload=01000000' "$dir/bt-recovered-configured.txt"
/tmp/k96-bt-mgmt-probe configure > "$dir/bt-recovered-configure.txt"
/tmp/k96-bt-mgmt-probe info > "$dir/bt-recovered-powered-info.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-after.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
dmesg > "$dir/dmesg-after.txt"
echo HOT_CYCLE_RECOVERY_PASS
