#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#95 SMP PREEMPT'
dir=/tmp/k96-initial
test ! -e "$dir"
mkdir -m 700 "$dir"
if ! grep -q ' /sys/kernel/debug debugfs ' /proc/mounts; then
    mount -t debugfs debugfs /sys/kernel/debug
fi
for attempt in $(seq 1 180); do
    test -e /run/samurai-wifi/ready && break
    sleep 1
done
test -e /run/samurai-wifi/ready
grep -qx 0 /run/samurai-wifi/boot-finished
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
test -e /sys/class/graphics/fb0
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-before.txt"
/tmp/k96-dms-mac-read wlan > "$dir/dms-wlan.txt" 2>&1
/tmp/k96-dms-mac-read bt > "$dir/dms-bt.txt" 2>&1
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-before.txt"
cat /sys/class/net/wlan0/address > "$dir/wlan-address-before.txt"
# Same-handset cnss-daemon reverses the QMI array before using the MAC.
wlan_mac=$(od -An -tx1 -v /tmp/k96-verified-wlan-mac-le.bin | awk '{printf "%s:%s:%s:%s:%s:%s",$6,$5,$4,$3,$2,$1}')
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 terminate | grep -qx OK
sleep 1
ip link set wlan0 down
ip link set dev wlan0 address "$wlan_mac"
cat /sys/class/net/wlan0/address > "$dir/wlan-address-after.txt"
unset wlan_mac
ip link set wlan0 up
cp /tmp/k96-wpa-private.conf /run/samurai-wifi/wpa.conf
nohup /usr/sbin/wpa_supplicant -Dnl80211 -iwlan0 -c/run/samurai-wifi/wpa.conf > "$dir/wpa-address-restart.log" 2>&1 < /dev/null &
echo $! > /run/samurai-wifi/wpa.pid
for attempt in $(seq 1 30); do
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-after.txt" 2> "$dir/wpa-control-wait.txt" || true
    if grep -qx wpa_state=COMPLETED "$dir/wpa-after.txt" && grep -qx freq=2462 "$dir/wpa-after.txt"; then break; fi
    sleep 2
done
grep -qx wpa_state=COMPLETED "$dir/wpa-after.txt"
grep -qx freq=2462 "$dir/wpa-after.txt"
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp.txt" 2>&1
echo TWO_GHZ_DMS_ADDRESS_AUTH_DHCP_PASS
for attempt in $(seq 1 120); do
    grep -q BT_DRIVER_REGISTERED /run/samurai-bluetooth-boot.log && break
    sleep 1
done
grep -q BT_DRIVER_REGISTERED /run/samurai-bluetooth-boot.log
for attempt in $(seq 1 30); do
    /tmp/k96-bt-mgmt-probe info > "$dir/bt-unconfigured.txt" || true
    grep -qx 'command=0x0036 status=0x00 payload=01000000' "$dir/bt-unconfigured.txt" && break
    sleep 1
done
grep -qx 'command=0x0036 status=0x00 payload=01000000' "$dir/bt-unconfigured.txt"
/tmp/k96-bt-mgmt-probe dms-address /tmp/k96-verified-bt-mac-le.bin > "$dir/bt-address.txt"
for attempt in $(seq 1 30); do
    if /tmp/k96-bt-mgmt-probe info > "$dir/bt-configured.txt"; then break; fi
    sleep 1
done
grep -qx 'command=0x0003 status=0x00 payload=01000000' "$dir/bt-configured.txt"
/tmp/k96-bt-mgmt-probe configure > "$dir/bt-configure.txt"
/tmp/k96-bt-mgmt-probe info > "$dir/bt-powered-info.txt"
/tmp/k96-nfc-controller-probe > "$dir/nfc-controller.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-after.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
dmesg > "$dir/dmesg-after.txt"
echo CONNECTIVITY_SETUP_DMS_ADDRESSES_PASS
