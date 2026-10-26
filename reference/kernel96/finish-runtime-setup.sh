#!/bin/sh
# Continue the preserved stage96 setup after its control-socket startup race.
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
test -f /tmp/k96-verified-wlan-mac-le.bin
test -f /tmp/k96-verified-bt-mac-le.bin
dir=/tmp/k96-initial-retry1
test ! -e "$dir"
mkdir -m 700 "$dir"
if ! grep -q ' /sys/kernel/debug debugfs ' /proc/mounts; then
    mount -t debugfs debugfs /sys/kernel/debug
fi
for attempt in $(seq 1 30); do
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-after.txt" 2> "$dir/wpa-control-wait.txt" || true
    if grep -qx wpa_state=COMPLETED "$dir/wpa-after.txt" && grep -qx freq=2462 "$dir/wpa-after.txt"; then break; fi
    sleep 2
done
grep -qx wpa_state=COMPLETED "$dir/wpa-after.txt"
grep -qx freq=2462 "$dir/wpa-after.txt"
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp.txt" 2>&1
echo TWO_GHZ_DMS_ADDRESS_AUTH_DHCP_PASS
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
