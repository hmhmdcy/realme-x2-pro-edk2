#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k109-networkmanager-first
test ! -e "$dest"
mkdir "$dest"
sha256sum /sys/class/net/wlan0/address > "$dest/mac-before-hash.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 terminate | grep -qx OK
sleep 1
ip addr flush dev wlan0
rc-update add networkmanager default
rc-service networkmanager start > "$dest/start.log" 2>&1
connected=0
for attempt in $(seq 1 90); do
    nmcli -t -f GENERAL.STATE device show wlan0 > "$dest/state-last.txt" 2>/dev/null || true
    if grep -q ':100 ' "$dest/state-last.txt"; then connected=1; break; fi
    sleep 1
done
[ "$connected" = 1 ]
sha256sum /sys/class/net/wlan0/address > "$dest/mac-after-hash.txt"
cmp "$dest/mac-before-hash.txt" "$dest/mac-after-hash.txt"
nmcli -t -f GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS device show wlan0 > "$dest/device.txt"
iw dev wlan0 link > "$dest/link-private.txt"
curl -4 --interface wlan0 --fail --connect-timeout 10 --max-time 20 https://www.baidu.com/ -o "$dest/https-body.txt" > "$dest/https-status.txt" 2>&1
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
dmesg > "$dest/dmesg.txt"
tar -C "$dest" -cf /tmp/k109-networkmanager-first.tar .
sha256sum /tmp/k109-networkmanager-first.tar
echo NETWORKMANAGER_WIFI_HTTPS_AND_MAC_PASS
